import sys, os, shutil, subprocess, json, pathlib, secrets
from datetime import datetime
from dataclasses import dataclass
from typing import List
import locale

# 新增：本地化支持与管理
LOCALES_DIR = pathlib.Path(__file__).parent / "locales"

def load_texts(lang: str = None) -> dict:
    if not lang:
        env = os.environ.get("UWP_LANG", "").strip()
        if env:
            lang = env
        else:
            sys_lang = (locale.getdefaultlocale()[0] or "").lower()
            lang = "zh_CN" if sys_lang.startswith("zh") else "en_US"
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        path = LOCALES_DIR / "en_US.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# 全局文本字典与翻译函数
TEXTS = load_texts()

def t(key: str, **kwargs):
    s = TEXTS.get(key, key)
    try:
        return s.format(**kwargs)
    except Exception:
        return s

from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread, QRunnable, QThreadPool
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QLabel, QFileDialog,
                             QHeaderView, QComboBox)  # 新增 QComboBox
from qfluentwidgets import (setTheme, Theme, FluentWindow, NavigationItemPosition,
                            PushButton, LineEdit, ProgressBar, CheckBox as FWCheckBox,
                            InfoBar, InfoBarPosition, StateToolTip,FluentIcon as FIcon)

# Localization 管理对象，发出语言变更信号供界面更新
class Localization(QObject):
    languageChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._lang = None
        self._load_default()

    def _load_default(self):
        # init from existing TEXTS if possible
        # if LOCALES_DIR contains files, pick env or system default
        lang = os.environ.get("UWP_LANG", None)
        if not lang:
            sys_lang = (locale.getdefaultlocale()[0] or "").lower()
            lang = "zh_CN" if sys_lang.startswith("zh") else "en_US"
        self.set_lang(lang, emit=False)

    def set_lang(self, lang: str, emit: bool = True):
        global TEXTS
        if not lang:
            return
        # normalize e.g. zh_CN.json name or zh_CN
        key = lang
        if key.endswith(".json"):
            key = pathlib.Path(key).stem
        path = LOCALES_DIR / f"{key}.json"
        if not path.exists():
            # fallback to en_US
            key = "en_US"
            path = LOCALES_DIR / "en_US.json"
        TEXTS = load_texts(key)
        self._lang = key
        if emit:
            self.languageChanged.emit()

    def current(self):
        return self._lang

    def available(self):
        if not LOCALES_DIR.exists():
            return []
        res = []
        for p in sorted(LOCALES_DIR.glob("*.json")):
            res.append(p.stem)
        return res

    # 新增：返回某语言的友好显示名（优先查找 language_name_{code}, language_display, language_name）
    def display_name_for(self, code: str) -> str:
        try:
            path = LOCALES_DIR / f"{code}.json"
            if not path.exists():
                return code
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 优先键
            key_specific = f"language_name_{code}"
            for k in (key_specific, "language_display", "language_name"):
                if k in data and data[k]:
                    return data[k]
        except Exception:
            pass
        return code

    # 新增：返回 code->display 字典
    def display_names(self) -> dict:
        names = {}
        for code in self.available():
            names[code] = self.display_name_for(code)
        return names

LOC = Localization()

# --------------------------------------------------
# 数据模型
# --------------------------------------------------
@dataclass
class UwpItem:
    name: str
    pkg_fullname: str
    version: str
    arch: str
    install_path: str
    is_selected: bool = False

# 新增：解析 ms-resource 引用到友好名称（从 Strings/*.resw 等资源文件中查找）
def resolve_ms_resource(raw_name: str, install_path: str) -> str:
    try:
        if not raw_name:
            return raw_name
        rn = str(raw_name).strip()
        if "ms-resource" not in rn.lower():
            return rn
        # 提取资源键（取最后一个段）
        try:
            after = rn.split(":", 1)[1]
        except Exception:
            after = rn
        key = after.split("/")[-1].strip()
        if not key:
            return rn
        base = pathlib.Path(install_path) if install_path else None
        # 首先在 Strings 目录查找 .resw
        candidates = []
        if base and base.exists():
            strings_dir = base / "Strings"
            if strings_dir.exists():
                for p in strings_dir.rglob("*.resw"):
                    candidates.append(p)
            # 也尝试在 install_path 下任意 .resw 文件（部分应用结构不同）
            for p in base.rglob("*.resw"):
                if p not in candidates:
                    candidates.append(p)
        # 解析 .resw（XML）查找 key
        import xml.etree.ElementTree as ET
        for resw in candidates:
            try:
                tree = ET.parse(resw)
                root = tree.getroot()
                # <data name="Key"><value>Text</value></data>
                for data in root.findall(".//data"):
                    if data.get("name") == key:
                        val = data.find("value")
                        if val is not None and (val.text and val.text.strip()):
                            return val.text.strip()
            except Exception:
                continue
        # 备用：尝试在 AppxManifest.xml 中查找 Properties/DisplayName（有时包含 localized string）
        if base:
            mf = base / "AppxManifest.xml"
            if mf.exists():
                try:
                    tree = ET.parse(mf)
                    root = tree.getroot()
                    # 查找 Identity / Properties / DisplayName
                    dn = root.find(".//{http://schemas.microsoft.com/appx/2010/manifest}DisplayName")
                    if dn is None:
                        # 更宽松查找
                        dn = root.find(".//DisplayName")
                    if dn is not None and dn.text and dn.text.strip() and "ms-resource" not in dn.text.lower():
                        return dn.text.strip()
                except Exception:
                    pass
        # 回退到安装目录名或原始值
        if base:
            try:
                return base.name or rn
            except Exception:
                pass
    except Exception:
        pass
    return raw_name

# --------------------------------------------------
# PowerShell 枚举线程
# --------------------------------------------------
class PsEnumThread(QThread):
    finished = pyqtSignal(list)

    def run(self):
        cmd = [
            "powershell", "-NoLogo", "-NonInteractive", "-OutputFormat", "Text",
            "-Command", r"""
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            $items = @(
                Get-AppxPackage | ForEach-Object {
                    $pkg = $_
                    if ([string]::IsNullOrEmpty($pkg.InstallLocation)) { return }
                    try {
                        $manifest = Get-AppxPackageManifest -Package $pkg.PackageFullName -ErrorAction SilentlyContinue
                        $dispName = if ($manifest -and $manifest.Package.Properties.DisplayName) {
                                          $manifest.Package.Properties.DisplayName
                                    } else { $pkg.Name }
                    } catch {
                        $dispName = $pkg.Name
                    }
                    [PSCustomObject]@{
                        Name        = $dispName
                        PackageFullName = $pkg.PackageFullName
                        PackageFamilyName = $pkg.PackageFamilyName
                        Version     = $pkg.Version
                        Architecture= $pkg.Architecture
                        InstallLocation = $pkg.InstallLocation
                    }
                }
            )
            $items | ConvertTo-Json -Depth 4
            """
        ]
        try:
            # 延长超时至 60 秒以减少中途超时导致空输出的概率
            completed = subprocess.run(cmd, capture_output=True, text=True,
                                       encoding='utf-8', errors='ignore', timeout=60)
        except subprocess.TimeoutExpired:
            self.finished.emit([])
            return
        if completed.returncode != 0:
            print(t("ps_stderr_prefix"), completed.stderr[:1000])
        raw = completed.stdout or completed.stderr or ""
        raw = raw.strip()
        if not raw:
            self.finished.emit([])
            return

        try:
            import re
            # 去掉常见的 ANSI / 控制字符，避免干扰
            raw_clean = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', raw)
            raw_clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', lambda m: ' ' if m.group(0) in '\r\n\t' else '', raw_clean)

            def extract_balanced(s: str):
                # 定位第一个 JSON 起始符
                start_idx = None
                for i, ch in enumerate(s):
                    if ch in '[{':
                        start_idx = i
                        break
                if start_idx is None:
                    return None
                stack = []
                in_str = False
                esc = False
                for i in range(start_idx, len(s)):
                    ch = s[i]
                    if esc:
                        esc = False
                        continue
                    if ch == '\\' and in_str:
                        esc = True
                        continue
                    if ch == '"' :
                        in_str = not in_str
                        continue
                    if in_str:
                        continue
                    if ch in '[{':
                        stack.append(ch)
                    elif ch in ']}':
                        if not stack:
                            # unmatched closing, skip
                            continue
                        top = stack[-1]
                        if (top == '[' and ch == ']') or (top == '{' and ch == '}'):
                            stack.pop()
                            if not stack:
                                return s[start_idx:i+1]
                        else:
                            # mismatch
                            return None
                # 未匹配完：返回截断的片段以便后续尝试
                return s[start_idx:]

            candidate = extract_balanced(raw_clean)
            parsed = None
            if candidate:
                try:
                    parsed = json.loads(candidate)
                except Exception:
                    parsed = None

            # 若上面失败，尝试使用最后出现的闭合括号位置截取（经常能处理末尾被截断情况）
            if parsed is None:
                last_sq = raw_clean.rfind(']')
                last_cu = raw_clean.rfind('}')
                last_pos = max(last_sq, last_cu)
                first_sq = raw_clean.find('[')
                first_cu = raw_clean.find('{')
                first_pos_candidates = [p for p in (first_sq, first_cu) if p != -1]
                first_pos = min(first_pos_candidates) if first_pos_candidates else -1
                if first_pos != -1 and last_pos != -1 and last_pos > first_pos:
                    try_sub = raw_clean[first_pos:last_pos+1]
                    try:
                        parsed = json.loads(try_sub)
                    except Exception:
                        parsed = None

            # 最后回退到简单的正则捕获（非贪婪地捕获首个 JSON 数组/对象）
            if parsed is None:
                m = re.search(r'(\[.*?\]|\{.*?\})', raw_clean, re.S)
                if m:
                    try:
                        parsed = json.loads(m.group(1))
                    except Exception:
                        parsed = None

            if parsed is None:
                print(t("unable_extract_json_preview"), raw[:1000])
                self.finished.emit([])
                return

            data = parsed
            if not isinstance(data, list):
                data = [data]
        except Exception as e:
            print(t("json_extraction_error"), e)
            self.finished.emit([])
            return

        # 在解析到 data 后，尝试获取 Start menu 应用映射（AppID -> Name）
        def get_startapps_map():
            try:
                scmd = [
                    "powershell", "-NoLogo", "-NonInteractive", "-OutputFormat", "Text",
                    "-Command", r"""
                    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
                    Get-StartApps | Select-Object AppID,Name | ConvertTo-Json -Depth 2
                    """
                ]
                comp = subprocess.run(scmd, capture_output=True, text=True,
                                      encoding='utf-8', errors='ignore', timeout=20)
                out = comp.stdout.strip() or comp.stderr.strip()
                if not out:
                    return {}
                arr = json.loads(out) if out else []
                if isinstance(arr, dict):
                    arr = [arr]
                m = {}
                for a in arr:
                    aid = (a.get('AppID') or '').lower()
                    name = a.get('Name') or ''
                    if aid:
                        m[aid] = name
                return m
            except Exception:
                return {}

        start_map = get_startapps_map()

        arch_map = {0: 'X86', 5: 'ARM', 9: 'X64', 11: 'ARM64', 12: 'ARM64'}
        items = []
        for d in data:
            raw_name = d.get('Name') or d.get('PackageFullName')
            install_location = d.get('InstallLocation') or ''
            pkg_full = d.get('PackageFullName') or ''
            pkg_family = d.get('PackageFamilyName') or ''

            # 若返回的 Name 是 ms-resource 引用，尝试解析本地资源以获取友好名称
            display_name = raw_name
            try:
                if isinstance(raw_name, str) and 'ms-resource' in raw_name.lower():
                    # 1) 先尝试本地 .resw 解析
                    resolved = resolve_ms_resource(raw_name, install_location)
                    if resolved and ('ms-resource' not in str(resolved).lower()):
                        display_name = resolved
                    else:
                        # 2) 使用 StartApps 映射：查找 AppID 中包含 package family 的项
                        if pkg_family and start_map:
                            found = None
                            low_family = pkg_family.lower()
                            for aid, aname in start_map.items():
                                if low_family in aid:
                                    found = aname
                                    break
                            if found:
                                display_name = found
                            else:
                                # 3) 最后回退：从 PackageFullName 截取更友好的前缀（去掉版本信息）
                                if pkg_full:
                                    display_name = pkg_full.split('_')[0]
                else:
                    display_name = raw_name
            except Exception:
                display_name = raw_name

            items.append(UwpItem(
                name=display_name,
                pkg_fullname=pkg_full,
                version=d.get('Version') or '',
                arch=arch_map.get(d.get('Architecture'), 'Unknown'),
                install_path=install_location
            ))
        self.finished.emit(items)

# --------------------------------------------------
# 工具链路径
# --------------------------------------------------
BIN_DIR = pathlib.Path(__file__).parent / "bin"
MAKEAPPX = BIN_DIR / "makeappx.exe"
MAKECERT = BIN_DIR / "makecert.exe"
PVK2PFX  = BIN_DIR / "pvk2pfx.exe"
SIGNTOOL = BIN_DIR / "signtool.exe"

def _run(tool: pathlib.Path, args: list, cwd=None) -> str:
    if not tool.exists():
        raise RuntimeError(t("tool_not_exist", tool=tool.name))
    cmd = [str(tool), *args]
    completed = subprocess.run(cmd, capture_output=True, text=True,
                               encoding='utf-8', errors='ignore', cwd=cwd or BIN_DIR)
    if completed.returncode != 0:
        err = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(t("tool_failed", tool=tool.name, err=err))
    return completed.stdout

# --------------------------------------------------
# 打包线程（带跳过签名开关）
# --------------------------------------------------
class PackSignThread(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, item: UwpItem, out_dir: pathlib.Path, skip_sign: bool):
        super().__init__()
        self.item = item
        self.out_dir = out_dir
        self.skip_sign = skip_sign

    def run(self):
        try:
            import re
            from pathlib import Path
            
            # 使用C#风格的命名
            ws_app_path = Path(self.item.install_path)
            ws_app_name = ws_app_path.name
            
            # 生成输出文件名（类似C#版本）
            file_name = ws_app_name
            appx_file = self.out_dir / f"{file_name}.appx"
            
            # 清理现有文件（类似C#版本）
            self.out_dir.mkdir(parents=True, exist_ok=True)
            for ext in ['.appx', '.pvk', '.cer', '.pfx']:
                old_file = self.out_dir / f"{file_name}{ext}"
                if old_file.exists():
                    old_file.unlink(missing_ok=True)

            # 1. 打包（与C#版本相同的参数）
            self.log.emit(t("pack_log_pack"))
            _run(MAKEAPPX, ['pack', '-d', str(ws_app_path), '-p', str(appx_file), '-l'])
            
            if self.skip_sign:
                self.log.emit(t("pack_log_skipped"))
                self.finished.emit(True)
                return

            # 2. 解析AppxManifest.xml获取Publisher（类似C#版本）
            publisher = self.extract_publisher_from_manifest(ws_app_path)
            if not publisher:
                publisher = "CN=TempUWPExtractCert"
            
            # 3. 生成证书（使用C#版本的参数格式）
            self.log.emit(t("pack_log_gen_cert"))
            pvk_file = self.out_dir / f"{file_name}.pvk"
            cer_file = self.out_dir / f"{file_name}.cer"
            
            # 使用与C#版本完全相同的MakeCert参数
            makecert_args = [
                '-n', publisher,
                '-r', 
                '-a', 'sha256', 
                '-len', '2048', 
                '-cy', 'end', 
                '-h', '0', 
                '-eku', '1.3.6.1.5.5.7.3.3',
                '-b', '01/01/2000',
                '-sv', str(pvk_file),
                str(cer_file)
            ]
            
            _run(MAKECERT, makecert_args)

            # 4. 转换证书（C#版本没有密码）
            self.log.emit(t("pack_log_convert_cert"))
            pfx_file = self.out_dir / f"{file_name}.pfx"
            
            pvk2pfx_args = [
                '-pvk', str(pvk_file),
                '-spc', str(cer_file), 
                '-pfx', str(pfx_file)
            ]
            _run(PVK2PFX, pvk2pfx_args)

            # 5. 签名（使用C#版本的参数）
            self.log.emit(t("pack_log_signing"))
            
            signtool_args = [
                'sign', 
                '-fd', 'SHA256', 
                '-a', 
                '-f', str(pfx_file),
                str(appx_file)
            ]
            
            out = _run(SIGNTOOL, signtool_args)
            
            if "successfully signed" in out.lower():
                self.log.emit(t("pack_log_sign_success"))
                self.log.emit(t("pack_log_install_cer"))
                self.log.emit(t("pack_log_install_appx"))
                self.finished.emit(True)
            else:
                raise RuntimeError(t("sign_no_success"))
                
        except Exception as e:
            self.log.emit(t("pack_error", err=e))
            self.finished.emit(False)

    def extract_publisher_from_manifest(self, app_path):
        """从AppxManifest.xml提取Publisher，类似C#版本"""
        try:
            manifest_path = app_path / "AppxManifest.xml"
            if not manifest_path.exists():
                return None
                
            import xml.etree.ElementTree as ET
            tree = ET.parse(manifest_path)
            root = tree.getroot()
            
            # 查找Identity元素的Publisher属性
            namespaces = {
                'default': 'http://schemas.microsoft.com/appx/manifest/foundation/windows10',
                'mp': 'http://schemas.microsoft.com/appx/2014/phone/manifest',
                'uap': 'http://schemas.microsoft.com/appx/manifest/uap/windows10'
            }
            
            # 注册命名空间
            for prefix, uri in namespaces.items():
                ET.register_namespace(prefix, uri)
            
            # 尝试查找Identity元素
            identity = root.find('.//{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Identity')
            if identity is not None:
                publisher = identity.get('Publisher')
                if publisher:
                    return publisher
                    
        except Exception as e:
            self.log.emit(t("manifest_parse_error", err=e))
        
        return None

# --------------------------------------------------
# 设置页
# --------------------------------------------------
class SettingsInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsInterface")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.title = QLabel(t("settings_title"))
        self.title.setStyleSheet("font: 20px 'Segoe UI'; font-weight: bold;")
        lay.addWidget(self.title)

        self.skipCheck = FWCheckBox(t("skip_checkbox"))
        self.skipCheck.setToolTip(t("skip_tooltip"))
        lay.addWidget(self.skipCheck)

        # 新增：语言选择下拉（显示友好名称，itemData 存语言代码）
        h_lang = QHBoxLayout()
        h_lang_lbl = QLabel(t("language_label") if TEXTS.get("language_label") else "Language")
        self.langCombo = QComboBox()
        # 使用 LOC.display_names() 获取 code->display
        self._populate_lang_combo()
        # 改为根据 index 改变时使用 itemData 获取语言代码
        self.langCombo.currentIndexChanged.connect(self.on_lang_index_changed)
        h_lang.addWidget(h_lang_lbl)
        h_lang.addWidget(self.langCombo)
        lay.addLayout(h_lang)

        self.saveBtn = PushButton(t("save_button"))
        self.saveBtn.clicked.connect(self.save_cfg)
        lay.addWidget(self.saveBtn)

        self._skip = False

        # 订阅全局语言变更，更新界面文本
        LOC.languageChanged.connect(self.retranslate_ui)

    # 新增：填充下拉并选中当前语言
    def _populate_lang_combo(self):
        self.langCombo.blockSignals(True)
        self.langCombo.clear()
        names = LOC.display_names()  # code -> display
        cur = LOC.current() or ""
        for code, display in names.items():
            self.langCombo.addItem(display, code)
        if cur:
            # 设置当前选中项（依据 userData）
            for i in range(self.langCombo.count()):
                if self.langCombo.itemData(i) == cur:
                    self.langCombo.setCurrentIndex(i)
                    break
        self.langCombo.blockSignals(False)

    def on_lang_index_changed(self, index: int):
        # 从 itemData 读取语言代码并切换
        code = self.langCombo.itemData(index)
        if code:
            LOC.set_lang(code)

    def load_cfg(self, skip: bool):
        self._skip = skip
        self.skipCheck.setChecked(skip)

    def save_cfg(self):
        self._skip = self.skipCheck.isChecked()
        InfoBar.success(t("save_success_title"), t("save_success_msg"), duration=1500, parent=self, position=InfoBarPosition.TOP)

    def get_cfg(self) -> bool:
        return self._skip

    def on_lang_changed(self, lang_code: str):
        # 切换语言并通知其它组件
        LOC.set_lang(lang_code)

    def retranslate_ui(self):
        # 更新所有静态文本
        self.title.setText(t("settings_title"))
        self.skipCheck.setText(t("skip_checkbox"))
        self.skipCheck.setToolTip(t("skip_tooltip"))
        self.saveBtn.setText(t("save_button"))
        # 重新填充下拉显示名并保持选中项
        self._populate_lang_combo()

# --------------------------------------------------
# 主页
# --------------------------------------------------
class MainInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("mainInterface")
        self.items: List[UwpItem] = []
        self.skip_sign = False
        self.init_ui()
        self.enum_thread = PsEnumThread()
        self.enum_thread.finished.connect(self.on_enum_done)
        self.enum_thread.start()
        # 订阅语言变化
        LOC.languageChanged.connect(self.retranslate_ui)

    def init_ui(self):
        # 顶部搜索
        self.search = LineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.setPlaceholderText(t("search_placeholder"))
        self.search.textChanged.connect(self.do_filter)

        # 中间表格
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            t("table_header_select"),
            t("table_header_name"),
            t("table_header_pkg"),
            t("table_header_version"),
            t("table_header_arch")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 24)         
        header.setMinimumSectionSize(24)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # 底部控制区
        self.btn_sel_all = FWCheckBox(t("select_all"))
        self.btn_sel_all.stateChanged.connect(self.on_sel_all)
        self.btn_out = PushButton(t("select_out_btn"))
        self.btn_out.clicked.connect(self.pick_out_dir)
        self.lab_out = QLabel(t("select_label_default"))
        self.btn_run = PushButton(t("extract_button"))
        self.btn_run.clicked.connect(self.start_extract)
        self.progress = ProgressBar()
        self.progress.setVisible(False)

        lay_bottom = QHBoxLayout()
        lay_bottom.addWidget(self.btn_sel_all)
        lay_bottom.addWidget(self.btn_out)
        lay_bottom.addWidget(self.lab_out, 1)
        lay_bottom.addWidget(self.btn_run)

        lay = QVBoxLayout(self)
        lay.addWidget(self.search)
        lay.addWidget(self.table)
        lay.addLayout(lay_bottom)
        lay.addWidget(self.progress)

    # ---------- 枚举 ----------
    def on_enum_done(self, items: List[UwpItem]):
        self.items = items
        self.fill_table()
        InfoBar.success(t("enum_done_title"), t("enum_done_msg", count=len(items)), duration=2000,
                        parent=self, position=InfoBarPosition.TOP)

    def fill_table(self):
        self.table.setRowCount(0)
        for idx, it in enumerate(self.items):
            self.table.insertRow(idx)
            chk = FWCheckBox()
            chk.setChecked(it.is_selected)
            chk.checkStateChanged.connect(lambda st, i=idx: self.on_item_check(st, i))
            self.table.setCellWidget(idx, 0, chk)
            self.table.setItem(idx, 1, QTableWidgetItem(it.name))
            self.table.setItem(idx, 2, QTableWidgetItem(it.pkg_fullname))
            self.table.setItem(idx, 3, QTableWidgetItem(it.version))
            self.table.setItem(idx, 4, QTableWidgetItem(it.arch))
        self.do_filter()

    def on_item_check(self, state, idx):
        self.items[idx].is_selected = bool(state)

    def on_sel_all(self, state):
        for i, it in enumerate(self.items):
            it.is_selected = bool(state)
            if self.table.cellWidget(i, 0):
                self.table.cellWidget(i, 0).setChecked(bool(state))

    def do_filter(self):
        kw = self.search.text().strip().lower()
        for i in range(self.table.rowCount()):
            txt = self.table.item(i, 1).text().lower()
            self.table.setRowHidden(i, kw not in txt)

    # ---------- 提取 ----------
    def pick_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, t("select_out_dialog_title"))
        if d:
            self.out_dir = pathlib.Path(d)
            self.lab_out.setText(str(self.out_dir))

    def start_extract(self):
        if not hasattr(self, "out_dir"):
            InfoBar.warning(t("warning_title"), t("out_dir_not_selected_msg"), parent=self, position=InfoBarPosition.TOP)
            return
        selected = [it for it in self.items if it.is_selected]
        if not selected:
            InfoBar.warning(t("warning_title"), t("not_selected_msg"), parent=self, position=InfoBarPosition.TOP)
            return
        if len(selected) > 1:
            InfoBar.warning(t("warning_title"), t("multi_select_msg"), parent=self, position=InfoBarPosition.TOP)
            return
        item = selected[0]
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_run.setEnabled(False)

        self.pack_thread = PackSignThread(item, self.out_dir, self.skip_sign)
        self.pack_thread.log.connect(self.log)
        self.pack_thread.finished.connect(self.on_pack_done)
        self.pack_thread.start()

    def on_pack_done(self, ok: bool):
        self.btn_run.setEnabled(True)
        self.progress.setVisible(False)
        if ok:
            InfoBar.success(t("complete_title"), t("complete_msg"), parent=self, position=InfoBarPosition.TOP)
        else:
            InfoBar.error(t("fail_title"), t("fail_msg"), parent=self, position=InfoBarPosition.TOP)

    def log(self, msg):
        print(f"[{datetime.now():%H:%M:%S}] {msg}")

    def retranslate_ui(self):
        # 更新动态文本
        self.search.setPlaceholderText(t("search_placeholder"))
        self.table.setHorizontalHeaderLabels([
            t("table_header_select"),
            t("table_header_name"),
            t("table_header_pkg"),
            t("table_header_version"),
            t("table_header_arch")
        ])
        self.btn_sel_all.setText(t("select_all"))
        self.btn_out.setText(t("select_out_btn"))
        # lab_out 若为默认文本才替换，否则保留路径
        if not hasattr(self, "out_dir"):
            self.lab_out.setText(t("select_label_default"))
        self.btn_run.setText(t("extract_button"))

# --------------------------------------------------
# AppWindow：左侧导航 + 设置页
# --------------------------------------------------
class AppWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("window_title"))
        self.resize(920, 680)

        # 1. 主页
        self.main = MainInterface()
        self.main.setObjectName("mainInterface")
        self.addSubInterface(self.main, FIcon.HOME, t("nav_home") if TEXTS.get("nav_home") else "Home", NavigationItemPosition.TOP)

        # 2. 设置页
        self.settings = SettingsInterface()
        self.settings.setObjectName("settingsInterface")
        self.addSubInterface(self.settings, FIcon.SETTING, t("nav_settings") if TEXTS.get("nav_settings") else "Settings", NavigationItemPosition.BOTTOM)

        # 3. 配置双向同步
        self.settings.load_cfg(self.main.skip_sign)
        self.settings.saveBtn.clicked.connect(self.apply_settings)

        # 订阅语言变更，更新窗口标题与导航文本
        LOC.languageChanged.connect(self.retranslate_ui)

    def apply_settings(self):
        self.main.skip_sign = self.settings.get_cfg()
        InfoBar.success(t("settings_saved_title"), t("settings_saved_msg"), duration=1500, parent=self, position=InfoBarPosition.TOP)

    def retranslate_ui(self):
        self.setWindowTitle(t("window_title"))
        # 更新导航项文本（FluentWindow 的 addSubInterface 不提供直接重设接口）
        # 简单方案：移除并重新添加子界面（保持当前选中态可能丢失）
        # 先保存当前 index
        try:
            current = self.getCurrentIndex()
        except Exception:
            current = 0
        # 清空并重新添加
        # 注意：FluentWindow 没有公开移除接口，这里仅尝试设置显示名（如果 API 支持）
        # 如果控件库限制，用户可以重启应用以使语言生效
        # 尝试通过 setItemText 或类似 API（视 qfluentwidgets 版本而定）
        # 兜底：不抛异常
        try:
            # 尝试更新 nav texts if possible
            self.setWindowTitle(t("window_title"))
        except Exception:
            pass

# --------------------------------------------------
# main
# --------------------------------------------------
if __name__ == "__main__":
    setTheme(Theme.AUTO)
    app = QApplication(sys.argv)
    w = AppWindow()
    w.show()
    sys.exit(app.exec())