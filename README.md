# VoxCPM OpenAI-Compatible TTS API

This is an OpenAI Text-to-Speech compatible HTTP service powered by VoxCPM.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python api.py

# Or start with CORS enabled (for web browsers)
python api.py --allow-cors
```

The server will start on `http://localhost:8000`. You can now make requests to `/v1/audio/speech` using the OpenAI TTS API format.

## Features

- ✅ OpenAI TTS API compatible endpoint (`POST /v1/audio/speech`)
- ✅ Streaming audio response support
- ✅ Multiple voice selection from `voices/` directory
- ✅ Voice preview endpoint with real audio samples
- ✅ Optional API key authentication
- ✅ Optional CORS support for cross-origin requests
- ✅ Multiple audio format support (WAV, FLAC, PCM)

## Installation

Install dependencies using pip or uv:

```bash
pip install -r requirements.txt
```

Or with uv:

```bash
uv pip install -r requirements.txt
```

## Usage

### Starting the Server

Run the server with:

```bash
python api.py
```

Enable CORS for cross-origin requests:

```bash
python api.py --allow-cors
```

With custom host and port:

```bash
python api.py --host 0.0.0.0 --port 8000 --allow-cors
```

Specify allowed CORS origins:

```bash
python api.py --allow-cors --cors-origins "http://localhost:3000,https://example.com"
```

Or with uvicorn directly:

```bash
uvicorn openai:app --host 0.0.0.0 --port 8000
```

Or with uv:

```bash
uv run api.py --allow-cors
```

### Command Line Arguments

- `--host HOST`: Host to bind (default: `0.0.0.0`)
- `--port PORT`: Port to bind (default: `8000`)
- `--allow-cors`: Enable CORS support for cross-origin requests
- `--cors-origins ORIGINS`: Comma-separated list of allowed CORS origins (default: `*`, allows all origins)

### Environment Variables

- `OPENAI_API_KEY` (optional): If set, the server will require authentication with this API key
- `HOST` (optional, default: `0.0.0.0`): Server host (can be overridden by `--host` argument)
- `PORT` (optional, default: `8000`): Server port (can be overridden by `--port` argument)

### API Endpoints

#### POST /v1/audio/speech

Generate speech from text.

**Request Body:**

```json
{
  "model": "tts-1",
  "input": "Hello, this is a test.",
  "voice": "Bai Ke",
  "response_format": "wav"
}
```

**Parameters:**

- `model` (string, required): Model name (ignored, any value accepted)
- `input` (string, required): Text to synthesize (max 4096 characters)
- `voice` (string, required): Voice name from `voices/` directory (without .wav extension)
  - Available voices: `Bai Ke`, `Pure-hearted Boy`, `Reliable Executive`, `Sincere Adult`, `Stubborn Friend`, `Zhang Biao`
- `response_format` (string, optional): Audio format - `wav` (default), `flac`, `pcm`
  - Note: `mp3`, `opus`, `aac` will fallback to WAV
- `instructions` (string, optional): Ignored
- `speed` (number, optional): Ignored
- `stream_format` (string, optional): `audio` (default) - SSE not supported

**Custom Headers:**

- `X-Prompt-Speech-Enhancement` (string, optional): Enable prompt audio denoising
  - `"True"`: Enable ZipEnhancer denoising for clean, studio-like voice
  - `"False"`: Keep original audio atmosphere (default)
- `X-Text-Normalization` (string, optional): Enable text normalization
  - `"True"`: Use WeTextProcessing to normalize text
  - `"False"`: Use VoxCPM's native text understanding (supports phonemes, formulas, etc.) (default)
- `X-CFG-Value` (float, optional): Guidance scale value for generation
  - Range: `1.0` to `3.0`
  - Default: `2.0`
  - Lower values: More creativity, less adherence to prompt
  - Higher values: Better adherence to prompt speech style
- `X-Inference-Timesteps` (integer, optional): Number of inference timesteps
  - Range: `4` to `30`
  - Default: `10`
  - Lower values: Faster generation
  - Higher values: Better quality

**Response:**

Streaming audio file in the requested format.

#### GET /v1/voices

List available voices with preview URLs.

**Response:**

```json
{
  "voices": [
    {
      "id": "Bai Ke",
      "name": "Bai Ke",
      "preview_url": "http://localhost:8000/v1/voices/Bai%20Ke/preview"
    },
    ...
  ]
}
```

#### GET /v1/voices/{voice_name}/preview

Get preview audio for a specific voice.

**Parameters:**

- `voice_name` (string, path parameter): Voice name (without .wav extension). Special characters should be URL-encoded (e.g., space becomes `%20`).

**Response:**

Returns the WAV audio file for the specified voice. If the voice doesn't exist, returns a 404 error.

**Example:**

```bash
# Download voice preview
curl http://localhost:8000/v1/voices/Bai%20Ke/preview --output preview.wav

# Or just open in browser
# http://localhost:8000/v1/voices/Bai Ke/preview
```

#### GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "ok"
}
```

### Example Usage

#### Using cURL

Without authentication:

```bash
curl http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "你好，这是一个测试。",
    "voice": "Bai Ke"
  }' \
  --output speech.wav
```

With authentication (if `OPENAI_API_KEY` is set):

```bash
curl http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "你好，这是一个测试。",
    "voice": "Bai Ke"
  }' \
  --output speech.wav
```

With custom headers for enhancement and normalization:

```bash
curl http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "X-Prompt-Speech-Enhancement: True" \
  -H "X-Text-Normalization: True" \
  -d '{
    "model": "tts-1",
    "input": "你好，这是一个测试。",
    "voice": "Bai Ke"
  }' \
  --output speech.wav
```

With all custom headers (full control):

```bash
curl http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "X-Prompt-Speech-Enhancement: True" \
  -H "X-Text-Normalization: False" \
  -H "X-CFG-Value: 2.5" \
  -H "X-Inference-Timesteps: 15" \
  -d '{
    "model": "tts-1",
    "input": "你好，这是一个测试。",
    "voice": "Bai Ke"
  }' \
  --output speech.wav
```

List available voices:

```bash
curl http://localhost:8000/v1/voices
```

Preview a voice:

```bash
# Download preview audio
curl http://localhost:8000/v1/voices/Bai%20Ke/preview --output preview.wav

# Or open directly in browser
open http://localhost:8000/v1/voices/Bai%20Ke/preview
```

#### Using Python

Basic usage:

```python
import requests

url = "http://localhost:8000/v1/audio/speech"
headers = {
    "Content-Type": "application/json",
    # "Authorization": "Bearer YOUR_API_KEY"  # If OPENAI_API_KEY is set
}
data = {
    "model": "tts-1",
    "input": "你好，这是一个测试。",
    "voice": "Bai Ke",
    "response_format": "wav"
}

response = requests.post(url, json=data, headers=headers, stream=True)

if response.status_code == 200:
    with open("speech.wav", "wb") as f:
        for chunk in response.iter_content(chunk_size=4096):
            f.write(chunk)
    print("Audio saved to speech.wav")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

With custom headers:

```python
import requests

url = "http://localhost:8000/v1/audio/speech"
headers = {
    "Content-Type": "application/json",
    "X-Prompt-Speech-Enhancement": "True",  # Enable denoising
    "X-Text-Normalization": "True",         # Enable text normalization
}
data = {
    "model": "tts-1",
    "input": "你好，这是一个测试。",
    "voice": "Bai Ke",
    "response_format": "wav"
}

response = requests.post(url, json=data, headers=headers, stream=True)

if response.status_code == 200:
    with open("speech.wav", "wb") as f:
        for chunk in response.iter_content(chunk_size=4096):
            f.write(chunk)
    print("Audio saved to speech.wav")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

With all custom headers (full control):

```python
import requests

url = "http://localhost:8000/v1/audio/speech"
headers = {
    "Content-Type": "application/json",
    "X-Prompt-Speech-Enhancement": "True",  # Enable denoising
    "X-Text-Normalization": "False",        # Use native text understanding
    "X-CFG-Value": "2.5",                   # Higher guidance scale
    "X-Inference-Timesteps": "15",          # More timesteps for better quality
}
data = {
    "model": "tts-1",
    "input": "你好，这是一个测试。",
    "voice": "Bai Ke",
    "response_format": "wav"
}

response = requests.post(url, json=data, headers=headers, stream=True)

if response.status_code == 200:
    with open("speech.wav", "wb") as f:
        for chunk in response.iter_content(chunk_size=4096):
            f.write(chunk)
    print("Audio saved to speech.wav")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

#### Using OpenAI Python SDK

You can use the OpenAI Python SDK by pointing it to your local server:

```python
from openai import OpenAI

# Point to local server
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # Use actual key if OPENAI_API_KEY is set
)

response = client.audio.speech.create(
    model="tts-1",
    voice="Bai Ke",
    input="你好，这是一个测试。"
)

response.stream_to_file("speech.wav")
```

## Voice Management

Voices are stored in the `voices/` directory. Each voice requires two files:

- `{voice_name}.wav` - Reference audio file
- `{voice_name}.txt` - Reference text (transcript of the audio)

To add a new voice:

1. Place a WAV file in `voices/` directory (e.g., `My Voice.wav`)
2. Create a corresponding text file with the transcript (e.g., `My Voice.txt`)
3. The voice will be available as `"voice": "My Voice"` in API requests

## Limitations

- The `model`, `instructions`, and `speed` parameters are ignored
- Only `voice` parameter maps to reference audio files in `voices/` directory
- `mp3`, `opus`, `aac` formats fall back to WAV (requires ffmpeg for proper support)
- SSE (`stream_format: "sse"`) is not supported
- Maximum input length is 4096 characters

## Model Directory

The VoxCPM model should be located at `models/VoxCPM-0.5B/`. Ensure all model files are present:

- `config.json`
- `pytorch_model.bin`
- `audiovae.pth`
- `tokenizer.json`
- `tokenizer_config.json`
- `special_tokens_map.json`

## License

This implementation uses the VoxCPM model. Please refer to the VoxCPM license for usage terms.

