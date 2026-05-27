# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec — works on Windows (.exe) and macOS (.app)
Build:  pyinstaller build.spec
Output: dist/AIInterpretation/
"""
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

APP_NAME = "AIInterpretation"

# ── Generate app icon from app/icon.py ────────────────────────────────────────
# The icon is drawn at runtime with Pillow; here we rasterise it into the
# static .ico (.icns on macOS) that PyInstaller embeds into the executable.
import sys as _sys
_sys.path.insert(0, ".")
_ICON_WIN  = None   # Windows .ico path
_ICON_MAC  = None   # macOS  .icns path

try:
    from app.icon import _draw as _draw_icon

    if sys.platform == "win32" or True:          # always generate .ico (cross-compile safe)
        _ico_path = "app_icon.ico"
        _img = _draw_icon(256)
        _img.save(
            _ico_path, format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
        _ICON_WIN = _ico_path
        print(f"[build] generated {_ico_path}")

    if sys.platform == "darwin":
        import os as _os, subprocess as _sp, shutil as _sh, tempfile as _tmp
        _iconset = _tmp.mkdtemp(suffix=".iconset")
        for _sz in [16, 32, 128, 256, 512]:
            _draw_icon(_sz).save(f"{_iconset}/icon_{_sz}x{_sz}.png")
            _draw_icon(_sz * 2).save(f"{_iconset}/icon_{_sz}x{_sz}@2x.png")
        _sp.run(["iconutil", "-c", "icns", _iconset, "-o", "app_icon.icns"], check=True)
        _sh.rmtree(_iconset)
        _ICON_MAC = "app_icon.icns"
        print(f"[build] generated app_icon.icns")

except Exception as _e:
    print(f"[build] WARNING: icon generation failed — {_e}")

# ── Collect customtkinter themes/images ───────────────────────────────────────
ctk_datas = collect_data_files("customtkinter")

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["app/__main__.py"],
    pathex=["."],
    binaries=collect_dynamic_libs("pyaudio"),
    datas=[
        *ctk_datas,
        ("gateway/terms.json", "gateway"),
        ("screen/index.html",  "screen"),
    ],
    hiddenimports=[
        # uvicorn / fastapi dynamic imports PyInstaller misses
        "uvicorn.logging",
        "uvicorn.loops", "uvicorn.loops.auto", "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http", "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan", "uvicorn.lifespan.on", "uvicorn.lifespan.off",
        "fastapi.responses", "fastapi.staticfiles", "fastapi.templating",
        "starlette.routing", "starlette.middleware", "starlette.middleware.cors",
        "starlette.responses", "starlette.background",
        # async / http
        "h11", "h11._connection", "h11._events",
        "anyio", "anyio.abc", "anyio._backends._asyncio",
        "anyio.streams.memory",
        # watchdog
        "watchdog.observers", "watchdog.observers.polling", "watchdog.events",
        # dashscope / dotenv
        "dashscope", "dashscope.audio.asr",
        "dotenv",
        # numpy / pyaudio / PIL
        "numpy", "numpy.core._methods", "numpy.lib.format",
        "pyaudio",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "unittest"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=False,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,   # macOS: don't convert argv to Apple events
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_ICON_WIN,         # embedded into the .exe on Windows
)

# ── macOS: wrap the onefile exe into a double-clickable .app bundle ───────────
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name=f"{APP_NAME}.app",
        icon=_ICON_MAC,
        bundle_identifier=f"com.{APP_NAME.lower()}",
        info_plist={
            "NSHighResolutionCapable": True,
            "NSMicrophoneUsageDescription": "Required for real-time speech recognition.",
        },
    )
