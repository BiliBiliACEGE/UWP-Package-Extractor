from pathlib import Path
import json

BASE_DIR   = Path(__file__).with_suffix('').parent
TRANS_DIR  = BASE_DIR / "locales"

TRANS_DIR.mkdir(exist_ok=True)

# 所有会被代码引用的 key，一次性写全
DEFAULT_ZH = {
    "window_title": "UWP 安装包提取工具",
    "nav_home": "主页",
    "nav_settings": "设置",
    "settings_title": "设置",
    "skip_checkbox": "跳过签名（仅打包，不生成证书）",
    "skip_tooltip": "勾选后只生成 .appx/.msix，不再签名",
    "language_label": "语言",
    "language_name_zh_CN": "中文（简体）",
    "language_name_en_US": "English（US）",
    "language_display": "语言",
    "save_button": "保存",
    "save_success_title": "已保存",
    "save_success_msg": "设置已生效",
    "settings_saved_title": "设置已保存",
    "settings_saved_msg": "",
    "enum_done_title": "枚举完成",
    "enum_done_msg": "共找到 {count} 个应用",
    "select_out_btn": "选择保存目录",
    "select_out_dialog_title": "选择保存目录",
    "select_label_default": "未选择",
    "out_dir_not_selected_msg": "请先选择保存目录",
    "warning_title": "提示",
    "not_selected_msg": "未勾选任何应用",
    "multi_select_msg": "一次只能勾选一个应用进行打包",
    "extract_button": "提取安装包",
    "select_all": "全选",
    "search_placeholder": "输入关键字过滤…",
    "table_header_select": " ",
    "table_header_name": "应用名称",
    "table_header_pkg": "包全名",
    "table_header_version": "版本",
    "table_header_arch": "架构",
    "pack_log_pack": ">>> 正在打包 .appx ...",
    "pack_log_skipped": ">>> 已跳过签名（仅打包）",
    "pack_log_gen_cert": ">>> 正在生成自签证书 ...",
    "pack_log_convert_cert": ">>> 正在转换证书 ...",
    "pack_log_signing": ">>> 正在签名（这可能需要几分钟）...",
    "pack_log_sign_success": ">>> 签名成功！",
    "pack_log_install_cer": ">>> 请将 .cer 文件安装到 [本地计算机\\\\受信任的根证书颁发机构]",
    "pack_log_install_appx": ">>> 然后再安装 .appx 文件包",
    "pack_error": "❌ 打包签名失败：{err}",
    "manifest_parse_error": ">>> 无法解析 AppxManifest.xml：{err}",
    "sign_no_success": "签名未返回成功信息",
    "tool_not_exist": "{tool} 不存在",
    "tool_failed": "{tool} 失败！\\n{err}",
    "ps_stderr_prefix": "PS stderr >>>",
    "unable_extract_json_preview": "无法从 PowerShell 输出中提取有效 JSON，输出预览：",
    "json_extraction_error": "JSON 解析/提取错误：",
    "complete_title": "完成",
    "complete_msg": "已提取/打包完成",
    "fail_title": "失败",
    "fail_msg": "查看日志了解详情",
    "raw_json_preview": "Raw JSON candidate preview:"
}

DEFAULT_EN = {
    "window_title": "UWP Package Extractor",
    "nav_home": "Home",
    "nav_settings": "Settings",
    "settings_title": "Settings",
    "skip_checkbox": "Skip signing (pack only, do not generate cert)",
    "skip_tooltip": "When checked, only produce .appx/.msix and skip signing",
    "language_label": "Language",
    "language_name_zh_CN": "中文 (zh_CN)",
    "language_name_en_US": "English (en_US)",
    "language_display": "Language",
    "save_button": "Save",
    "save_success_title": "Saved",
    "save_success_msg": "Settings applied",
    "settings_saved_title": "Settings saved",
    "settings_saved_msg": "",
    "enum_done_title": "Enumeration Done",
    "enum_done_msg": "Found {count} apps",
    "select_out_btn": "Choose output folder",
    "select_out_dialog_title": "Choose output folder",
    "select_label_default": "Not selected",
    "out_dir_not_selected_msg": "Please choose an output folder first",
    "warning_title": "Warning",
    "not_selected_msg": "No app selected",
    "multi_select_msg": "Only one app can be selected for packaging",
    "extract_button": "Extract Package",
    "select_all": "Select All",
    "search_placeholder": "Filter by keyword…",
    "table_header_select": " ",
    "table_header_name": "App Name",
    "table_header_pkg": "Package Full Name",
    "table_header_version": "Version",
    "table_header_arch": "Architecture",
    "pack_log_pack": ">>> Packing .appx ...",
    "pack_log_skipped": ">>> Signing skipped (pack only)",
    "pack_log_gen_cert": ">>> Generating self-signed certificate ...",
    "pack_log_convert_cert": ">>> Converting certificate ...",
    "pack_log_signing": ">>> Signing (this may take a few minutes) ...",
    "pack_log_sign_success": ">>> Signed successfully!",
    "pack_log_install_cer": ">>> Please install the .cer file to [Local Computer\\\\Trusted Root Certification Authorities]",
    "pack_log_install_appx": ">>> Then install the .appx package",
    "pack_error": "❌ Pack/sign failed: {err}",
    "manifest_parse_error": ">>> Unable to parse AppxManifest.xml: {err}",
    "sign_no_success": "Signing did not return success info",
    "tool_not_exist": "{tool} not found",
    "tool_failed": "{tool} failed!\\n{err}",
    "ps_stderr_prefix": "PS stderr >>>",
    "unable_extract_json_preview": "Unable to extract valid JSON from PowerShell output, preview:",
    "json_extraction_error": "JSON extraction error:",
    "complete_title": "Done",
    "complete_msg": "Extraction/packing complete",
    "fail_title": "Failed",
    "fail_msg": "See logs for details",
    "raw_json_preview": "Raw JSON candidate preview:"
}

def _write_json(path: Path, data: dict):
    if path.exists():
        return
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ---------- 统一入口 ----------
def init_resources():
    _write_json(TRANS_DIR / "zh_CN.json", DEFAULT_ZH)
    _write_json(TRANS_DIR / "en_US.json", DEFAULT_EN)


init_resources()