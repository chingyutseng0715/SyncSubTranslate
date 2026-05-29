# SyncSubTranslate — Developer Reference

Real-time AI bilingual captioning for conference big screens.  
Version: **v1.1.15** (displayed in sidebar, `app/launcher.py:165`)

---

## Architecture

Two-process desktop app. The same executable runs in two modes:

```
python -m app               → UI mode  (CustomTkinter GUI)
python -m app --gateway N   → Gateway mode  (FastAPI server, spawned by UI)
```

`GatewayRunner` (`app/runner.py`) spawns the gateway as a subprocess, passing all config via environment variables. On a frozen PyInstaller build, the exe relaunches itself with `--gateway <device_index>`. In dev mode it runs `gateway/main.py` directly.

**No database.** All state is in-memory: terms dict, subtitle queue, WebSocket client list.

---

## File Map

| File | Role |
|------|------|
| `app/__main__.py` | Entry point; routes `--gateway` flag or starts UI |
| `app/launcher.py` | `MainWindow` — single window shell with sidebar + swappable views |
| `app/service.py` | `ServiceView` — all subtitle service config and start/stop |
| `app/monitor.py` | `MonitorView` — LAN dashboard of all service nodes |
| `app/settings.py` | `SettingsView` — language and theme toggles |
| `app/runner.py` | `GatewayRunner` — subprocess lifecycle for the gateway |
| `app/heartbeat.py` | `HeartbeatSender` / `HeartbeatReceiver` — UDP status protocol |
| `app/i18n.py` | Translation strings for en / zh_cn / zh_tw; `t(key)` lookup |
| `app/theme.py` | Light/Dark palette tokens; `set_theme()` fires callbacks |
| `app/paths.py` | Platform-correct paths for settings, logs, error.log |
| `app/icon.py` | App icon drawn at runtime with Pillow (no image file needed) |
| `gateway/main.py` | FastAPI gateway: ASR → translation → WebSocket broadcast |
| `gateway/terms.json` | Terminology dict `{zh: translation}` — hot-reloaded by watchdog |
| `gateway/.env` | API key and env overrides (never commit real keys) |
| `screen/index.html` | Browser subtitle display — single HTML file, no build step |
| `build.spec` | PyInstaller spec; generates icon at build time |
| `.github/workflows/build.yml` | CI: Windows + macOS builds on `v*` tags |

---

## APIs Required

| API | Where to get |
|-----|-------------|
| `DASHSCOPE_API_KEY` | https://dashscope.console.aliyun.com/ → API Keys → Create API Key |

One key covers both ASR and translation.

---

## Environment Variables

All passed to the gateway subprocess via `GatewayRunner.start()`. Can also be set in `gateway/.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | *(required)* | Alibaba Cloud DashScope key |
| `ASR_MODEL` | `paraformer-realtime-v2` | ASR model (see ASR Backends below) |
| `TRANSLATE_MODEL` | `qwen-plus` | Qwen model for translation |
| `TRANSLATE_TIMEOUT` | `4.0` | Seconds before L2 fallback |
| `LANG_PAIR` | `zh-en` | `zh-en` or `zh-ja` |
| `DISPLAY_MODE` | `both` | `en` / `zh` / `both` |
| `ZH_FONT_SIZE` | `30` | Original text font size (px) |
| `EN_FONT_SIZE` | `30` | Translated text font size (px) |
| `ZH_COLOR` | `#7dd3fc` | Original text color |
| `EN_COLOR` | `#4ade80` | Translated text color |
| `BG_COLOR` | `#000000` | Screen background color |
| `PORT` | `8000` | Gateway HTTP/WS port |
| `PYAUDIO_DEVICE_INDEX` | *(system default)* | Audio input device index |
| `DISABLE_AUDIO` | *(unset)* | Set to `1` for test/demo mode (no mic) |
| `AI_DATA_DIR` | *(auto)* | User data dir injected by runner on frozen build |

---

## ASR Backends

Two separate code paths selected at startup based on `ASR_MODEL`:

```python
loop_fn = _run_asr_loop if ASR_MODEL.startswith("paraformer") else _run_realtime_asr_loop
```

**`_run_asr_loop`** — DashScope SDK `Recognition` class. Used for `paraformer-realtime-v2`.

**`_run_realtime_asr_loop`** — OpenAI-compatible Realtime API over WebSocket (`websocket-client`). Used for `qwen3-asr-flash-realtime-2026-02-10` and `fun-asr-realtime-2026-02-28`. Implements server-side VAD (threshold 0.2, silence 800ms), delta streaming.

Both backends:
- Auto-detect microphone native sample rate and channel count
- Resample to 16kHz mono via numpy linear interpolation (`_to_mono_16k`)
- Restart automatically on any error with 3s backoff (infinite loop — this is the L3 recovery)

---

## Subtitle Processing (`gateway/main.py: _process_loop`)

State machine for partial → final transitions:

- `committed_len` tracks how many characters of the current ASR stream have already been pushed as mini-finals
- **Partial event**: shows `zh[committed_len:]` as the live partial
- **Sentence boundary** (`。？！.?!` found in new text): pushes text up to boundary as a final, updates `committed_len`, broadcasts remainder as new partial
- **Force-push**: if uncommitted text exceeds 25 CJK chars or 20 English words, push without punctuation
- **ASR final event**: translates `zh[committed_len:]` (the uncommitted remainder), resets `committed_len = 0`
- **Queue draining**: while awaiting translation, stale partials are dropped — `_drain()` keeps the newest partial or the first final encountered

---

## Translation (`gateway/main.py: _call_qwen_sync`)

- Runs in `asyncio.to_thread` with `TRANSLATE_TIMEOUT` timeout
- **Attempt 1**: full system prompt + user message wrapped in `<source>` tags
- **Attempt 2**: bare `逐字翻译` prompt — fires if attempt 1 fails or returns empty (handles model refusals)
- System prompt injects `terms.json` contents on every call
- Chinese-Japanese mode adds a note to not copy English terms verbatim
- Timeout → returns `""` → `_process_loop` shows `[译文生成中...]` (L2 fallback)

---

## Terminology System

- `gateway/terms.json` — flat `{zh: translation}` JSON object
- Watched by `watchdog.Observer` with 0.15s debounce on modification
- `_terms_version` increments on every reload
- Thread-safe via `_terms_lock`
- Injected into the Qwen system prompt on every call
- Version number sent in every WebSocket payload → shown on screen badge and monitor cards

---

## Heartbeat Protocol (`app/heartbeat.py`)

Service laptops → monitor laptop via UDP unicast, port **47474**, every **5 seconds**.

```json
{"room": "Main Hall", "ip": "192.168.1.5", "status": "ok", "ws_clients": 1, "terms_version": 3}
```

On stop: sends `{"status": "stopped"}` so the monitor removes the card immediately.  
Monitor marks a room offline after **15 seconds** of silence.  
If `target_ip` is `None` (no Monitor IP entered), `HeartbeatSender` is a no-op.

---

## HTTP Endpoints

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/` | GET | `screen/index.html` |
| `/ws` | WebSocket | Subtitle push stream |
| `/health` | GET | `{status, terms_entries, terms_version, screen_clients}` |
| `/config` | GET | `{display_mode, zh_font_size, en_font_size, zh_color, en_color, bg_color}` |
| `/terms` | GET | `{version, terms}` |
| `/logs/clear` | POST | Deletes all `logs/runtime_*.jsonl` |

---

## Browser Screen (`screen/index.html`)

Single self-contained HTML file. No framework, no build step.

- Connects to `ws://<host>/ws`; auto-reconnects every 2s; pings every 10s
- Fetches `/config` on connect → applies font sizes, colors, display mode as CSS variables
- **Partial**: faded (opacity 0.45), Chinese only, min-height reserved to prevent layout jump
- **Finals**: up to 30 kept in JS array; renders bottom-aligned
- **Recording**: collects finals into `recordedLines[]`; downloads `.doc` (HTML-in-Word format) with timestamp/zh/en table
- **Fullscreen**: double-click anywhere
- **Tab close**: `navigator.sendBeacon('/logs/clear')` wipes session logs
- Status states: `● 直播中` (green) / `● 重连中...` (yellow) / `● 连接异常` (red)

---

## UI Architecture

`MainWindow` (`app/launcher.py`) is a single window with a fixed sidebar (214px) and swappable content views. Views are created lazily on first navigation and hidden/shown via `grid()` / `grid_remove()`. Each view registers `on_change` (i18n) and `on_theme_change` callbacks and updates widgets in-place — no rebuild.

**Theme system** (`app/theme.py`): two palettes (`_LIGHT`, `_DARK`) with named tokens (BG, SURFACE, ACCENT, TEXT, BORDER, etc.). `set_theme()` fires callbacks + saves to `last_settings.json`. Status colors (green/amber/red) are semantic constants that never change with the theme.

**i18n system** (`app/i18n.py`): three locales (`en`, `zh_cn`, `zh_tw`). `set_lang()` fires callbacks. `t(key)` falls back to `en` for missing keys.

---

## Settings Persistence (`last_settings.json`)

Saved on every `Start Service` click. Loaded by "Use Last Settings" button.

Keys: `room`, `api_key`, `lang`, `mic`, `monitor_ip`, `display`, `zh_size`, `en_size`, `zh_color`, `en_color`, `bg`, `asr_model`, `translate_model`, `app_theme`.

Mic is saved by **name** (not index) — indices change when devices are plugged/unplugged. Restore logic: exact match first, then fuzzy substring fallback.

Path: project root in dev; `%APPDATA%/AIInterpretation/last_settings.json` in frozen build.

---

## Microphone Enumeration (`app/service.py: _win_active_mics`)

On Windows, uses raw COM (`IMMDeviceEnumerator`) to list only `DEVICE_STATE_ACTIVE` capture endpoints — the same set Windows Sound Settings shows. Falls back to PyAudio WASAPI enumeration on non-Windows or COM failure. Default mic is placed first in the list.

---

## Logging

Session logs: `logs/runtime_YYYYMMDD.jsonl` — one JSON object per finalized caption.

```json
{"status": "final", "zh": "...", "en": "...", "ts": "2026-06-02T10:30:00", "terms_version": 3, "locked": true}
```

Wiped automatically on gateway shutdown (FastAPI lifespan) and when the browser tab closes (`/logs/clear`).

Crash traces: `error.log` (written by `app/__main__.py` exception handler).

---

## Docker (gateway only)

```bash
cd SyncSubTranslate
docker compose -f gateway/docker-compose.yml up
```

`terms.json` and `logs/` are bind-mounted — edit terms.json on the host for hot-reload without rebuilding. Audio device passthrough via `/dev/snd` (Linux/WSL2 only).

---

## Build & Release

```bash
pip install pyinstaller
python -m PyInstaller build.spec --clean --noconfirm
```

- `build.spec` rasterizes the app icon from `app/icon.py` at build time (`.ico` for Windows, `.icns` for macOS)
- Output: `dist/AIInterpretation.exe` (Windows) or `dist/AIInterpretation.app` (macOS)
- macOS `.app` includes `NSMicrophoneUsageDescription` in `Info.plist`
- GitHub Actions builds both platforms on every `v*` tag push and attaches them to the GitHub Release

---

## Quick Start (dev)

```bash
pip install -r requirements.txt
python -m app
```

**macOS:**
```bash
brew install portaudio && pip install -r requirements.txt
python -m app
```

**No microphone (test mode):**
```bash
set DISABLE_AUDIO=1 && python -m app   # Windows
DISABLE_AUDIO=1 python -m app          # macOS/Linux
```
