# AI Conference Real-time Interpretation System
# AI 会议实时同传字幕系统

Real-time bilingual (Chinese ↔ English) captioning for conference big screens.  
Microphone → Alibaba Cloud ASR → Qwen LLM translation → WebSocket → browser display.

---

## Features

- **Real-time ASR** using Alibaba Cloud `paraformer-realtime-v2` (Chinese/English mixed)
- **Partial/Final state machine** — partial results shown grayed while speaking; final locks in with English translation
- **Qwen LLM translation** with conference terminology injection
- **Terminology hot-reload** — edit `gateway/terms.json` while running, changes apply in under 60 seconds, no restart needed
- **Auto-reconnect** — screen and ASR both recover automatically from network drops
- **L2 fallback** — if translation times out (>4s), shows original Chinese + `[译文生成中...]` automatically
- **Single-file screen** — `screen/index.html`, open in any browser, double-click for fullscreen
- **No database** — all state is in-memory; subtitle logs written to `logs/` as JSONL

---

## Project Structure

```
.
├── gateway/
│   ├── main.py            # FastAPI backend: audio capture, ASR, translation, WebSocket
│   ├── terms.json         # Terminology dictionary {Chinese: English} — hot-reloadable
│   ├── .env               # API keys and config (not committed)
│   ├── docker-compose.yml # One-command Docker deploy
│   └── Dockerfile
├── screen/
│   └── index.html         # Big-screen subtitle display (open in browser)
├── docs/
│   ├── 部署SOP.md         # On-site setup and operation guide
│   └── 应急预案手册.md     # L1/L2/L3 incident response playbook
├── logs/                  # Auto-created; runtime subtitle logs (JSONL)
├── requirements.txt
└── .gitignore
```

---

## Requirements

- Python 3.10+
- Alibaba Cloud DashScope API key (covers both ASR and Qwen translation)
  - Get one at: https://dashscope.console.aliyun.com/ → API Keys
  - New accounts receive ¥200–500 free credits (covers the full event)

---

## Setup

### 1. Install dependencies

**Windows** — PyAudio requires PortAudio. If `pip install pyaudio` fails:
```bash
pip install pipwin
pipwin install pyaudio
```

Then install the rest:
```bash
pip install -r requirements.txt
```

### 2. Configure API key

Fill in `gateway/.env`:
```
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 3. (Optional) Select audio input device

List available devices:
```bash
python -c "import pyaudio; p=pyaudio.PyAudio(); [print(i, p.get_device_info_by_index(i)['name']) for i in range(p.get_device_count()) if p.get_device_info_by_index(i)['maxInputChannels'] > 0]"
```

Set the index in `gateway/.env`:
```
PYAUDIO_DEVICE_INDEX=1
```

Leave blank to use the system default input.

### 4. Run

```bash
python gateway/main.py
```

### 5. Open the screen

Open `http://localhost:8000/` in the browser on the display machine.  
Double-click anywhere for fullscreen.

---

## Testing Without a Microphone

```bash
# Start gateway without audio capture
set DISABLE_AUDIO=1 && python gateway/main.py
```

Then push test subtitles from another terminal:
```python
import asyncio, websockets, json

async def demo():
    async with websockets.connect('ws://localhost:8000/ws') as ws:
        await ws.send(json.dumps({'status': 'partial', 'zh': '欢迎来到国创中心大会', 'en': '', 'locked': False}))
        import time; time.sleep(2)
        await ws.send(json.dumps({'status': 'final', 'zh': '欢迎来到国创中心大会。', 'en': 'Welcome to the National Innovation Center Conference.', 'locked': True}))

asyncio.run(demo())
```

---

## Terminology Hot-Reload

Edit `gateway/terms.json` at any time while the gateway is running:
```json
{
  "国创中心": "National Innovation Center",
  "新质生产力": "new quality productive forces"
}
```
Changes are picked up automatically within ~15 seconds. No restart required.

---

## Configuration Reference (`gateway/.env`)

| Variable | Default | Description |
|---|---|---|
| `DASHSCOPE_API_KEY` | *(required)* | Alibaba Cloud DashScope key |
| `TRANSLATE_MODEL` | `qwen-plus` | `qwen-turbo` / `qwen-plus` / `qwen-max` |
| `TRANSLATE_TIMEOUT` | `4.0` | Seconds before L2 fallback kicks in |
| `PORT` | `8000` | HTTP and WebSocket port |
| `DISABLE_AUDIO` | *(unset)* | Set to `1` to disable mic (test mode) |
| `PYAUDIO_DEVICE_INDEX` | *(system default)* | Audio input device index |

---

## Docker (Linux / WSL2)

```bash
cd gateway
docker-compose up -d
```

Audio device passthrough requires Linux. See `gateway/docker-compose.yml` for device configuration.

---

## Fallback Levels

| Level | Trigger | Behaviour |
|---|---|---|
| L1 | Normal | AI bilingual captions, full pipeline |
| L2 | Translation timeout or API rate limit | Shows Chinese original + `[译文生成中...]`, resumes automatically |
| L3 | ASR disconnect / network loss | Screen shows `● 重连中...`, gateway auto-restarts ASR (3s backoff) |

See `docs/应急预案手册.md` for manual intervention procedures.
