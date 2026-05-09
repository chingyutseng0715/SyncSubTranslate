# 部署 SOP — 现场操作流程

## 进场前（提前2小时）

### 1. 环境准备（Windows）
```bash
# 安装 Python 3.11+（如未安装）
# https://www.python.org/downloads/

# 安装 PyAudio（Windows 需先安装 PortAudio）
# 方法A（推荐）：使用预编译包
pip install pipwin
pipwin install pyaudio

# 方法B：下载 .whl 文件
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
# pip install PyAudio‑0.2.14‑cp311‑cp311‑win_amd64.whl

# 安装其他依赖
pip install -r requirements.txt
```

### 2. 配置 API Key
- 编辑 `gateway/.env`
- 填入 `DASHSCOPE_API_KEY=sk-xxxx`（从阿里云控制台获取）

### 3. 接线
```
麦克风/话筒 → 调音台输出 → USB声卡（Focusrite 2i2）→ 电脑USB
```
- 调音台输出电平：-12dBFS 至 -6dBFS（绿灯区）
- 避免超载（红灯）

### 4. 确认音频设备
```bash
python -c "import pyaudio; p=pyaudio.PyAudio(); [print(i, p.get_device_info_by_index(i)['name']) for i in range(p.get_device_count())]"
```
记录 USB声卡的设备编号，填入 `gateway/.env` → `PYAUDIO_DEVICE_INDEX=X`

---

## 开播流程

### 5. 启动网关
```bash
cd "C:\...\Speech Translate Tool"
python gateway/main.py
```
看到 `Gateway ready → http://localhost:8000/` 即成功。

### 6. 打开大屏
- 在大屏电脑浏览器中打开：`http://[网关IP]:8000/`
- 或直接打开：`screen/index.html`（需将 WS 地址改为网关 IP）
- **双击** 进入全屏模式
- 状态指示 `● 直播中`（绿色）= 正常连接

### 7. 校准测试
- 讲一段测试语音（约30秒）
- 确认：
  - [ ] 中文字幕出现（≤1.5秒首字延迟）
  - [ ] 英文翻译出现（≤3秒最终句延迟）
  - [ ] 术语显示正确

---

## 运行中巡检（每30分钟）

| 检查项 | 预期状态 |
|--------|---------|
| 大屏状态指示 | `● 直播中`（绿色） |
| 网关日志 | 无 ERROR 行 |
| 健康检查 | http://localhost:8000/health → `"status":"ok"` |
| CPU占用 | <50% |

---

## 收工

```bash
# Ctrl+C 停止网关
# 日志已自动保存至 logs/runtime_YYYYMMDD.jsonl
```

收工后将 `logs/` 目录打包存档，供会后精翻使用。
