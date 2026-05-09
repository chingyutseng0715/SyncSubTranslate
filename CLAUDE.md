# AI Conference Real-time Interpretation System

Real-time bilingual (Chinese ↔ English) captioning for conference big screens.

## Architecture
Single-node gateway: microphone → Alibaba Cloud ASR → Qwen LLM → WebSocket → browser.
No database. All state is in-memory (terms dict, subtitle queue, WebSocket client list).

## Key Files
| File | Purpose |
|------|---------|
| `gateway/main.py` | FastAPI gateway: audio capture, ASR, translation, WebSocket push |
| `gateway/terms.json` | Terminology dict `{zh: en}` — edit live, reloads in <60s |
| `gateway/.env` | API keys and config (never commit real keys) |
| `screen/index.html` | Big-screen HTML — open in browser, double-click for fullscreen |
| `logs/runtime_YYYYMMDD.jsonl` | Auto-created subtitle log (zh+en pairs, timestamped) |

## APIs Required
| API | Where to get |
|-----|-------------|
| `DASHSCOPE_API_KEY` | https://dashscope.console.aliyun.com/ → API Keys → Create API Key |

This single key covers both:
- **ASR**: paraformer-realtime-v2 (real-time speech recognition, ¥0.018/min)
- **Translation**: Qwen (qwen-plus model, ¥0.035/千字符)

New accounts get ¥200–500 in free credits which covers the full event.

## Quick Start
```bash
# 1. Install dependencies (Windows: install PortAudio first — see docs/部署SOP.md)
pip install -r requirements.txt

# 2. Set your API key
#    Edit gateway/.env → set DASHSCOPE_API_KEY=sk-xxxx

# 3. Run gateway
python gateway/main.py

# 4. Open screen in browser
#    http://localhost:8000/
#    (or open screen/index.html directly)
```

## Test Without Microphone
```bash
# Start gateway without audio
set DISABLE_AUDIO=1 && python gateway/main.py

# Push test subtitles from another terminal
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

## Fallback Behaviour (Risk Levels)
| Level | Trigger | Behaviour |
|-------|---------|-----------|
| L1 | Normal | AI bilingual captions |
| L2 | Translation timeout >4s or API 429 | Shows original Chinese + `[译文生成中...]` automatically |
| L3 | ASR disconnect / network loss | Gateway auto-restarts ASR loop (3s backoff), screen shows `● 重连中...` and holds last subtitle |

## Terms Hot-Reload
Edit `gateway/terms.json` at any time. The `watchdog` file watcher detects changes and reloads atomically within ~15 seconds. No restart needed.

## Environment Variables (gateway/.env)
| Variable | Default | Description |
|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | *(required)* | Alibaba Cloud DashScope API key |
| `TRANSLATE_MODEL` | `qwen-plus` | Qwen model (`qwen-turbo`/`qwen-plus`/`qwen-max`) |
| `TRANSLATE_TIMEOUT` | `4.0` | Seconds before L2 fallback |
| `PORT` | `8000` | Gateway HTTP/WS port |
| `DISABLE_AUDIO` | *(unset)* | Set to `1` to disable microphone (test mode) |
| `PYAUDIO_DEVICE_INDEX` | *(system default)* | Audio input device index |

## Listing Audio Devices (Windows)
```bash
python -c "import pyaudio; p=pyaudio.PyAudio(); [print(i, p.get_device_info_by_index(i)['name']) for i in range(p.get_device_count())]"
```
Set `PYAUDIO_DEVICE_INDEX` in `.env` to the index of your USB audio interface.
