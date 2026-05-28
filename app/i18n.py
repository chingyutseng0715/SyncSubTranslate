"""
Minimal i18n module.
Usage:
    from app.i18n import t, set_lang, on_change, current
    label_text = t("room_name")          # → translated string
    set_lang("zh_cn")                    # → fires all on_change callbacks
    on_change(my_view._apply_lang)       # → register a refresh callback
"""
from __future__ import annotations

_LANG: str = "en"
_CALLBACKS: list = []

# ── Translation table ──────────────────────────────────────────────────────────
_T: dict[str, dict[str, str]] = {
    "en": {
        # Sidebar
        "interp_system":    "Interpretation System",
        "main_section":     "MAIN",
        "subtitle_service": "Subtitle Service",
        "monitor_center":   "Monitor Center",
        "settings":         "Settings",
        # Service — header buttons
        "use_last":         "Use Last Settings",
        "open_screen":      "Open Screen",
        "start_service":    "▶  Start Service",
        "stop_service":     "⏹  Stop Service",
        # Service — status
        "status_idle":      "● Not started",
        "status_starting":  "● Starting...",
        "status_running":   "● Running",
        "status_stopped":   "● Stopped",
        "status_no_gw":     "● Gateway not responding",
        # Service — sections
        "sec_gateway":      "GATEWAY",
        "sec_display":      "DISPLAY",
        "sec_audio":        "AUDIO",
        # Service — gateway fields
        "room_name":        "Room Name",
        "api_key":          "API Key",
        "monitor_ip":       "Monitor IP",
        # Service — display fields
        "mode":             "Mode",
        "orig_size":        "Orig. Size",
        "trans_size":       "Trans. Size",
        "orig_color":       "Orig. Color",
        "trans_color":      "Trans. Color",
        "background":       "Background",
        # Service — audio fields
        "microphone":       "Microphone",
        "lang_pair":        "Language",
        # Service — ASR model
        "sec_asr":          "ASR MODEL",
        "asr_model":        "Model",
        # Service — translation model
        "sec_translate":    "TRANSLATION MODEL",
        "translate_model":  "Model",
        # Monitor
        "mon_subtitle":     "Live status of Subtitle Service nodes on the LAN",
        "waiting_hb":       "Waiting for heartbeats...",
        "this_ip":          "This computer's IP address:",
        "ip_hint":          "← Enter this into each Subtitle Service laptop's Monitor IP field",
        "footer_hint":      "Updates every 3 s  ·  Rooms silent for 15 s+ are flagged offline",
        # Settings
        "settings_sub":     "Configure application preferences",
        "cat_system":       "SYSTEM",
        "ui_language":      "Language",
        "lang_en":          "English",
        "lang_zh_cn":       "Simplified Chinese",
        "lang_zh_tw":       "Traditional Chinese",
        "theme_mode":       "Theme",
        "theme_light":      "Light",
        "theme_dark":       "Dark",
    },

    "zh_cn": {
        "interp_system":    "字幕翻译系统",
        "main_section":     "主菜单",
        "subtitle_service": "字幕服务",
        "monitor_center":   "监控中心",
        "settings":         "设置",
        "use_last":         "使用上次设置",
        "open_screen":      "打开字幕屏",
        "start_service":    "▶  启动服务",
        "stop_service":     "⏹  停止服务",
        "status_idle":      "● 未启动",
        "status_starting":  "● 启动中...",
        "status_running":   "● 运行中",
        "status_stopped":   "● 已停止",
        "status_no_gw":     "● 网关无响应",
        "sec_gateway":      "网关设置",
        "sec_display":      "显示设置",
        "sec_audio":        "音频设置",
        "room_name":        "房间名称",
        "api_key":          "API 密钥",
        "monitor_ip":       "监控 IP",
        "mode":             "显示模式",
        "orig_size":        "原文字号",
        "trans_size":       "译文字号",
        "orig_color":       "原文颜色",
        "trans_color":      "译文颜色",
        "background":       "背景颜色",
        "microphone":       "麦克风",
        "lang_pair":        "语言",
        "sec_asr":          "识别模型",
        "asr_model":        "模型",
        "sec_translate":    "翻译模型",
        "translate_model":  "模型",
        "mon_subtitle":     "局域网字幕服务节点实时状态",
        "waiting_hb":       "等待心跳包...",
        "this_ip":          "本机 IP 地址：",
        "ip_hint":          "← 请将此 IP 填入各字幕服务电脑的监控 IP 字段",
        "footer_hint":      "每 3 秒更新  ·  超过 15 秒无响应的房间将标记为离线",
        "settings_sub":     "配置应用程序偏好",
        "cat_system":       "系统",
        "ui_language":      "界面语言",
        "lang_en":          "English",
        "lang_zh_cn":       "简体中文",
        "lang_zh_tw":       "繁体中文",
        "theme_mode":       "主题",
        "theme_light":      "浅色",
        "theme_dark":       "深色",
    },

    "zh_tw": {
        "interp_system":    "字幕翻譯系統",
        "main_section":     "主選單",
        "subtitle_service": "字幕服務",
        "monitor_center":   "監控中心",
        "settings":         "設定",
        "use_last":         "使用上次設定",
        "open_screen":      "開啟字幕螢幕",
        "start_service":    "▶  啟動服務",
        "stop_service":     "⏹  停止服務",
        "status_idle":      "● 未啟動",
        "status_starting":  "● 啟動中...",
        "status_running":   "● 執行中",
        "status_stopped":   "● 已停止",
        "status_no_gw":     "● 閘道無回應",
        "sec_gateway":      "閘道設定",
        "sec_display":      "顯示設定",
        "sec_audio":        "音訊設定",
        "room_name":        "房間名稱",
        "api_key":          "API 金鑰",
        "monitor_ip":       "監控 IP",
        "mode":             "顯示模式",
        "orig_size":        "原文字型",
        "trans_size":       "譯文字型",
        "orig_color":       "原文顏色",
        "trans_color":      "譯文顏色",
        "background":       "背景顏色",
        "microphone":       "麥克風",
        "lang_pair":        "語言",
        "sec_asr":          "識別模型",
        "asr_model":        "模型",
        "sec_translate":    "翻譯模型",
        "translate_model":  "模型",
        "mon_subtitle":     "區域網路字幕服務節點即時狀態",
        "waiting_hb":       "等待心跳包...",
        "this_ip":          "本機 IP 位址：",
        "ip_hint":          "← 請將此 IP 填入各字幕服務電腦的監控 IP 欄位",
        "footer_hint":      "每 3 秒更新  ·  超過 15 秒無回應的房間將標記為離線",
        "settings_sub":     "設定應用程式偏好",
        "cat_system":       "系統",
        "ui_language":      "介面語言",
        "lang_en":          "English",
        "lang_zh_cn":       "簡體中文",
        "lang_zh_tw":       "繁體中文",
        "theme_mode":       "主題",
        "theme_light":      "淺色",
        "theme_dark":       "深色",
    },
}


def t(key: str) -> str:
    """Return the translated string for the current language."""
    return _T.get(_LANG, _T["en"]).get(key, _T["en"].get(key, key))


def current() -> str:
    return _LANG


def set_lang(lang: str) -> None:
    global _LANG
    if lang not in _T:
        return
    _LANG = lang
    for cb in list(_CALLBACKS):
        try:
            cb()
        except Exception:
            pass


def on_change(callback) -> None:
    if callback not in _CALLBACKS:
        _CALLBACKS.append(callback)


def remove_callback(callback) -> None:
    if callback in _CALLBACKS:
        _CALLBACKS.remove(callback)
