Place local Kokoro voice packs in this folder when you want TTS to work offline.

Expected files:
- `af_heart.pt`
- `hf_alpha.pt`

Then set:

```powershell
$env:KOKORO_VOICE_DIR = "C:\Users\vishn\OneDrive\Desktop\Ai-voice agent\voice-agent-2.0\tts\voices"
```

You can also point to a single voice file directly:

```powershell
$env:KOKORO_AF_HEART_PATH = "C:\path\to\af_heart.pt"
$env:KOKORO_HF_ALPHA_PATH = "C:\path\to\hf_alpha.pt"
```
