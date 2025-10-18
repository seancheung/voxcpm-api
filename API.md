## Create speech

> post https://api.openai.com/v1/audio/speech

Generates audio from the input text.

### Request body

**input** `string` *Required*

The text to generate audio for. The maximum length is 4096 characters.

**model** `string` *Required*

One of the available TTS models: tts-1, tts-1-hd or gpt-4o-mini-tts.

**voice** `string` *Required*

The voice to use when generating the audio. Supported voices are alloy, ash, ballad, coral, echo, fable, onyx, nova, sage, shimmer, and verse. Previews of the voices are available in the Text to speech guide.

**instructions** `string` *Optional*

Control the voice of your generated audio with additional instructions. Does not work with tts-1 or tts-1-hd.

**response_format** `string` *Optional*

Defaults to wav
The format to audio in. Supported formats are mp3, opus, aac, flac, wav, and pcm.

**speed** `number` *Optional*

Defaults to 1
The speed of the generated audio. Select a value from 0.25 to 4.0. 1.0 is the default.

**stream_format** `string` *Optional*

Defaults to audio
The format to stream the audio in. Supported formats are sse and audio. sse is not supported for tts-1 or tts-1-hd.

### Returns

The audio file content or a stream of audio events. The Speech API provides support for realtime audio streaming using chunk transfer encoding. This means the audio can be played before the full file is generated and made accessible.

### Example

**Default**

```curl
curl https://api.openai.com/v1/audio/speech \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini-tts",
    "input": "The quick brown fox jumped over the lazy dog.",
    "voice": "alloy"
  }' \
  --output speech.mp3
```

**SSE Stream Format**

```curl
curl https://api.openai.com/v1/audio/speech \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini-tts",
    "input": "The quick brown fox jumped over the lazy dog.",
    "voice": "alloy",
    "stream_format": "sse"
  }'
```