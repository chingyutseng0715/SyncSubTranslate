# AI Conference Real-time Interpretation System

Real-time bilingual captioning for conference big screens.  
Microphone → Alibaba Cloud ASR → Qwen LLM translation → WebSocket → browser display.

---

## Download

Go to the [Releases](../../releases) page and download the latest version for your platform:

| Platform | File |
|----------|------|
| Windows | `AIInterpretation-Windows.zip` |
| macOS | `AIInterpretation-Mac.zip` |

**Windows:** Extract the zip, open the `AIInterpretation` folder, and double-click `AIInterpretation.exe`.  
**macOS:** Extract the zip and open `AIInterpretation.app`. If macOS blocks it, go to System Settings → Privacy & Security → click "Open Anyway".

---

## How It Works

On launch you choose a role for the current computer:

### Subtitle Service
Runs on the laptop connected to the conference microphone.

1. Enter a **Room Name** (e.g. "Main Hall")
2. Paste your **DashScope API key** (masked with `*`)
3. Select **Language**: Chinese ↔ English or Chinese ↔ Japanese
4. Pick the correct **Microphone** from the dropdown
5. Click **Start Service**
6. Click **Open Screen** — this opens the subtitle display in your browser
7. Connect the browser to the big screen (fullscreen with double-click)

### Monitor Center
Runs on the organizer's laptop. Shows a live dashboard of every room on the same network — green dot means online, red means no response for 15+ seconds.

No configuration needed. All service laptops are discovered automatically via UDP broadcast.

> **Firewall note (Windows):** The app will attempt to add a Windows Firewall rule automatically. If rooms still don't appear after 20 seconds, run the app as Administrator once, or allow it manually under Windows Firewall → Allow an app.

---

## API Key

This app uses Alibaba Cloud DashScope — one key covers both speech recognition and translation.

1. Sign up at [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com/)
2. Go to **API Keys** → **Create API Key**
3. Paste the key into the app when starting the Subtitle Service

New accounts receive ¥200–500 in free credits, which is more than enough for a full conference day.

**Estimated cost:**
- ASR: ¥0.018 / minute
- Translation: ¥0.035 / 1,000 characters

---

## Features

- Real-time ASR via `paraformer-realtime-v2` (Chinese/English or Chinese/Japanese mixed input)
- Partial results shown live while speaking; final sentence locks in with translation
- Qwen LLM translation with conference terminology injection
- Terminology hot-reload — edit `gateway/terms.json` while running, applies within ~15 seconds, no restart needed
- Auto-reconnect — screen and ASR both recover automatically from network drops
- L2 fallback — if translation times out (>4s), shows original Chinese automatically while retrying
- Monitor Center — single dashboard for all rooms over LAN, no server required

---

## Fallback Levels

| Level | Trigger | Behaviour |
|-------|---------|-----------|
| L1 | Normal | Full AI bilingual captions |
| L2 | Translation timeout or API rate limit | Shows Chinese original, resumes automatically |
| L3 | ASR disconnect / network loss | Screen holds last subtitle, gateway auto-restarts ASR (3s backoff) |

---

## Terminology Customization

Edit `gateway/terms.json` at any time while the service is running:
```json
{
  "国创中心": "National Innovation Center",
  "新质生产力": "new quality productive forces"
}
```
Changes are detected automatically within ~15 seconds. No restart required.

---

## Advanced: Run from Source

Requires Python 3.10+ and an Alibaba Cloud DashScope API key.

```bash
# Install dependencies
pip install -r requirements.txt

# Run the desktop app
python -m app
```

**macOS — PyAudio setup:**
```bash
brew install portaudio
pip install -r requirements.txt
```

**Test without a microphone:**
```bash
set DISABLE_AUDIO=1 && python -m app   # Windows
DISABLE_AUDIO=1 python -m app          # macOS / Linux
```

---

## Build from Source

Requires PyInstaller:
```bash
pip install pyinstaller
python -m PyInstaller build.spec --clean --noconfirm
```

Output is in `dist/AIInterpretation/` (Windows) or `dist/AIInterpretation.app` (macOS).

Automated builds for both platforms run via GitHub Actions on every version tag (`v*`).

---

## Configuration Reference

These environment variables can be set in `gateway/.env` for advanced use:

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | *(required)* | Alibaba Cloud DashScope key |
| `LANG_PAIR` | `zh-en` | Language pair: `zh-en` or `zh-ja` |
| `TRANSLATE_MODEL` | `qwen-plus` | Qwen model: `qwen-turbo` / `qwen-plus` / `qwen-max` |
| `TRANSLATE_TIMEOUT` | `4.0` | Seconds before L2 fallback |
| `PORT` | `8000` | HTTP and WebSocket port |
| `DISABLE_AUDIO` | *(unset)* | Set to `1` to disable microphone (test mode) |
| `PYAUDIO_DEVICE_INDEX` | *(system default)* | Audio input device index |
