# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec — works on Windows (.exe) and macOS (.app)
Build:  pyinstaller build.spec
Output: dist/AIInterpretation/
"""
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

APP_NAME = "AIInterpretation"

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
)

# ── macOS: wrap the onedir folder into a double-clickable .app bundle ─────────
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=None,
        bundle_identifier=f"com.{APP_NAME.lower()}",
        info_plist={
            "NSHighResolutionCapable": True,
            "NSMicrophoneUsageDescription": "Required for real-time speech recognition.",
        },
    )
