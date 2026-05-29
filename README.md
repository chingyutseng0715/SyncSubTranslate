# SyncSubTranslate

Real-time AI-powered bilingual captioning for conference big screens.  
Microphone → Speech Recognition → AI Translation → Browser Display — end-to-end under 3 seconds.

---

## Demo

<!-- Insert demo video here -->

---

## Overview

SyncSubTranslate is a desktop application built for live conference interpretation. It captures audio from a microphone, transcribes speech in real time using Alibaba Cloud ASR, translates each sentence with Qwen LLM, and pushes bilingual subtitles to a browser screen suitable for projection.

Supported language pairs: **Chinese ↔ English** and **Chinese ↔ Japanese**.

---

## Download

Go to the [Releases](../../releases) page and download the latest version for your platform:

| Platform | File |
|----------|------|
| Windows | `AIInterpretation-Windows.zip` |
| macOS | `AIInterpretation-Mac.zip` |

**Windows:** Extract the zip and double-click `AIInterpretation.exe`.  
**macOS:** Extract the zip and open `AIInterpretation.app`. If macOS blocks it, go to System Settings → Privacy & Security → click "Open Anyway".

---

## Getting Started

### 1. Obtain an API Key

SyncSubTranslate uses Alibaba Cloud DashScope — one key covers both speech recognition and translation.

1. Sign up at [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com/)
2. Go to **API Keys** → **Create API Key**
3. Copy the key — you will paste it into the app when starting a session

New accounts receive free credits sufficient for a full conference day.

**Estimated cost:**
| Service | Rate |
|---------|------|
| ASR (Paraformer / Qwen ASR) | ¥0.018 / minute |
| Translation (Qwen LLM) | ¥0.035 / 1,000 characters |

---

### 2. Configure and Start

On launch, select **Subtitle Service**. Fill in the configuration form:

| Field | Description |
|-------|-------------|
| Room Name | A label for this session (e.g. "Main Hall") |
| DashScope API Key | Your Alibaba Cloud API key (masked after entry) |
| Language Pair | `Chinese ↔ English` or `Chinese ↔ Japanese` |
| Microphone | Select the input device; click ↻ to rescan |
| ASR Model | Speech recognition model (see [ASR Models](#asr-models) below) |
| Translation Model | LLM used for translation (see [Translation Models](#translation-models) below) |
| Display Mode | Translated only / Original only / Both |
| Font Size & Color | Customize subtitle appearance for both languages |
| Background | Screen background color: Black / Dark Grey / Dark Blue |
| Monitor IP | *(Optional)* IP of a Monitor Center laptop on the same LAN |

Click **Start Service**, then **Open Screen** to launch the subtitle display in your browser.  
Double-click the browser window to go fullscreen for projection.

> **Tip:** Your last-used settings are saved automatically. Click **Use Last Settings** at the top of the form to restore them instantly at the next session.

---

## ASR Models

Three speech recognition models are available, each suited to different priorities:

| Model | Protocol | Best For |
|-------|----------|----------|
| `paraformer-realtime-v2` | DashScope SDK | Stability-first deployments; proven in production |
| `qwen3-asr-flash-realtime-2026-02-10` | Realtime API | Higher accuracy, especially for mixed-language speech |
| `fun-asr-realtime-2026-02-28` | Realtime API | Alternative Realtime API option; FunASR-based backend |

**`paraformer-realtime-v2`** (recommended for most events)  
The classic DashScope SDK path. Mature, stable, and well-tested in conference environments. Lowest risk for mission-critical sessions.

**`qwen3-asr-flash-realtime-2026-02-10`**  
Uses the newer OpenAI-compatible Realtime API protocol. Delivers improved accuracy on mixed Chinese-English speech. Best choice when transcript quality matters most and you are comfortable with a newer model.

**`fun-asr-realtime-2026-02-28`**  
Also uses the Realtime API path. FunASR-based backend — a good alternative if `qwen3-asr-flash` is unavailable or rate-limited.

> All three models automatically resample your microphone's native audio to 16kHz mono before sending to the API, so they work with any microphone regardless of its native sample rate.

---

## Translation Models

Three Qwen LLM models are available for translation. Choose based on the trade-off between speed, cost, and accuracy:

| Model | Speed | Cost | Accuracy | Best For |
|-------|-------|------|----------|----------|
| `qwen-turbo` | Fastest | Lowest | Good | High-volume sessions; tight budgets |
| `qwen-plus` | Balanced | Medium | Very good | Most conferences *(default)* |
| `qwen-max` | Slowest | Highest | Best | Technical sessions with complex terminology |

**`qwen-turbo`**  
The most responsive option. Translations typically arrive in under 1 second. Suitable when speaker pace is fast and sentence complexity is low. Occasionally produces less nuanced phrasing on highly technical content.

**`qwen-plus`** *(recommended default)*  
A well-balanced model for conference use. Handles professional vocabulary and mixed-language sentences reliably, with translation latency well within the 4-second threshold under normal network conditions.

**`qwen-max`**  
The highest-quality model. Produces the most accurate and natural translations, especially for specialized terminology, formal speech, or policy language. Slower response time increases the chance of hitting the L2 fallback on very long sentences — consider raising `TRANSLATE_TIMEOUT` if you use this model.

> All three models respect the terminology dictionary in `gateway/terms.json`. Domain-specific terms are injected into the system prompt on every call, regardless of which model is selected.

---

## Subtitle Screen

The browser display at `http://localhost:8000` shows:

- **Live partial text** — faintly displayed while the speaker is mid-sentence
- **Finalized captions** — full translation locked in at each sentence boundary
- Up to 3 completed captions on screen at once; older ones scroll off automatically
- Clock (top-left) and WebSocket connection status (top-right)
- Terminology version badge (bottom-right) — confirms the latest `terms.json` is active

**Fullscreen:** Double-click anywhere on the screen to toggle fullscreen.

**Recording:** Click **⏺ 录制** to begin recording all finalized captions. Click **⏹ 停止录制** to stop and download a `.doc` transcript containing timestamps, original text, and translations.



---

## Fallback Behaviour

The system degrades gracefully under poor network conditions or API errors:

| Level | Trigger | Behaviour |
|-------|---------|-----------|
| L1 | Normal operation | Full AI bilingual captions |
| L2 | Translation timeout (>4s) or Qwen API error | Displays original Chinese immediately with `[译文生成中...]`; silently retries and replaces with the translation when it arrives |
| L3 | ASR disconnect or network loss | Screen holds last subtitle and shows `● 重连中...`; gateway automatically restarts the ASR loop after a 3-second backoff |

The L2 timeout threshold is configurable via `TRANSLATE_TIMEOUT` (default: 4.0 seconds). If you use `qwen-max`, consider increasing this to 6–8 seconds.

---

## Monitor Center

For multi-room events, the **Monitor Center** role provides a live LAN dashboard of all active Subtitle Service laptops — no server or cloud infrastructure required.

- Displays room name, online status, screen client count, and terminology version per room
- Green dot = online; red dot = no heartbeat for 15+ seconds
- Dashboard refreshes every 3 seconds
- Discovery uses direct UDP unicast on port 47474 — each service laptop must have the monitor laptop's IP entered in the Monitor IP field
- The monitor window prominently displays **this computer's IP** to share with session operators

> **Firewall note (Windows):** The app automatically adds a Windows Firewall rule for UDP port 47474 on first launch. If rooms do not appear after 20 seconds, run the app as Administrator once, or allow it manually under Windows Firewall → Allow an app.

---

## Run from Source

Requires Python 3.10+.

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

Output is placed in `dist/AIInterpretation/` (Windows) or `dist/AIInterpretation.app` (macOS).

Automated builds for both platforms run via GitHub Actions on every version tag (`v*`).

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | *(required)* | Alibaba Cloud DashScope API key |
| `LANG_PAIR` | `zh-en` | Language pair: `zh-en` or `zh-ja` |
| `ASR_MODEL` | `paraformer-realtime-v2` | ASR model (see [ASR Models](#asr-models)) |
| `TRANSLATE_MODEL` | `qwen-plus` | Translation model (see [Translation Models](#translation-models)) |
| `TRANSLATE_TIMEOUT` | `4.0` | Seconds before L2 fallback triggers |
| `DISPLAY_MODE` | `both` | `en` (translated only), `zh` (original only), `both` |
| `ZH_FONT_SIZE` | `30` | Font size (px) for original-language text |
| `EN_FONT_SIZE` | `30` | Font size (px) for translated text |
| `ZH_COLOR` | `#7dd3fc` | Color for original-language text |
| `EN_COLOR` | `#4ade80` | Color for translated text |
| `BG_COLOR` | `#000000` | Screen background color |
| `PORT` | `8000` | HTTP and WebSocket port |
| `DISABLE_AUDIO` | *(unset)* | Set to `1` to disable microphone (test mode) |
| `PYAUDIO_DEVICE_INDEX` | *(system default)* | Audio input device index |
