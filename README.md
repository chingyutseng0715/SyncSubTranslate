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

On launch, select the role for this computer:

### Subtitle Service
Runs on the laptop connected to the conference microphone.

1. Enter a **Room Name** (e.g. "Main Hall")
2. Paste your **DashScope API key** (masked with `*`)
3. Select **Language**: Chinese ↔ English or Chinese ↔ Japanese
4. Pick the correct **Microphone** from the dropdown (click ↻ to rescan)
5. Optionally enter a **Monitor IP** — the IP address of the organizer's laptop running Monitor Center
6. Choose a **Display** mode: Translated only, Original only, or Both
7. Adjust **Font Size** and **Color** for original and translated text
8. Click **Start Service**
9. Click **Open Screen** — opens the subtitle display in your browser
10. Double-click the browser window to go fullscreen and connect to the big screen

### Monitor Center
Runs on the organizer's laptop. Shows a live dashboard of every service room that has this computer's IP entered as Monitor IP.

- The monitor window shows **this computer's IP** — enter it into each Subtitle Service laptop's Monitor IP field
- Green dot = online; red dot = no response for 15+ seconds
- Updates every 3 seconds; shows screen client count and terminology version per room
- No server required — discovery uses direct UDP on port 47474

> **Firewall note (Windows):** The app attempts to add a Windows Firewall rule automatically. If rooms don't appear after 20 seconds, run the app as Administrator once, or allow it manually under Windows Firewall → Allow an app.

---

## Screen Display

The browser subtitle screen (`http://localhost:8000`) shows:
- **Partial text** (live, slightly faded) — updates as the speaker talks
- **Final captions** (bright, locked) — appear on sentence completion with full translation
- Up to 3 completed captions on screen at once
- **Clock** top-left; **connection status** top-right
- **Terminology version** badge bottom-right

**Recording:** Click the ⏺ 录制 button to start recording all finalized captions. Click ⏹ 停止录制 to stop and download a `.doc` file with timestamps, original text, and translations.

**Fullscreen:** Double-click anywhere to toggle fullscreen.

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
- Configurable display: Translated only / Original only / Both, with custom font sizes and colors
- Terminology hot-reload — edit `gateway/terms.json` while running, applies within ~15 seconds
- Auto-reconnect — screen and ASR both recover automatically from network drops
- L2 fallback — if translation times out (>4s), shows original Chinese automatically while retrying
- Monitor Center — single dashboard for all rooms over LAN, no server required
- Session recording — download bilingual caption transcripts as `.doc` from the browser screen

---

## Fallback Levels

| Level | Trigger | Behaviour |
|-------|---------|-----------|
| L1 | Normal | Full AI bilingual captions |
| L2 | Translation timeout or API rate limit | Shows original Chinese + `[译文生成中...]`, resumes automatically |
| L3 | ASR disconnect / network loss | Screen holds last subtitle; gateway auto-restarts ASR (3s backoff) |

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
pip install -r requirements.txt
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

```bash
pip install pyinstaller
python -m PyInstaller build.spec --clean --noconfirm
```

Output is in `dist/AIInterpretation/` (Windows) or `dist/AIInterpretation.app` (macOS).

Automated builds for both platforms run via GitHub Actions on every version tag (`v*`).

---

## Configuration Reference

Environment variables passed through the UI or set in `gateway/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | *(required)* | Alibaba Cloud DashScope key |
| `LANG_PAIR` | `zh-en` | Language pair: `zh-en` or `zh-ja` |
| `DISPLAY_MODE` | `en` | What to show: `en` (translated only), `zh` (original only), `both` |
| `ZH_FONT_SIZE` | `30` | Font size in px for original-language text |
| `EN_FONT_SIZE` | `30` | Font size in px for translated text |
| `ZH_COLOR` | `#ffff00` | Color for original-language text |
| `EN_COLOR` | `#4ade80` | Color for translated text |
| `BG_COLOR` | `#000000` | Screen background color |
| `TRANSLATE_MODEL` | `qwen-plus` | Qwen model: `qwen-turbo` / `qwen-plus` / `qwen-max` |
| `TRANSLATE_TIMEOUT` | `4.0` | Seconds before L2 fallback |
| `PORT` | `8000` | HTTP and WebSocket port |
| `DISABLE_AUDIO` | *(unset)* | Set to `1` to disable microphone (test mode) |
| `PYAUDIO_DEVICE_INDEX` | *(system default)* | Audio input device index |
