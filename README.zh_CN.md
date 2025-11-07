[English](readme.md)
# UWP 安装包提取工具（GUI）

此程序为开源工具 WSAppBak（https://github.com/Wapitiii/WSAppBak ）的 GUI 版本，提供图形界面用于枚举已安装的 UWP 应用并打包/签名为 .appx/.msix。

要点
- 基于 WSAppBak 思路的 GUI 前端。
- 不需要 PRI 解析：通过查找应用目录下的 `Strings/*.resw`、使用开始菜单条目或回退到包名来获取应用显示名。
- 支持多语言，文本集中在 `locales/` 目录下的 JSON 文件中。

环境要求
- Windows 10/11（工具通过 PowerShell 枚举 Appx 包）
- Python 3.9+
- PyQt6 与 qfluentwidgets（通过 pip 安装）
  pip install PyQt6 qfluentwidgets

可选
- 如需签名功能，请将 makeappx.exe、makecert.exe、pvk2pfx.exe、signtool.exe 放到项目的 `bin/` 文件夹，或按需调整 `_run` 中的路径。

使用方法
1. 安装 Python 依赖。
2. （可选）准备签名工具或在设置中选择跳过签名。
3. 运行：
   python main.py
4. 在“设置”页切换语言（或启动前设置环境变量 UWP_LANG=zh_CN 或 UWP_LANG=en_US）。

本地化
- 所有 UI 文本保存在 `locales/` 下的 JSON 文件。可编辑 `en_US.json` / `zh_CN.json` 来修改文本。
- 切换语言后界面会尽量即时更新（部分导航文本在某些库版本中可能需重启生效）。

许可与致谢
- 本项目作为 GUI 适配，参考并致谢 WSAppBak： https://github.com/Wapitiii/WSAppBak
- 请参阅原项目以确认其许可与致谢要求。

说明
- 程序会优先使用 `.resw` 解析 `ms-resource:` 字符串；若无法解析则尝试使用开始菜单映射或使用包名的前缀作为回退。特意不实现 PRI 解析。
