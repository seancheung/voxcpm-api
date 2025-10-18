import os
import io
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import quote
import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
import voxcpm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="VoxCPM OpenAI-Compatible TTS API", version="1.0.0")


def setup_cors(app: FastAPI, allow_origins: list = None):
    """
    Setup CORS middleware for the FastAPI app.
    
    Args:
        app: FastAPI application instance
        allow_origins: List of allowed origins. If None or ["*"], allows all origins.
    """
    if allow_origins is None:
        allow_origins = ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled with origins: {allow_origins}")


# Global model instance (lazy loading)
voxcpm_model: Optional[voxcpm.VoxCPM] = None
VOICES_DIR = Path(__file__).parent / "voices"
MODEL_DIR = Path(__file__).parent / "models" / "VoxCPM-0.5B"


class TTSRequest(BaseModel):
    model: Optional[str] = Field(None, description="Model name (ignored)")
    input: str = Field(..., max_length=4096, description="Text to synthesize")
    voice: str = Field(..., description="Voice name from voices directory")
    instructions: Optional[str] = Field(None, description="Additional instructions (ignored)")
    response_format: Optional[str] = Field("wav", description="Audio format")
    speed: Optional[float] = Field(1.0, description="Speed (ignored)")
    stream_format: Optional[str] = Field("audio", description="Stream format: audio or sse")


def get_voxcpm_model() -> voxcpm.VoxCPM:
    """Lazy load VoxCPM model."""
    global voxcpm_model
    if voxcpm_model is None:
        logger.info("Loading VoxCPM model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        if not MODEL_DIR.exists():
            raise RuntimeError(f"Model directory not found: {MODEL_DIR}")
        
        voxcpm_model = voxcpm.VoxCPM(voxcpm_model_path=str(MODEL_DIR))
        logger.info("VoxCPM model loaded successfully")
    
    return voxcpm_model


def load_voice(voice_name: str) -> tuple[str, str]:
    """
    Load voice files (wav + txt) from voices directory.
    
    Args:
        voice_name: Name of the voice (without extension)
    
    Returns:
        Tuple of (prompt_wav_path, prompt_text)
    
    Raises:
        HTTPException: If voice files not found
    """
    wav_path = VOICES_DIR / f"{voice_name}.wav"
    txt_path = VOICES_DIR / f"{voice_name}.txt"
    
    if not wav_path.exists() or not txt_path.exists():
        available_voices = sorted(set(
            f.stem for f in VOICES_DIR.glob("*.wav")
            if (VOICES_DIR / f"{f.stem}.txt").exists()
        ))
        raise HTTPException(
            status_code=400,
            detail=f"Voice '{voice_name}' not found. Available voices: {', '.join(available_voices)}"
        )
    
    # Read prompt text
    with open(txt_path, "r", encoding="utf-8") as f:
        prompt_text = f.read().strip()
    
    return str(wav_path), prompt_text


def verify_api_key(authorization: Optional[str]) -> None:
    """
    Verify API key if OPENAI_API_KEY environment variable is set.
    
    Args:
        authorization: Authorization header value
    
    Raises:
        HTTPException: If authentication fails
    """
    expected_key = os.environ.get("OPENAI_API_KEY", "").strip()
    
    # If no key is set, skip authentication
    if not expected_key:
        return
    
    # Check authorization header
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )
    
    # Extract bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )
    
    provided_key = authorization[7:]  # Remove "Bearer " prefix
    
    if provided_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )


def convert_audio_format(wav_data: np.ndarray, sample_rate: int, format: str) -> bytes:
    """
    Convert audio data to specified format.
    
    Args:
        wav_data: Audio waveform as numpy array
        sample_rate: Sample rate in Hz
        format: Target format (mp3, opus, aac, flac, wav, pcm)
    
    Returns:
        Audio data as bytes
    """
    buffer = io.BytesIO()
    
    # Map format to soundfile subtype
    format_map = {
        "wav": "WAV",
        "flac": "FLAC",
        "pcm": "WAV",  # PCM is just raw WAV
    }
    
    if format in format_map:
        sf.write(buffer, wav_data, sample_rate, format=format_map[format])
        buffer.seek(0)
        return buffer.read()
    elif format in ["mp3", "opus", "aac"]:
        # For MP3/OPUS/AAC, we'd need ffmpeg or similar
        # For simplicity, default to WAV
        logger.warning(f"Format '{format}' not directly supported, returning WAV")
        sf.write(buffer, wav_data, sample_rate, format="WAV")
        buffer.seek(0)
        return buffer.read()
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {format}"
        )


def generate_audio_chunks(wav_data: np.ndarray, sample_rate: int, format: str, chunk_size: int = 4096):
    """
    Generate audio data in chunks for streaming.
    
    Args:
        wav_data: Audio waveform as numpy array
        sample_rate: Sample rate in Hz
        format: Target format
        chunk_size: Size of each chunk in bytes
    
    Yields:
        Audio data chunks
    """
    # Convert to target format
    audio_bytes = convert_audio_format(wav_data, sample_rate, format)
    
    # Stream in chunks
    for i in range(0, len(audio_bytes), chunk_size):
        yield audio_bytes[i:i + chunk_size]


@app.post("/v1/audio/speech")
async def create_speech(
    request: TTSRequest,
    authorization: Optional[str] = Header(None),
    x_prompt_speech_enhancement: Optional[str] = Header(None, alias="X-Prompt-Speech-Enhancement"),
    x_text_normalization: Optional[str] = Header(None, alias="X-Text-Normalization"),
    x_cfg_value: Optional[str] = Header(None, alias="X-CFG-Value"),
    x_inference_timesteps: Optional[str] = Header(None, alias="X-Inference-Timesteps")
):
    """
    Generate speech from text using VoxCPM.
    
    OpenAI-compatible endpoint for text-to-speech synthesis.
    
    Custom Headers:
    - X-Prompt-Speech-Enhancement: "True" to enable prompt audio denoising, "False" to disable (default: False)
    - X-Text-Normalization: "True" to enable text normalization, "False" to disable (default: False)
    - X-CFG-Value: Guidance scale value (float, range: 1.0-3.0, default: 2.0)
    - X-Inference-Timesteps: Number of inference timesteps (int, range: 4-30, default: 10)
    """
    try:
        # Verify API key if required
        verify_api_key(authorization)
        
        # Validate input
        if not request.input or not request.input.strip():
            raise HTTPException(status_code=400, detail="Input text is required")
        
        # Parse header values
        denoise = x_prompt_speech_enhancement and x_prompt_speech_enhancement.lower() == "true"
        normalize = x_text_normalization and x_text_normalization.lower() == "true"
        
        # Parse CFG value
        cfg_value = 2.0  # default
        if x_cfg_value:
            try:
                cfg_value = float(x_cfg_value)
                if cfg_value < 1.0 or cfg_value > 3.0:
                    raise HTTPException(
                        status_code=400,
                        detail="X-CFG-Value must be between 1.0 and 3.0"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="X-CFG-Value must be a valid number"
                )
        
        # Parse inference timesteps
        inference_timesteps = 10  # default
        if x_inference_timesteps:
            try:
                inference_timesteps = int(x_inference_timesteps)
                if inference_timesteps < 4 or inference_timesteps > 30:
                    raise HTTPException(
                        status_code=400,
                        detail="X-Inference-Timesteps must be between 4 and 30"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="X-Inference-Timesteps must be a valid integer"
                )
        
        logger.info(f"Processing with denoise={denoise}, normalize={normalize}, cfg_value={cfg_value}, timesteps={inference_timesteps}")
        
        # Load voice files
        prompt_wav_path, prompt_text = load_voice(request.voice)
        
        # Get model
        model = get_voxcpm_model()
        
        # Generate audio
        logger.info(f"Generating audio for voice '{request.voice}': {request.input[:60]}...")
        wav_data = model.generate(
            text=request.input,
            prompt_text=prompt_text,
            prompt_wav_path=prompt_wav_path,
            cfg_value=cfg_value,
            inference_timesteps=inference_timesteps,
            normalize=normalize,
            denoise=denoise,
        )
        
        # Get sample rate (VoxCPM uses 16kHz)
        sample_rate = 16000
        
        # Determine response format
        response_format = request.response_format.lower()
        
        # Map MIME types
        mime_types = {
            "mp3": "audio/mpeg",
            "opus": "audio/opus",
            "aac": "audio/aac",
            "flac": "audio/flac",
            "wav": "audio/wav",
            "pcm": "audio/pcm",
        }
        media_type = mime_types.get(response_format, "audio/wav")
        
        # Return streaming response
        if request.stream_format == "audio" or request.stream_format is None:
            return StreamingResponse(
                generate_audio_chunks(wav_data, sample_rate, response_format),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename=speech.{response_format}",
                    "Transfer-Encoding": "chunked"
                }
            )
        elif request.stream_format == "sse":
            # SSE format not fully implemented, return error
            raise HTTPException(
                status_code=400,
                detail="SSE stream format is not supported in this implementation"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stream_format: {request.stream_format}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating speech: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/v1/voices")
async def list_voices(request: Request):
    """List available voices with preview URLs."""
    available_voices = sorted(set(
        f.stem for f in VOICES_DIR.glob("*.wav")
        if (VOICES_DIR / f"{f.stem}.txt").exists()
    ))
    
    # Build base URL from request
    base_url = str(request.base_url).rstrip('/')
    
    return {
        "voices": [
            {
                "id": voice,
                "name": voice,
                "preview_url": f"{base_url}/v1/voices/{quote(voice, safe='')}/preview"
            }
            for voice in available_voices
        ]
    }


@app.get("/v1/voices/{voice_name}/preview")
async def get_voice_preview(voice_name: str):
    """
    Get preview audio for a specific voice.
    
    Args:
        voice_name: Name of the voice (without extension)
    
    Returns:
        Audio file for preview
    
    Raises:
        HTTPException 404: If voice file not found
    """
    wav_path = VOICES_DIR / f"{voice_name}.wav"
    
    if not wav_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Voice preview not found: {voice_name}"
        )
    
    return FileResponse(
        path=wav_path,
        media_type="audio/wav",
        filename=f"{voice_name}.wav"
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="VoxCPM OpenAI-Compatible TTS API")
    parser.add_argument("--host", type=str, default=None, help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind (default: 8000)")
    parser.add_argument("--allow-cors", action="store_true", help="Enable CORS support for cross-origin requests")
    parser.add_argument("--cors-origins", type=str, default="*", help="Comma-separated list of allowed CORS origins (default: *)")
    args = parser.parse_args()
    
    # Get host and port from args or environment
    host = args.host or os.environ.get("HOST", "0.0.0.0")
    port = args.port or int(os.environ.get("PORT", 8000))
    
    # Setup CORS if requested
    if args.allow_cors:
        if args.cors_origins == "*":
            setup_cors(app, ["*"])
        else:
            origins = [origin.strip() for origin in args.cors_origins.split(",")]
            setup_cors(app, origins)
    
    logger.info(f"Starting VoxCPM OpenAI-Compatible TTS API on {host}:{port}")
    if args.allow_cors:
        logger.info(f"CORS is enabled")
    uvicorn.run(app, host=host, port=port)

