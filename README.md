# AI-powered bilingual simultaneous interpretation for conference

Real-time speech recognition, AI translation, and big-screen subtitle display — end-to-end under 3 seconds.

---

## Demo

<!-- Insert demo video here -->

---

## Overview

SyncSubTranslate listens to a microphone, transcribes speech in real time using Alibaba Cloud ASR, translates each sentence with Qwen LLM, and pushes bilingual subtitles to a browser screen over WebSocket — ready for projection at any scale.

| | |
|---|---|
| **Language pairs** | Chinese ↔ English · Chinese ↔ Japanese |
| **Latency** | ≤ 3 seconds end-to-end |
| **Platforms** | Windows · macOS |
| **Infrastructure** | Zero — runs entirely on a single laptop |

---

## Download

Go to the [Releases](../../releases) page and download the latest version:

| Platform | File |
|----------|------|
| Windows | `AIInterpretation-Windows.exe` |
| macOS | `AIInterpretation-Mac.zip` |

**Windows:** Double-click `AIInterpretation-Windows.exe` to run directly — no installation needed.  
**macOS:** Extract the zip and open `AIInterpretation.app`. If macOS blocks it, go to System Settings → Privacy & Security → click "Open Anyway".

---

## Getting Started

### Step 1 — Get an API Key

SyncSubTranslate uses Alibaba Cloud DashScope. One key covers both speech recognition and translation.

1. Sign up at [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com/)
2. Go to **API Keys** → **Create API Key**
3. Copy the key — you will paste it into the app

New accounts receive free credits sufficient for a full conference day.

| Service | Rate |
|---------|------|
| Speech recognition | ¥0.018 / minute |
| Translation (Qwen) | ¥0.035 / 1,000 characters |

---

### Step 2 — Configure the Service

Launch the app and select **Subtitle Service**. Fill in the form:

**Gateway**

| Field | Description |
|-------|-------------|
| Room Name | A label for this session, e.g. "Main Hall" |
| API Key | Your DashScope key (masked after entry) |
| Monitor IP | *(Optional)* IP of the Monitor Center laptop on the same LAN |

**Display**

| Field | Options |
|-------|---------|
| Mode | Translated only / Original only / Both |
| Original font size | Any size in px |
| Translated font size | Any size in px |
| Original color | White / Red / Yellow / Light Yellow / Blue / Green / Pink / Leaf Green / Dark Blue |
| Translated color | Same 9 options |
| Background | Black / Dark Grey / Dark Blue |

**Audio**

| Field | Options |
|-------|---------|
| Microphone | Dropdown of active input devices; click ↻ to rescan |
| Language | Chinese ↔ English or Chinese ↔ Japanese |

**ASR Model** — see [Choosing an ASR Model](#choosing-an-asr-model)

**Translation Model** — see [Choosing a Translation Model](#choosing-a-translation-model)

> **Tip:** Your settings are saved automatically every time you start the service. Click **Use Last Settings** at the top to restore them instantly at the next session.

---

### Step 3 — Start and Display

1. Click **Start Service**
2. Click **Open Screen** — opens the subtitle display in your browser at `http://localhost:8000`
3. Double-click the browser window to go fullscreen
4. Connect to the projector or big screen

---

## Choosing an ASR Model

Three speech recognition models are available:

| Model | Best For |
|-------|----------|
| `paraformer-realtime-v2` | Stability-first; proven in production environments |
| `qwen3-asr-flash-realtime-2026-02-10` | Higher accuracy on mixed Chinese-English speech |
| `fun-asr-realtime-2026-02-28` | Alternative Realtime API backend; FunASR-based |

**`paraformer-realtime-v2`** — The classic DashScope SDK model. Mature, stable, and well-tested in conference environments. Recommended when reliability is the top priority.

**`qwen3-asr-flash-realtime-2026-02-10`** — Uses the newer OpenAI-compatible Realtime API. Delivers improved accuracy on mixed-language speech and includes server-side voice activity detection. Best when transcript quality matters most.

**`fun-asr-realtime-2026-02-28`** — Also uses the Realtime API path. A solid alternative if `qwen3-asr-flash` is at capacity or unavailable.

All three models work with any microphone — the app automatically resamples your mic's native audio to 16kHz mono before sending to the API.

---

## Choosing a Translation Model

Three Qwen LLM models are available:

| Model | Speed | Cost | Quality | Best For |
|-------|-------|------|---------|----------|
| `qwen-turbo` | Fastest | Lowest | Good | High-volume sessions, tight budgets |
| `qwen-plus` | Balanced | Medium | Very good | Most conferences *(default)* |
| `qwen-max` | Slowest | Highest | Best | Technical or policy-heavy sessions |

**`qwen-turbo`** — Translations typically arrive in under 1 second. Suitable when speaker pace is fast and content is straightforward. May produce slightly less nuanced phrasing on technical vocabulary.

**`qwen-plus`** *(recommended)* — Well-balanced for conference use. Handles professional terminology and mixed-language sentences reliably, with translation latency comfortably within the 4-second threshold.

**`qwen-max`** — The highest-quality model. Best for specialized terminology, formal speeches, and policy language. Slower response time increases the chance of triggering the L2 fallback on long sentences — consider the trade-off for your event.

All models respect the terminology dictionary in `gateway/terms.json`. Domain-specific terms are injected into every translation call regardless of which model is selected.

---

## Subtitle Screen

The browser display at `http://localhost:8000`:

- **Live partial text** — faintly shown while the speaker is mid-sentence
- **Finalized captions** — full translation locked in at each sentence boundary
- Clock top-left; WebSocket connection status top-right
- Terminology version badge confirms the latest `terms.json` is active

**Fullscreen:** Double-click anywhere on the screen.

**Recording:** Click **⏺ 录制** to start capturing all finalized captions. Click **⏹ 停止录制** to stop and download a `.doc` transcript with timestamps, original text, and translations.

---

## Terminology Customization

Edit `gateway/terms.json` at any time while the service is running:

```json
{
  "国创中心": "National Innovation Center",
  "新质生产力": "new quality productive forces",
  "大模型": "large language model"
}
```

Changes are detected and applied automatically — no restart required. The terminology version badge on the subtitle screen increments to confirm the reload.

---

## Fallback Behaviour

The system degrades gracefully under poor network or API conditions:

| Level | Trigger | Behaviour |
|-------|---------|-----------|
| L1 | Normal | Full AI bilingual captions |
| L2 | Translation timeout (>4s) or API error | Displays original Chinese immediately with `[译文生成中...]`; replaces with the translation when it arrives |
| L3 | ASR disconnect or network loss | Screen holds last subtitle, shows `● 重连中...`; gateway restarts ASR automatically with a 3-second backoff |

---

## Monitor Center

For multi-room events, the **Monitor Center** view provides a live LAN dashboard of all active Subtitle Service laptops — no server or cloud infrastructure required.

- Shows this computer's IP address to share with service operators
- Displays a card per room: online status, screen client count, terminology version
- Green = running · Amber = issue · Red = offline (no heartbeat for 15+ seconds)
- Refreshes every 3 seconds; rooms disappear immediately when a service is stopped

**Setup:** Enter the monitor laptop's IP into the Monitor IP field on each service laptop. The monitor laptop must be on the same LAN.

> **Firewall note (Windows):** The app automatically adds a Windows Firewall rule for UDP port 47474 on first launch. If rooms do not appear after 20 seconds, run the app as Administrator once, or allow it manually under Windows Firewall → Allow an app.

---

## App Settings

Click the **Settings** icon at the bottom of the sidebar to configure:

| Setting | Options |
|---------|---------|
| UI Language | English · 简体中文 · 繁體中文 |
| Theme | Light · Dark |

Language and theme changes apply instantly across the entire app without restarting.

---

## Run from Source

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python -m app
```

**macOS — install PortAudio first:**
```bash
brew install portaudio
pip install -r requirements.txt
python -m app
```

**Test without a microphone:**
```bash
set DISABLE_AUDIO=1 && python -m app   # Windows
DISABLE_AUDIO=1 python -m app          # macOS / Linux
```

---

## Docker (gateway only)

To run the gateway in a container without the desktop UI:

```bash
docker compose -f gateway/docker-compose.yml up
```

`gateway/terms.json` and `logs/` are bind-mounted — edit terms on the host for live hot-reload without rebuilding the image. Audio device passthrough via `/dev/snd` is supported on Linux and WSL2.

---

## Build from Source

```bash
pip install pyinstaller
python -m PyInstaller build.spec --clean --noconfirm
```

Output: `dist/AIInterpretation.exe` (Windows) or `dist/AIInterpretation.app` (macOS).

Automated builds for both platforms run via GitHub Actions on every version tag (`v*`) and are attached automatically to the GitHub Release.

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | *(required)* | Alibaba Cloud DashScope API key |
| `ASR_MODEL` | `paraformer-realtime-v2` | Speech recognition model |
| `TRANSLATE_MODEL` | `qwen-plus` | Qwen translation model |
| `TRANSLATE_TIMEOUT` | `4.0` | Seconds before L2 fallback triggers |
| `LANG_PAIR` | `zh-en` | `zh-en` or `zh-ja` |
| `DISPLAY_MODE` | `both` | `en` / `zh` / `both` |
| `ZH_FONT_SIZE` | `30` | Original text font size (px) |
| `EN_FONT_SIZE` | `30` | Translated text font size (px) |
| `ZH_COLOR` | `#7dd3fc` | Original text color |
| `EN_COLOR` | `#4ade80` | Translated text color |
| `BG_COLOR` | `#000000` | Screen background color |
| `PORT` | `8000` | HTTP and WebSocket port |
| `DISABLE_AUDIO` | *(unset)* | Set to `1` to disable microphone (test mode) |
| `PYAUDIO_DEVICE_INDEX` | *(system default)* | Audio input device index |
