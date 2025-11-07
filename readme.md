# UWP Package Extractor (GUI)

This project is a GUI wrapper for the open-source WSAppBak tool: https://github.com/Wapitiii/WSAppBak

It provides a user-friendly interface to enumerate installed UWP apps and pack/sign them into .appx/.msix packages.

Key points
- GUI frontend for WSAppBak-style functionality.
- Does not require PRI parsing — it uses .resw files and Start Menu entries as fallbacks for app display names.
- Multi-language support (locales stored in `locales/`).

Requirements
- Windows 10/11 (this tool enumerates Appx packages via PowerShell)
- Python 3.9+
- PyQt6 and qfluentwidgets (install via pip)
  pip install PyQt6 qfluentwidgets

Optional
- If you use signing features you need makeappx.exe, makecert.exe, pvk2pfx.exe, signtool.exe in the `bin/` folder or adjust `_run` to point to system tools.

Usage
1. Ensure Python dependencies are installed.
2. Place required signing tools (if you need signing) under `bin/` or keep signing disabled in Settings.
3. Run:
   python main.py
4. Open Settings to change language (or set environment variable `UWP_LANG=zh_CN` or `en_US` before starting).

Localization
- All UI strings are in `locales/` as JSON files. Add or edit `en_US.json` / `zh_CN.json` to modify texts.
- Language can be switched in Settings; no PRI parsing required.

License & Attribution
- This tool is a GUI adaptation and uses/credits the WSAppBak project: https://github.com/Wapitiii/WSAppBak
- Check original repository for its license and attribution requirements.

Notes
- The tool attempts to resolve `ms-resource:` names by looking for `Strings/*.resw` in the app folder and, if missing, by using Start Menu entries or falling back to package names. PRI parsing is intentionally not implemented.
