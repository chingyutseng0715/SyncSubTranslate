# AI Conference Real-time Interpretation System

Real-time bilingual (Chinese ↔ English/Japanese) captioning for conference big screens.

## Architecture

Two-process desktop app:
- **Desktop UI** (`app/`) — CustomTkinter GUI, runs as the main process
- **Gateway** (`gateway/main.py`) — FastAPI subprocess spawned by the UI; handles audio capture, ASR, translation, and WebSocket push to the browser screen

No database. All state is in-memory (terms dict, subtitle queue, WebSocket client list).  
Gateway is launched via `subprocess.Popen` by `GatewayRunner`; it is killed when the user clicks Stop or closes the app.

## Key Files

| File | Purpose |
|------|---------|
| `app/__main__.py` | Entry point; initializes CustomTkinter root and opens `LauncherWindow` |
| `app/launcher.py` | Role-selection screen: "Subtitle Service" or "Monitor Center" |
| `app/service.py` | Subtitle Service window — mic picker, display config, start/stop gateway |
| `app/monitor.py` | Monitor Center window — live dashboard of service laptops on the LAN |
| `app/runner.py` | `GatewayRunner` — spawns/terminates `gateway/main.py` as a subprocess |
| `app/heartbeat.py` | `HeartbeatSender` / `HeartbeatReceiver` — UDP status protocol between service and monitor laptops |
| `gateway/main.py` | FastAPI gateway: audio capture → ASR → translation → WebSocket broadcast |
| `gateway/terms.json` | Terminology dict `{zh: translation}` — edit live, hot-reloads in ~15s via watchdog |
| `gateway/.env` | API keys and env config (never commit real keys) |
| `screen/index.html` | Big-screen HTML — fetches display config from `/config`, connects to `/ws` |
| `build.spec` | PyInstaller spec for single-folder bundled executables |
| `.github/workflows/build.yml` | CI: builds Windows + macOS releases on `v*` tags |

## APIs Required

| API | Where to get |
|-----|-------------|
| `DASHSCOPE_API_KEY` | https://dashscope.console.aliyun.com/ → API Keys → Create API Key |

One key covers both:
- **ASR**: `paraformer-realtime-v2` (real-time speech recognition, ¥0.018/min)
- **Translation**: Qwen (`qwen-plus` default, ¥0.035/千字符)

## Quick Start (from source)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the desktop app
python -m app
```

The UI will prompt for the API key before starting the gateway.

## Test Without Microphone

```bash
# Start the app with audio disabled
set DISABLE_AUDIO=1 && python -m app   # Windows
DISABLE_AUDIO=1 python -m app          # macOS/Linux
```

Then push test subtitles from another terminal:
```bash
python -c "
import asyncio, websockets, json, time

async def demo():
    async with websockets.connect('ws://localhost:8000/ws') as ws:
        await ws.send(json.dumps({'status':'partial','zh':'这是识别中的文字...','en':'','locked':False}))
        time.sleep(1.5)
        await ws.send(json.dumps({'status':'final','zh':'欢迎来到国创中心大会。','en':'Welcome to the National Innovation Center Conference.','locked':True}))
        time.sleep(2)

asyncio.run(demo())
"
```

## Sentence Boundary Logic

The `_process_loop` in `gateway/main.py` handles partial → final state:

- **Partial events**: buffered; only the portion after the last committed offset is shown
- **Sentence break**: pushes a mini-final when sentence-ending punctuation (`。？！.?!`) appears mid-partial
- **Force-push**: pushes without punctuation when uncommitted text exceeds 25 CJK characters or 20 English words
- **ASR final event**: translates and pushes any uncommitted remainder; resets `committed_len` to 0

Translation runs in a thread via `asyncio.to_thread` with a 4s timeout (configurable). On timeout → L2 fallback (`[译文生成中...]`). Qwen is called with a system prompt that wraps input in `<source>` tags; a bare-prompt retry fires if the first attempt fails or returns empty.

## Heartbeat Protocol

Service laptops send UDP datagrams every 5s to the monitor laptop's IP (entered by the user in the Monitor IP field). The monitor listens on UDP port 47474. Heartbeat payload:

```json
{"room": "Main Hall", "ip": "192.168.1.5", "status": "ok", "ws_clients": 1, "terms_version": 3}
```

A room is marked as offline after 15s of silence. On service stop, a `"status": "stopped"` packet is sent so the monitor removes the room immediately.

**Important:** Heartbeats are targeted (unicast), not broadcast. The monitor's IP must be entered manually in the service window. If left blank, the sender is a no-op (standalone mode).

## Environment Variables (gateway/.env or passed via subprocess env)

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | *(required)* | Alibaba Cloud DashScope API key |
| `LANG_PAIR` | `zh-en` | `zh-en` or `zh-ja` |
| `DISPLAY_MODE` | `en` | `en` (translated only), `zh` (original only), `both` |
| `ZH_FONT_SIZE` | `30` | Font size px for original-language text |
| `EN_FONT_SIZE` | `30` | Font size px for translated text |
| `ZH_COLOR` | `#ffff00` | CSS color for original-language text |
| `EN_COLOR` | `#4ade80` | CSS color for translated text |
| `BG_COLOR` | `#000000` | CSS color for screen background |
| `TRANSLATE_MODEL` | `qwen-plus` | Qwen model (`qwen-turbo`/`qwen-plus`/`qwen-max`) |
| `TRANSLATE_TIMEOUT` | `4.0` | Seconds before L2 fallback |
| `PORT` | `8000` | Gateway HTTP/WS port |
| `DISABLE_AUDIO` | *(unset)* | Set to `1` to disable microphone (test mode) |
| `PYAUDIO_DEVICE_INDEX` | *(system default)* | Audio input device index |

All display variables (DISPLAY_MODE, font sizes, colors) are set by the service window UI and passed to the gateway subprocess — they do not need to be in `.env` for normal use.

## Audio Device Discovery

```bash
python -c "import pyaudio; p=pyaudio.PyAudio(); [print(i, p.get_device_info_by_index(i)['name']) for i in range(p.get_device_count())]"
```

The gateway reads the device's native sample rate and channel count, then resamples to 16kHz mono via numpy linear interpolation before sending to ASR.

## Fallback Behaviour

| Level | Trigger | Behaviour |
|-------|---------|-----------|
| L1 | Normal | Full AI bilingual captions |
| L2 | Translation timeout >4s or Qwen error | Shows original Chinese + `[译文生成中...]` automatically |
| L3 | ASR disconnect / network loss | Gateway auto-restarts ASR loop (3s backoff); screen shows `● 重连中...` and holds last subtitle |

## Gateway HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves `screen/index.html` |
| `/ws` | WS | WebSocket for subtitle push |
| `/health` | GET | Returns `{status, terms_entries, terms_version, screen_clients}` |
| `/config` | GET | Returns display config `{display_mode, zh_font_size, en_font_size, zh_color, en_color, bg_color}` |
| `/terms` | GET | Returns `{version, terms}` |
| `/logs/clear` | POST | Deletes all `logs/runtime_*.jsonl` files |

The browser screen fetches `/config` on WebSocket connect to apply display settings, and calls `/logs/clear` via `navigator.sendBeacon` on tab close.

## Logging

Session logs are written to `logs/runtime_YYYYMMDD.jsonl` (one JSON object per final caption, with `zh`, `en`, `ts`, `terms_version`). Logs are wiped on gateway shutdown (FastAPI lifespan teardown) and when the browser tab closes.

## Build & Packaging

```bash
pip install pyinstaller
python -m PyInstaller build.spec --clean --noconfirm
```

The spec bundles `gateway/` and `screen/` as datas into `_internal/`. When running frozen, `gateway/main.py` detects `sys.frozen` and resolves paths relative to `sys._MEIPASS`. The bundled exe relaunches itself with `--gateway <device_index>` to start the gateway subprocess.

Automated builds trigger on `v*` tags via `.github/workflows/build.yml` and produce release artifacts for Windows and macOS.
