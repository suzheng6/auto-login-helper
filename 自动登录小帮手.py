import sys
import re
import time
import asyncio
import subprocess
import keyboard
import requests
import webbrowser
import os
import json
import shutil
import threading
from datetime import datetime
from bs4 import BeautifulSoup

APP_VERSION = "1.0.0"
GITHUB_REPO = "suzheng6/auto-login-helper"

# Telethon 用于直接调用 Telegram API 登录（抓包复现请求）
try:
    from telethon import TelegramClient
    from telethon.errors import (
        SessionPasswordNeededError, PhoneCodeInvalidError,
        FloodWaitError, PhoneNumberBannedError, PhoneNumberInvalidError,
        AuthKeyUnregisteredError
    )
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False

# opentele 不能在启动时导入（会 monkey-patch telethon 导致登录失败）
# 仅检查是否已安装，实际使用时在子进程中延迟导入
import importlib.util
OPENETELE_AVAILABLE = importlib.util.find_spec("opentele") is not None
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTextEdit, QLabel, QVBoxLayout,
    QPushButton, QHBoxLayout, QGroupBox, QFileDialog, QMessageBox, QComboBox,
    QLineEdit
)
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette


# 多语言配置
class Translations:
    """多语言配置类"""
    ZH = "zh"
    EN = "en"

    STRINGS = {
        ZH: {
            # 窗口标题
            "window_title": f"自动登录小助手 v{APP_VERSION}",

            # 统计
            "stats_title": "📊 登录统计",
            "total_accounts": "总账号数: {count}",
            "current_account": "当前账号: {count}",
            "success_count": "✓ 成功: {count}",
            "fail_count": "✗ 失败: {count}",

            # 输入区域
            "input_title": "📝 账号列表",
            "input_placeholder": "每行格式：手机号|验证码URL\n"
                                "例：+15795807280|https://miha.uk/tgapi/.../GetHTML\n\n"
                                "F4 - 打开当前行网址  |  F3 - 自动登录（验证码与2FA从URL页面获取）",

            # 状态
            "status_title": "📋 操作日志",
            "status_waiting": "等待操作...",

            # 按钮
            "btn_clear": "🗑️ 清空列表",
            "btn_add_account": "➕ 添加账户",
            "btn_retry": "🔄 重新登录失败账号",
            "btn_export": "📥 导出失败账号",
            "btn_ayugram": "📱 选择 AyuGram",
            "ayugram_path_placeholder": "未选择（登录后将写入该程序的 tdata 目录）",
            "api_settings_title": "⚙️ API 设置（可选）",
            "api_id_placeholder": "API ID（留空用默认 Desktop）",
            "api_hash_placeholder": "API Hash（留空用默认 Desktop）",
            "api_hint": "默认使用 TelegramDesktop 官方 API，通常无需修改",
            "btn_capture": "📸 截取验证码界面",
            "btn_test": "🔍 测试截图",

            # 添加账户对话框
            "dialog_add_account_title": "添加账户",
            "dialog_add_account_phone": "手机号（如 +14582185432）:",
            "dialog_add_account_url": "验证码 URL（可选，留空可稍后填写）:",
            "msg_account_added": "已添加账户：{phone}",
            "msg_account_added_fail": "请输入手机号",

            # 复选框和标签
            "chk_input_plus_one": "输入+1",
            "lbl_start": "🚀 F3开始  |  F5停止",
            "btn_stop": "🛑 紧急停止",

            # 消息提示
            "msg_no_failed_accounts": "没有失败账号需要导出",
            "msg_export_success": "已将{count}个失败账号保存到 {file}",
            "msg_no_failed_retry": "没有失败账号需要重新登录",
            "msg_retry_loaded": "失败账号已加载到列表中，请按F3重新登录",
            "msg_url_extracted": "已打开网址：{url}",
            "msg_url_complete": "网址提取完毕",
            "msg_login_complete": "所有账号登录完成！",
            "msg_login_complete_with_fail": "登录完成！成功: {success}, 失败: {fail}",
            "msg_login_all_success": "登录完成！所有账号成功登录",

            # 截图相关
            "screenshot_title": "自动截取验证码界面",
            "screenshot_prepare": "📍 准备验证码界面\n\n"
                                  "请先打开登录界面，确保验证码输入框可见。\n\n"
                                  "点击确定后，将自动打开截图工具。\n\n"
                                  "请用鼠标框选验证码界面区域，\n"
                                  "截图完成后，点击下方\"已完成截图\"按钮。",
            "screenshot_waiting": "📍 正在等待截图...\n\n"
                                  "程序已自动调用截图工具（Windows+Shift+S）。\n\n"
                                  "请用鼠标框选验证码界面区域。\n\n"
                                  "截图完成后，点击下方\"✅ 已完成截图\"按钮",
            "screenshot_cancel": "取消",
            "screenshot_done": "✅ 已完成截图",

            # 截图错误提示
            "error_no_clipboard": "未能从剪贴板获取到截图！\n\n"
                                  "请确保：\n"
                                  "1. 您已经使用截图工具截图\n"
                                  "2. 截图成功保存到剪贴板\n"
                                  "3. 没有复制其他内容到剪贴板",
            "error_capture_failed": "截图获取失败",
            "error_verify_failed": "截图验证失败，请检查截图内容。\n\n"
                                   "建议：\n"
                                   "1. 确保截图包含完整的验证码界面\n"
                                   "2. 截图宽度建议在 800-1920 像素之间\n"
                                   "3. 重新截图，框选更大的区域",
            "error_screenshot_saved": "截图已保存：{filename}",
            "error_screenshot_loaded": "✅ 验证码界面截图已加载：{filename}",

            # 成功提示
            "success_captured": "验证码界面截图已成功截取并加载！\n\n"
                                "文件：{filename}\n"
                                "保存位置：{path}\n\n"
                                "现在可以按F3开始自动登录了。",

            # 测试截图
            "test_no_screenshot": "❌ 当前目录下没有找到验证码界面截图。\n\n"
                                  "是否现在截取验证码界面？\n\n"
                                  "截取后程序会自动识别是否可用。",
            "test_no_screenshot_title": "未检测到截图",
            "test_capture_cancel": "截图已取消",
            "test_capture_failed": "❌ 未成功截取截图",
            "test_not_captured": "❌ 请先截取验证码界面",
            "test_check_failed": "截图检查失败",
            "test_checking": "正在检查截图文件...",
            "test_checking_file": "正在尝试在屏幕上识别截图...",
            "test_checking_path": "使用的截图路径：{path}",
            "test_checking_size": "文件大小：{size} 字节",
            "test_image_size": "图片尺寸：{width} x {height}",
            "test_no_chinese": "❌ 检测到中文路径，建议将截图文件放在程序目录下",
            "test_res_small": "❌ 截图分辨率过小：{w}x{h}",
            "test_res_large": "❌ 截图分辨率过大：{w}x{h}",
            "test_res_ok": "✅ 截图分辨率合适：{w}x{h}",
            "test_res_info": "ℹ️ 截图分辨率：{w}x{h}（建议 800-1920 x 600-1080）",
            "test_success": "截图可用",
            "test_recognized": "✅ 截图识别成功！\n\n"
                               "截图文件：{filename}\n"
                               "匹配位置：{location}\n\n"
                               "🚀 现在可以按 F3 开始自动登录了！",
            "test_recognized_low_conf": "✅ 截图识别成功！（较低置信度）\n\n"
                                         "截图文件：{filename}\n"
                                         "匹配位置：{location}\n\n"
                                         "🚀 现在可以按 F3 开始自动登录了！",
            "test_failed": "截图识别失败",
            "test_failed_msg": "❌ 在屏幕上未找到与截图匹配的区域。\n\n"
                               "可能原因：\n"
                               "1. 截图与当前屏幕界面不一致\n"
                               "2. 截图包含动态内容（如时间）\n"
                               "3. 验证码界面未打开或被遮挡\n\n"
                               "是否重新截取验证码界面？",

            # 中文路径警告
            "warning_chinese_path": "⚠️ 检测到中文路径：{path}",
            "warning_chinese_path_dir": "⚠️ 警告：程序所在文件夹路径包含中文字符",
            "warning_chinese_path_current": "当前路径：{path}",
            "warning_chinese_path_advice": "建议：将程序文件夹放在不含中文的路径下",
            "warning_chinese_path_result": "这可能导致 OpenCV 无法读取截图文件",
            "warning_chinese_path_screenshot": "建议：将截图文件放在程序目录下",

            # 状态消息
            "status_trigger_screenshot": "已打开截图工具，请框选验证码界面",
            "status_screenshot_cancelled": "截图已取消",
            "status_getting_screenshot": "正在从剪贴板获取截图...",
            "status_screenshot_saved": "截图已保存：{filename}",
            "status_screenshot_verify_failed": "截图验证失败",
            "status_error_log_saved": "错误信息已保存到：{file}",

            # 错误处理
            "error_loading_screenshot": "无法加载截图文件：{error}",
            "error_screenshot_advice": "建议：使用 Windows 自带的画图工具重新保存截图为 PNG 格式",
            "error_screen_timeout": "❌ 超时：未检测到界面 {filename}",
            "error_screen_attempts": "检测次数：{count}次，用时：{timeout}秒",
            "error_screen_advice": "建议：点击\"测试截图\"按钮检查截图是否正确",
            "error_opencv": "❌ 截图识别失败\n\n"
                            "可能原因：\n"
                            "1. Telegram 窗口太小\n"
                            "2. 截图分辨率过低或格式不正确\n"
                            "3. 文件路径包含中文字符\n\n"
                            "解决方法：\n"
                            "1. 将 Telegram 窗口拉大，确保窗口尺寸足够\n"
                            "2. 重新截图，框选更大的区域\n"
                            "3. 将程序文件夹和截图文件放在不含中文的路径下\n"
                            "4. 确保截图文件为 PNG 格式\n\n"
                            "详细错误信息已保存到：\n{file}",

            # 登录流程
            "login_press_1": "[账号 {current}/{total}] 按键: 1",
            "login_press_enter": "[账号 {current}/{total}] 等待响应...",
            "login_skip_plus_one": "[账号 {current}/{total}] 跳过+1输入，直接提取手机号",
            "login_paste_phone": "[账号 {current}/{total}] 粘贴手机号: {phone}",
            "login_submit_phone": "[账号 {current}/{total}] 提交手机号，等待验证码界面...",
            "login_no_screenshot": "[账号 {current}] ❌ 未截取验证码界面",
            "login_capture_hint": "请点击\"截取验证码界面\"按钮先截取验证码界面",
            "login_timeout": "[账号 {current}] ❌ 等待验证码界面超时",
            "login_no_url": "[账号 {current}] ❌ 未提供URL",
            "login_error": "[账号 {current}] ❌ 登录异常：{error}",
            "login_extracting": "[账号 {current}/{total}] 正在提取验证码...",
            "login_paste_code": "[账号 {current}/{total}] 粘贴验证码: {code}",
            "login_submit_code": "[账号 {current}/{total}] 提交验证码，等待2fa密码...",
            "login_paste_2fa": "[账号 {current}/{total}] 粘贴2fa密码: {pass_2fa}",
            "login_success": "[账号 {current}] ✅ 登录成功！",
            "login_no_2fa": "[账号 {current}] ⚠️ 未找到2fa密码",
            "login_no_code": "[账号 {current}] ❌ 未能提取到验证码",
            "login_retry_hint": "💡 提示：按F3继续下一个账户登录",

            # 提取验证码
            "extract_retry": "未提取到验证码，2秒后重试... (第{attempt}次)",
            "extract_failed": "提取失败：{error}",

            # 语言切换
            "language": "语言",
            "chinese": "中文",
            "english": "English",

            # 日志提示
            "log_location": "提示：所有错误信息会自动保存到：{file}",
        },
        EN: {
            # Window Title
            "window_title": f"Auto Login Assistant v{APP_VERSION}",

            # Stats
            "stats_title": "📊 Login Statistics",
            "total_accounts": "Total: {count}",
            "current_account": "Current: {count}",
            "success_count": "✓ Success: {count}",
            "fail_count": "✗ Failed: {count}",

            # Input Area
            "input_title": "📝 Account List",
            "input_placeholder": "One per line: phone|codeURL\n"
                                "e.g. +15795807280|https://miha.uk/tgapi/.../GetHTML\n\n"
                                "F4 - Open URL  |  F3 - Auto login (code & 2FA from URL)",

            # Status
            "status_title": "📋 Operation Log",
            "status_waiting": "Waiting...",

            # Buttons
            "btn_clear": "🗑️ Clear List",
            "btn_add_account": "➕ Add Account",
            "btn_retry": "🔄 Retry Failed Accounts",
            "btn_export": "📥 Export Failed",
            "btn_ayugram": "📱 Select AyuGram",
            "ayugram_path_placeholder": "Not selected (sessions will be written to tdata)",
            "api_settings_title": "⚙️ API Settings (optional)",
            "api_id_placeholder": "API ID (leave empty for default Desktop)",
            "api_hash_placeholder": "API Hash (leave empty for default Desktop)",
            "api_hint": "Uses official TelegramDesktop API by default, no change needed",
            "btn_capture": "📸 Capture Screen",
            "btn_test": "🔍 Test Screenshot",

            # Add Account Dialog
            "dialog_add_account_title": "Add Account",
            "dialog_add_account_phone": "Phone (e.g. +14582185432):",
            "dialog_add_account_url": "Verification URL (optional):",
            "msg_account_added": "Account added: {phone}",
            "msg_account_added_fail": "Please enter phone number",

            # Checkbox and Label
            "chk_input_plus_one": "Input +1",
            "lbl_start": "🚀 F3 Start  |  F5 Stop",
            "btn_stop": "🛑 Emergency Stop",

            # Messages
            "msg_no_failed_accounts": "No failed accounts to export",
            "msg_export_success": "Exported {count} failed accounts to {file}",
            "msg_no_failed_retry": "No failed accounts to retry",
            "msg_retry_loaded": "Failed accounts loaded, press F3 to retry",
            "msg_url_extracted": "Opened URL: {url}",
            "msg_url_complete": "URL extraction complete",
            "msg_login_complete": "All accounts login complete!",
            "msg_login_complete_with_fail": "Login complete! Success: {success}, Failed: {fail}",
            "msg_login_all_success": "Login complete! All accounts successful",

            # Screenshot
            "screenshot_title": "Capture Verification Screen",
            "screenshot_prepare": "📍 Prepare Verification Screen\n\n"
                                  "Please open the login interface first.\n\n"
                                  "Click OK to start screenshot tool.\n\n"
                                  "Select the verification screen area.\n"
                                  "After capturing, click \"Done\" button.",
            "screenshot_waiting": "📍 Waiting for screenshot...\n\n"
                                  "Screenshot tool activated (Windows+Shift+S).\n\n"
                                  "Please select the verification screen area.\n\n"
                                  "After capturing, click \"✅ Done\" button",
            "screenshot_cancel": "Cancel",
            "screenshot_done": "✅ Done",

            # Screenshot Errors
            "error_no_clipboard": "Could not get screenshot from clipboard!\n\n"
                                  "Please ensure:\n"
                                  "1. You have captured the screen\n"
                                  "2. Screenshot saved to clipboard\n"
                                  "3. No other content copied to clipboard",
            "error_capture_failed": "Screenshot capture failed",
            "error_verify_failed": "Screenshot verification failed.\n\n"
                                   "Suggestions:\n"
                                   "1. Ensure screenshot includes complete verification screen\n"
                                   "2. Recommended width: 800-1920 pixels\n"
                                   "3. Recapture, select larger area",
            "error_screenshot_saved": "Screenshot saved: {filename}",
            "error_screenshot_loaded": "✅ Screenshot loaded: {filename}",

            # Success
            "success_captured": "Screenshot captured and loaded successfully!\n\n"
                                "File: {filename}\n"
                                "Location: {path}\n\n"
                                "Press F3 to start auto login.",

            # Test Screenshot
            "test_no_screenshot": "❌ Screenshot file not found.\n\n"
                                  "Capture verification screen now?\n\n"
                                  "Program will verify after capture.",
            "test_no_screenshot_title": "No Screenshot Found",
            "test_capture_cancel": "Screenshot cancelled",
            "test_capture_failed": "❌ Screenshot capture failed",
            "test_not_captured": "❌ Please capture verification screen first",
            "test_check_failed": "Screenshot check failed",
            "test_checking": "Checking screenshot file...",
            "test_checking_file": "Trying to recognize screenshot on screen...",
            "test_checking_path": "Screenshot path: {path}",
            "test_checking_size": "File size: {size} bytes",
            "test_image_size": "Image size: {width} x {height}",
            "test_no_chinese": "❌ Chinese path detected, use English path",
            "test_res_small": "❌ Resolution too small: {w}x{h}",
            "test_res_large": "❌ Resolution too large: {w}x{h}",
            "test_res_ok": "✅ Resolution good: {w}x{h}",
            "test_res_info": "ℹ️ Resolution: {w}x{h} (recommended 800-1920 x 600-1080)",
            "test_success": "Screenshot Valid",
            "test_recognized": "✅ Screenshot recognized successfully!\n\n"
                               "File: {filename}\n"
                               "Location: {location}\n\n"
                               "🚀 Press F3 to start auto login!",
            "test_recognized_low_conf": "✅ Screenshot recognized! (low confidence)\n\n"
                                         "File: {filename}\n"
                                         "Location: {location}\n\n"
                                         "🚀 Press F3 to start auto login!",
            "test_failed": "Recognition Failed",
            "test_failed_msg": "❌ Could not find matching area on screen.\n\n"
                               "Possible reasons:\n"
                               "1. Screenshot doesn't match current screen\n"
                               "2. Screenshot contains dynamic content (e.g., time)\n"
                               "3. Verification screen not open or blocked\n\n"
                               "Recapture verification screen?",

            # Chinese Path Warning
            "warning_chinese_path": "⚠️ Chinese path detected: {path}",
            "warning_chinese_path_dir": "⚠️ Warning: Program folder contains Chinese characters",
            "warning_chinese_path_current": "Current path: {path}",
            "warning_chinese_path_advice": "Suggestion: Place program in English path",
            "warning_chinese_path_result": "May cause OpenCV reading errors",
            "warning_chinese_path_screenshot": "Suggestion: Place screenshot in program directory",

            # Status Messages
            "status_trigger_screenshot": "Screenshot tool opened, select verification screen",
            "status_screenshot_cancelled": "Screenshot cancelled",
            "status_getting_screenshot": "Getting screenshot from clipboard...",
            "status_screenshot_saved": "Screenshot saved: {filename}",
            "status_screenshot_verify_failed": "Screenshot verification failed",
            "status_error_log_saved": "Error log saved to: {file}",

            # Error Handling
            "error_loading_screenshot": "Cannot load screenshot: {error}",
            "error_screenshot_advice": "Suggestion: Use Paint to save as PNG format",
            "error_screen_timeout": "❌ Timeout: Screen {filename} not detected",
            "error_screen_attempts": "Attempts: {count}, Time: {timeout}s",
            "error_screen_advice": "Suggestion: Click \"Test Screenshot\" to verify",
            "error_opencv": "❌ Screenshot recognition failed\n\n"
                            "Possible causes:\n"
                            "1. Telegram window too small\n"
                            "2. Screenshot resolution too low or format incorrect\n"
                            "3. File path contains Chinese characters\n\n"
                            "Solutions:\n"
                            "1. Maximize Telegram window\n"
                            "2. Recapture, select larger area\n"
                            "3. Place program and screenshots in English path\n"
                            "4. Ensure screenshot is PNG format\n\n"
                            "Detailed error saved to:\n{file}",

            # Login Process
            "login_press_1": "[Account {current}/{total}] Press: 1",
            "login_press_enter": "[Account {current}/{total}] Waiting...",
            "login_skip_plus_one": "[Account {current}/{total}] Skip +1, extract phone",
            "login_paste_phone": "[Account {current}/{total}] Paste phone: {phone}",
            "login_submit_phone": "[Account {current}/{total}] Submit phone, waiting...",
            "login_no_screenshot": "[Account {current}] ❌ No screenshot",
            "login_capture_hint": "Please click \"Capture Screen\" first",
            "login_timeout": "[Account {current}] ❌ Timeout waiting for screen",
            "login_no_url": "[Account {current}] ❌ No URL provided",
            "login_error": "[Account {current}] ❌ Login error: {error}",
            "login_extracting": "[Account {current}/{total}] Extracting code...",
            "login_paste_code": "[Account {current}/{total}] Paste code: {code}",
            "login_submit_code": "[Account {current}/{total}] Submit code, waiting...",
            "login_paste_2fa": "[Account {current}/{total}] Paste 2FA: {pass_2fa}",
            "login_success": "[Account {current}] ✅ Login successful!",
            "login_no_2fa": "[Account {current}] ⚠️ No 2FA found",
            "login_no_code": "[Account {current}] ❌ Could not extract code",
            "login_retry_hint": "💡 Hint: Press F3 to continue with next account",

            # Extract Code
            "extract_retry": "No code extracted, retrying in 2s... (attempt {attempt})",
            "extract_failed": "Extraction failed: {error}",

            # Language Switch
            "language": "Language",
            "chinese": "中文",
            "english": "English",

            # Log
            "log_location": "Hint: All errors will be saved to: {file}",
        }
    }


# Telegram API — 默认使用 TelegramDesktop 官方凭证
# 使用 Android API ID (6) + 不匹配的设备指纹会被 Telegram 标记为可疑，导致冻结
DEFAULT_API_ID = 2040
DEFAULT_API_HASH = "b18441a1ff607e10a989891a5462e627"

# TelegramDesktop 基础参数（与官方 Desktop 客户端一致）
_TDESKTOP_BASE = {
    "app_version": "5.8.3 x64",
    "lang_code": "en",
    "system_lang_code": "en-US",
}

# 用于为每个账号生成稳定且不同的设备指纹
import hashlib

_WINDOWS_VERSIONS = [
    "Windows 10", "Windows 11",
]
_DESKTOP_MODELS = [
    "Desktop", "Laptop", "PC",
]

def generate_device_params(unique_id: str) -> dict:
    """根据 unique_id（通常是手机号）生成稳定的设备指纹，模拟 TelegramDesktop。"""
    h = int(hashlib.sha256(unique_id.encode()).hexdigest(), 16)
    return {
        "device_model": _DESKTOP_MODELS[h % len(_DESKTOP_MODELS)],
        "system_version": _WINDOWS_VERSIONS[(h >> 8) % len(_WINDOWS_VERSIONS)],
        "app_version": _TDESKTOP_BASE["app_version"],
        "lang_code": _TDESKTOP_BASE["lang_code"],
        "system_lang_code": _TDESKTOP_BASE["system_lang_code"],
    }


class HotkeyListener(QThread):
    """热键在独立线程中监听，通过信号转回主线程执行。"""
    f4_pressed = pyqtSignal()
    f3_pressed = pyqtSignal()
    f5_pressed = pyqtSignal()

    def run(self):
        keyboard.add_hotkey("F4", self.f4_pressed.emit)
        keyboard.add_hotkey("F3", self.f3_pressed.emit)
        keyboard.add_hotkey("F5", self.f5_pressed.emit)
        keyboard.wait()


class LoginWorker(QThread):
    """在后台线程通过 Telethon API 完成登录：发验证码 → 从 URL 拉取验证码与 2FA → sign_in。"""
    status_msg = pyqtSignal(str)
    finished_ok = pyqtSignal(str)  # 传出 2FA 密码（无则为空串）
    finished_fail = pyqtSignal(str)

    def __init__(self, phone, url, session_path, api_id, api_hash):
        super().__init__()
        self.phone = phone
        self.url = url
        self.session_path = session_path
        self.api_id = api_id
        self.api_hash = api_hash

    @staticmethod
    def _fetch_code_from_url(url, max_retries=30, interval=3):
        """从 URL 页面提取 id=code 与 id=pass2fa 的值。
        自动识别限频提示并等待对应秒数后重试。"""
        last_err = ""
        for attempt in range(max_retries):
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                code_el = soup.find("input", {"id": "code"})
                pass_el = soup.find("input", {"id": "pass2fa"})
                code = (code_el.get("value") or "").strip() if code_el else ""
                pass2fa = (pass_el.get("value") or "").strip() if pass_el else ""
                if code:
                    return code, pass2fa, ""
                err_el = soup.find(class_="error-message")
                if err_el:
                    err_text = err_el.get_text(strip=True)
                    last_err = err_text
                    wait_match = re.search(r"等待\s*(\d+)\s*秒", err_text)
                    if wait_match:
                        wait_sec = int(wait_match.group(1)) + 2
                        time.sleep(wait_sec)
                        continue
            except Exception as e:
                last_err = str(e)
            time.sleep(interval)
        return "", "", last_err or "轮询超时，页面无 code"

    def run(self):
        if not TELETHON_AVAILABLE:
            self.finished_fail.emit("未安装 telethon，请执行: pip install telethon")
            return
        try:
            asyncio.run(self._login())
        except Exception as e:
            self.finished_fail.emit(f"{type(e).__name__}: {e}")

    async def _login(self):
        dp = generate_device_params(self.phone)
        client = TelegramClient(
            self.session_path,
            self.api_id,
            self.api_hash,
            device_model=dp["device_model"],
            system_version=dp["system_version"],
            app_version=dp["app_version"],
            lang_code=dp["lang_code"],
            system_lang_code=dp["system_lang_code"],
        )
        used_pass2fa = ""
        try:
            await client.connect()
            if await client.is_user_authorized():
                self.status_msg.emit(f"已登录: {self.phone}")
                # 已登录也需要从 URL 获取 2FA 密码，供 tdata 转换使用
                _, url_pass2fa, _ = self._fetch_code_from_url(self.url, max_retries=1, interval=0)
                self.finished_ok.emit(url_pass2fa)
                return

            self.status_msg.emit(f"发送验证码: {self.phone}")
            try:
                sent = await client.send_code_request(self.phone)
                self.status_msg.emit(f"验证码已发送 (hash: {sent.phone_code_hash[:8]}…)")
            except FloodWaitError as e:
                self.finished_fail.emit(f"频率限制，需等待 {e.seconds} 秒")
                return
            except PhoneNumberBannedError:
                self.finished_fail.emit("手机号已被封禁")
                return
            except PhoneNumberInvalidError:
                self.finished_fail.emit("手机号格式无效")
                return

            # 发码后等待几秒，让接码平台收到新验证码（避免拿到旧码）
            self.status_msg.emit("等待新验证码到达…")
            await asyncio.sleep(5)

            self.status_msg.emit("从 URL 获取验证码…")
            code, pass2fa, fetch_err = self._fetch_code_from_url(self.url)
            if not code:
                self.finished_fail.emit(f"未能从 URL 获取验证码 ({fetch_err})")
                return

            # 尝试提交验证码，若无效则重新获取一次
            for attempt in range(2):
                self.status_msg.emit(f"获取到验证码: {code}，提交中…")
                try:
                    await client.sign_in(self.phone, code)
                    break
                except SessionPasswordNeededError:
                    if pass2fa:
                        self.status_msg.emit("需要 2FA，提交密码…")
                        await client.sign_in(password=pass2fa)
                        used_pass2fa = pass2fa
                        break
                    else:
                        self.finished_fail.emit("需要 2FA 密码，URL 中未提供")
                        return
                except PhoneCodeInvalidError:
                    if attempt == 0:
                        self.status_msg.emit("验证码无效，重新发码并等待…")
                        await client.send_code_request(self.phone)
                        await asyncio.sleep(8)
                        code, pass2fa, fetch_err = self._fetch_code_from_url(self.url)
                        if not code:
                            self.finished_fail.emit(f"重试后仍未获取到验证码 ({fetch_err})")
                            return
                    else:
                        self.finished_fail.emit("验证码无效或已过期（重试后仍失败）")
                        return

            me = await client.get_me()
            name = me.first_name or ""
            uname = f"@{me.username}" if me.username else ""
            self.status_msg.emit(f"登录成功: {name} {uname} ({self.phone})")
            self.finished_ok.emit(used_pass2fa)
        except Exception as e:
            self.finished_fail.emit(f"{type(e).__name__}: {e}")
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass


class SyncToAyuGramWorker(QThread):
    """在独立子进程中将 Telethon 会话写入 AyuGram 的 tdata（避免 opentele 污染主进程的 telethon）。"""
    finished_ok = pyqtSignal(str)
    finished_fail = pyqtSignal(str)

    _SYNC_SCRIPT = r'''
import sys, asyncio, os
session_path, tdata_dir = sys.argv[1], sys.argv[2]
api_id, api_hash = int(sys.argv[3]), sys.argv[4]
phone = sys.argv[5] if len(sys.argv) > 5 else ""
pass2fa = sys.argv[6] if len(sys.argv) > 6 else ""
from opentele.tl import TelegramClient as OTeleClient
from opentele.td import TDesktop, Account
from opentele.api import API, UseCurrentSession, CreateNewSession
async def sync():
    if phone:
        api = API.TelegramDesktop.Generate(system="windows", unique_id=phone)
    else:
        api = API.TelegramDesktop
    client = OTeleClient(session=session_path, api=api)
    await client.connect()
    if not await client.is_user_authorized():
        print("ERR:会话未授权", flush=True); return
    os.makedirs(tdata_dir, exist_ok=True)
    # 加载已有 tdata（如果存在），将新账号追加进去而不是覆盖
    tdesk = TDesktop(tdata_dir, api=API.TelegramDesktop)
    if tdesk.isLoaded():
        existing_ids = {acc.UserId for acc in tdesk.accounts}
        me = await client.get_me()
        if me.id in existing_ids:
            print("OK:SKIP already exists", flush=True)
            await client.disconnect()
            return
        await Account.FromTelethon(client, flag=CreateNewSession, owner=tdesk, api=api, password=pass2fa or None)
    else:
        tdesk = await TDesktop.FromTelethon(client, flag=CreateNewSession, api=api, password=pass2fa or None)
    tdesk.SaveTData(tdata_dir)
    print("OK", flush=True)
    await client.disconnect()
asyncio.run(sync())
'''

    def __init__(self, session_path, tdata_dir, api_id, api_hash, phone="", pass2fa=""):
        super().__init__()
        self.session_path = session_path
        self.tdata_dir = tdata_dir
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.pass2fa = pass2fa

    def run(self):
        if not OPENETELE_AVAILABLE:
            self.finished_fail.emit("未安装 opentele")
            return
        try:
            result = subprocess.run(
                [sys.executable, "-c", self._SYNC_SCRIPT,
                 self.session_path, self.tdata_dir,
                 str(self.api_id), str(self.api_hash), self.phone, self.pass2fa],
                capture_output=True, text=True, timeout=60
            )
            output = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            if output.startswith("OK"):
                self.finished_ok.emit(output)
            elif output.startswith("ERR:"):
                self.finished_fail.emit(output[4:])
            else:
                self.finished_fail.emit(err[-300:] if err else "子进程无输出")
        except subprocess.TimeoutExpired:
            self.finished_fail.emit("同步超时（60秒）")
        except Exception as e:
            self.finished_fail.emit(f"{type(e).__name__}: {e}")


class ExtractorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.current_language = Translations.ZH  # 默认语言：中文

        # 获取程序所在目录（支持Python脚本和打包后的EXE）
        if getattr(sys, 'frozen', False):
            # 如果是打包后的EXE
            self.script_dir = os.path.dirname(sys.executable)
            print(f"[启动] 运行模式: 打包的EXE")
            print(f"[启动] EXE路径: {sys.executable}")
        else:
            # 如果是Python脚本
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
            print(f"[启动] 运行模式: Python脚本")
            print(f"[启动] 脚本路径: {__file__}")

        print(f"[启动] 程序目录: {self.script_dir}")

        # 设置窗口标题
        self.setWindowTitle(self.get_text("window_title"))
        self.setFixedSize(750, 640)

        # 配置文件路径
        self.config_file = os.path.join(self.script_dir, "config.json")

        # 错误日志文件路径
        self.error_log_file = os.path.join(self.script_dir, "error_log.txt")

        # 失败账号导出文件路径
        self.failed_file = os.path.join(self.script_dir, "failed_accounts.txt")
        # Telegram API（可从 config 覆盖）
        self.api_id = DEFAULT_API_ID
        self.api_hash = DEFAULT_API_HASH
        self.sessions_dir = os.path.join(self.script_dir, "sessions")
        self.login_worker = None
        self.ayugram_exe_path = ""
        self.sync_worker = None
        self._stop_requested = False

        # 状态统计变量
        self.total_accounts = 0
        self.success_count = 0
        self.fail_count = 0
        self.current_index = 0
        self.failed_accounts = []

        # 设置UI样式
        self.setup_ui()
        self.setup_styles()

        # 数据
        self.lines = []
        self.url_index = 0
        self.num_index = 0

        # 清空错误日志（仅保留最后100行，避免文件过大）
        try:
            if os.path.exists(self.error_log_file):
                with open(self.error_log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if len(lines) > 100:
                    with open(self.error_log_file, 'w', encoding='utf-8') as f:
                        f.writelines(lines[-100:])
        except:
            pass

        # 加载上次保存的配置
        self.load_config()

        # 显示错误日志位置提示
        self.update_status(self.get_text("log_location", file=os.path.basename(self.error_log_file)))

        # 检查程序目录是否包含中文
        if self.contains_chinese(self.script_dir):
            self.update_status(f"⚠️ 程序路径含中文：{self.script_dir}")

        # 启动时检查是否有旧 API 的 session 文件
        self._check_old_sessions()

        # 启动热键监听（信号在主线程执行，避免按 F3 闪退）
        self.listener = HotkeyListener()
        self.listener.f4_pressed.connect(self.extract_next_url)
        self.listener.f3_pressed.connect(self.extract_next_number)
        self.listener.f5_pressed.connect(self.emergency_stop)
        self.listener.start()

        # 后台检查更新
        threading.Thread(target=self._check_update, daemon=True).start()

    def _check_update(self):
        """后台检查 GitHub Release，若有新版本则提示用户。"""
        try:
            r = requests.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                timeout=10
            )
            if r.status_code != 200:
                return
            data = r.json()
            tag = data.get("tag_name", "")
            remote_ver = tag.lstrip("v")
            if not remote_ver or remote_ver == APP_VERSION:
                return
            if self._ver_tuple(remote_ver) <= self._ver_tuple(APP_VERSION):
                return
            assets = data.get("assets", [])
            exe_asset = next((a for a in assets if a["name"].endswith(".exe")), None)
            if not exe_asset:
                return
            download_url = exe_asset["browser_download_url"]
            exe_name = exe_asset["name"]
            QTimer.singleShot(0, lambda: self._prompt_update(remote_ver, download_url, exe_name))
        except Exception:
            pass

    @staticmethod
    def _ver_tuple(v):
        try:
            return tuple(int(x) for x in v.split("."))
        except Exception:
            return (0,)

    def _prompt_update(self, new_ver, download_url, exe_name):
        reply = QMessageBox.question(
            self,
            "发现新版本" if self.current_language == Translations.ZH else "Update Available",
            (f"发现新版本 v{new_ver}（当前 v{APP_VERSION}）\n是否立即更新？"
             if self.current_language == Translations.ZH else
             f"New version v{new_ver} available (current v{APP_VERSION})\nUpdate now?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self._do_update(download_url, exe_name)

    def _do_update(self, download_url, exe_name):
        """下载新版本 EXE 并替换当前程序。"""
        self.update_status("正在下载更新…")
        try:
            r = requests.get(download_url, stream=True, timeout=120)
            r.raise_for_status()
            current_exe = sys.executable if getattr(sys, 'frozen', False) else None
            if not current_exe:
                self.update_status("⚠️ 非 EXE 模式，请手动下载更新")
                return
            new_path = current_exe + ".new"
            with open(new_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            updater_path = os.path.join(self.script_dir, "updater.py")
            with open(updater_path, "w", encoding="utf-8") as f:
                f.write(
                    "import sys,time,shutil,subprocess\n"
                    "old,new=sys.argv[1],sys.argv[2]\n"
                    "time.sleep(1)\n"
                    "try:\n"
                    "    shutil.move(new,old)\n"
                    "except: sys.exit(1)\n"
                    "subprocess.Popen([old])\n"
                )
            subprocess.Popen([sys.executable, updater_path, current_exe, new_path])
            QApplication.quit()
        except Exception as e:
            self.update_status(f"⚠️ 更新失败: {e}")

    def contains_chinese(self, text):
        """检测文本中是否包含中文字符"""
        return any('\u4e00' <= char <= '\u9fff' for char in text)

    def get_program_directory(self):
        """
        获取程序所在目录（支持Python脚本和打包后的EXE）

        Returns:
            str: 程序所在目录的绝对路径
        """
        if getattr(sys, 'frozen', False):
            # 如果是打包后的EXE
            return os.path.dirname(sys.executable)
        else:
            # 如果是Python脚本
            return os.path.dirname(os.path.abspath(__file__))

    def get_text(self, key, **kwargs):
        """
        获取当前语言的文本

        Args:
            key: 文本键名
            **kwargs: 用于格式化字符串的参数

        Returns:
            str: 格式化后的文本
        """
        text = Translations.STRINGS[self.current_language].get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text

    def switch_language(self, index):
        """
        切换语言

        Args:
            index: 语言选择框的索引（0=中文，1=英文）
        """
        new_lang = Translations.ZH if index == 0 else Translations.EN
        if new_lang != self.current_language:
            self.current_language = new_lang
            self.update_ui_language()
            self.save_config()

    def update_ui_language(self):
        """更新所有UI元素的语言"""
        # 更新窗口标题
        self.setWindowTitle(self.get_text("window_title"))

        # 更新标题标签
        self.title_label.setText("🚀 " + self.get_text("window_title"))

        # 更新统计面板
        self.stats_group.setTitle(self.get_text("stats_title"))
        self.update_stats()

        # 更新输入区域
        self.input_group.setTitle(self.get_text("input_title"))
        self.text_edit.setPlaceholderText(self.get_text("input_placeholder"))

        # 更新状态区域
        self.status_group.setTitle(self.get_text("status_title"))
        pass  # 日志面板无需按语言重置

        # 更新按钮
        self.start_label.setText(self.get_text("lbl_start"))
        self.stop_btn.setText(self.get_text("btn_stop"))
        self.clear_btn.setText(self.get_text("btn_clear"))
        self.retry_btn.setText(self.get_text("btn_retry"))
        self.export_btn.setText(self.get_text("btn_export"))
        self.ayugram_btn.setText(self.get_text("btn_ayugram"))
        if not getattr(self, "ayugram_exe_path", ""):
            self.ayugram_path_label.setText(self.get_text("ayugram_path_placeholder"))
        if hasattr(self, "api_hint_label"):
            self.api_hint_label.setText(self.get_text("api_hint"))
            self.api_id_edit.setPlaceholderText(self.get_text("api_id_placeholder"))
            self.api_hash_edit.setPlaceholderText(self.get_text("api_hash_placeholder"))

        # 更新语言选择器文本
        self.language_label.setText(self.get_text("language") + ":")
        self.language_combo.setItemText(0, self.get_text("chinese"))
        self.language_combo.setItemText(1, self.get_text("english"))

    def setup_ui(self):
        """设置UI布局"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 标题和语言选择行
        title_row = QHBoxLayout()

        self.title_label = QLabel("🚀 " + self.get_text("window_title"))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))

        # 语言选择器
        self.language_label = QLabel(self.get_text("language") + ":")
        self.language_label.setFont(QFont("Microsoft YaHei", 10))

        self.language_combo = QComboBox()
        self.language_combo.addItems([self.get_text("chinese"), self.get_text("english")])
        self.language_combo.setCurrentIndex(0 if self.current_language == Translations.ZH else 1)
        self.language_combo.currentIndexChanged.connect(self.switch_language)
        self.language_combo.setStyleSheet("""
            QComboBox {
                padding: 5px 10px;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                background-color: white;
                font-size: 10px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)

        title_row.addWidget(self.title_label)
        title_row.addStretch()
        title_row.addWidget(self.language_label)
        title_row.addWidget(self.language_combo)

        main_layout.addLayout(title_row)

        # 状态统计面板
        self.stats_group = QGroupBox(self.get_text("stats_title"))
        stats_layout = QHBoxLayout()

        self.total_label = self.create_stat_label(self.get_text("total_accounts", count=0), "#4CAF50")
        self.current_label = self.create_stat_label(self.get_text("current_account", count=0), "#2196F3")
        self.success_label = self.create_stat_label(self.get_text("success_count", count=0), "#4CAF50")
        self.fail_label = self.create_stat_label(self.get_text("fail_count", count=0), "#F44336")

        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.current_label)
        stats_layout.addWidget(self.success_label)
        stats_layout.addWidget(self.fail_label)
        self.stats_group.setLayout(stats_layout)
        main_layout.addWidget(self.stats_group)

        # 输入区域
        self.input_group = QGroupBox(self.get_text("input_title"))
        input_layout = QVBoxLayout()

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(self.get_text("input_placeholder"))
        self.text_edit.setMaximumHeight(200)
        input_layout.addWidget(self.text_edit)

        self.input_group.setLayout(input_layout)
        main_layout.addWidget(self.input_group)

        # 当前操作状态
        self.status_group = QGroupBox(self.get_text("status_title"))
        status_layout = QVBoxLayout()
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFont(QFont("Consolas", 9))
        self.log_edit.setMaximumHeight(140)
        self.log_edit.setStyleSheet("""
            QTextEdit {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 6px;
                color: #333;
            }
        """)
        status_layout.addWidget(self.log_edit)
        self.status_group.setLayout(status_layout)
        main_layout.addWidget(self.status_group)

        # 按钮和选项区域
        control_layout = QVBoxLayout()

        # 第一行：提示和复选框
        control_row1 = QHBoxLayout()

        self.start_label = QLabel(self.get_text("lbl_start"))
        self.start_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #4CAF50;
                padding: 10px 15px;
                background-color: #E8F5E9;
                border: 2px solid #4CAF50;
                border-radius: 5px;
            }
        """)

        self.stop_btn = QPushButton(self.get_text("btn_stop"))
        self.stop_btn.clicked.connect(self.emergency_stop)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336; color: white; border: none;
                border-radius: 5px; padding: 10px 18px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #D32F2F; }
            QPushButton:disabled { background-color: #BDBDBD; }
        """)

        control_row1.addWidget(self.start_label)
        control_row1.addWidget(self.stop_btn)
        control_row1.addStretch()

        # 第二行：操作按钮
        control_row2 = QHBoxLayout()

        self.clear_btn = QPushButton(self.get_text("btn_clear"))
        self.clear_btn.clicked.connect(self.clear_text)
        self.clear_btn.setMinimumWidth(150)

        self.retry_btn = QPushButton(self.get_text("btn_retry"))
        self.retry_btn.clicked.connect(self.retry_failed_accounts)
        self.retry_btn.setEnabled(False)
        self.retry_btn.setMinimumWidth(170)

        self.export_btn = QPushButton(self.get_text("btn_export"))
        self.export_btn.clicked.connect(self.export_failed_accounts)
        self.export_btn.setEnabled(False)
        self.export_btn.setMinimumWidth(150)

        self.ayugram_btn = QPushButton(self.get_text("btn_ayugram"))
        self.ayugram_btn.clicked.connect(self._choose_ayugram)
        self.ayugram_btn.setMinimumWidth(130)
        self.ayugram_path_label = QLabel(self.get_text("ayugram_path_placeholder"))
        self.ayugram_path_label.setStyleSheet("color: #666; font-size: 11px;")
        self.ayugram_path_label.setToolTip("AyuGram 的 tdata 在其 exe 同目录下的 tdata 文件夹内")

        control_row2.addWidget(self.clear_btn)
        control_row2.addWidget(self.retry_btn)
        control_row2.addWidget(self.export_btn)
        control_row2.addWidget(self.ayugram_btn)
        control_row2.addWidget(self.ayugram_path_label, 1)

        # 第三行：API 设置（可选）
        control_row3 = QHBoxLayout()
        self.api_hint_label = QLabel(self.get_text("api_hint"))
        self.api_hint_label.setStyleSheet("color: #888; font-size: 10px;")

        self.api_id_edit = QLineEdit()
        self.api_id_edit.setPlaceholderText(self.get_text("api_id_placeholder"))
        self.api_id_edit.setMaximumWidth(180)
        self.api_id_edit.setStyleSheet("padding: 4px 6px; font-size: 11px; border: 1px solid #ccc; border-radius: 3px;")
        self.api_id_edit.editingFinished.connect(self._on_api_changed)

        self.api_hash_edit = QLineEdit()
        self.api_hash_edit.setPlaceholderText(self.get_text("api_hash_placeholder"))
        self.api_hash_edit.setMaximumWidth(260)
        self.api_hash_edit.setStyleSheet("padding: 4px 6px; font-size: 11px; border: 1px solid #ccc; border-radius: 3px;")
        self.api_hash_edit.editingFinished.connect(self._on_api_changed)

        control_row3.addWidget(self.api_hint_label)
        control_row3.addWidget(self.api_id_edit)
        control_row3.addWidget(self.api_hash_edit)
        control_row3.addStretch()

        control_layout.addLayout(control_row1)
        control_layout.addLayout(control_row2)
        control_layout.addLayout(control_row3)

        main_layout.addLayout(control_layout)

        self.setLayout(main_layout)

    def create_stat_label(self, text, color):
        """创建统计标签"""
        label = QLabel(text)
        label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        label.setStyleSheet(f"color: {color}; padding: 5px; border: 1px solid {color}; border-radius: 5px;")
        label.setAlignment(Qt.AlignCenter)
        return label

    def setup_styles(self):
        """设置样式"""
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                font-family: "Microsoft YaHei";
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTextEdit {
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 8px;
                font-family: "Consolas", 10px;
                background-color: #fafafa;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 15px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

    def update_stats(self):
        """更新统计信息"""
        self.total_label.setText(self.get_text("total_accounts", count=self.total_accounts))
        self.current_label.setText(self.get_text("current_account", count=self.current_index + 1))
        self.success_label.setText(self.get_text("success_count", count=self.success_count))
        self.fail_label.setText(self.get_text("fail_count", count=self.fail_count))

    def update_status(self, message, **kwargs):
        """追加一条日志到操作日志面板，自动滚动到底部。"""
        if message in Translations.STRINGS[self.current_language]:
            display_message = self.get_text(message, **kwargs)
        else:
            display_message = message.format(**kwargs) if kwargs else message

        ts = datetime.now().strftime("%H:%M:%S")
        self.log_edit.append(f"[{ts}] {display_message}")
        self.log_edit.verticalScrollBar().setValue(
            self.log_edit.verticalScrollBar().maximum()
        )

    def save_error_log(self, title, error_message):
        """保存错误日志到文件"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_content = f"""
{'='*60}
时间: {timestamp}
标题: {title}
{'='*60}
{error_message}
{'='*60}

"""
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(log_content)

            self.update_status(f"❌ 错误信息已保存到：{self.error_log_file}")
            return True
        except Exception as e:
            self.update_status(f"保存错误日志失败: {str(e)}")
            return False

    def _choose_ayugram(self):
        """选择 AyuGram 程序路径，登录成功后将把会话写入其 tdata 目录。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 AyuGram 程序",
            os.path.dirname(self.ayugram_exe_path) if self.ayugram_exe_path else "",
            "可执行文件 (*.exe);;全部 (*.*)"
        )
        if path:
            self.ayugram_exe_path = path
            self.ayugram_path_label.setText(path)
            self.ayugram_path_label.setToolTip(f"tdata 目录: {os.path.join(os.path.dirname(path), 'tdata')}")
            self.save_config()
            self.update_status("已设置 AyuGram 路径，登录成功后将自动写入 tdata")

    def _on_api_changed(self):
        """用户修改了 API ID/Hash 输入框时更新内部值。"""
        id_text = self.api_id_edit.text().strip()
        hash_text = self.api_hash_edit.text().strip()
        if id_text and hash_text:
            try:
                self.api_id = int(id_text)
                self.api_hash = hash_text
            except ValueError:
                self.update_status("⚠️ API ID 必须是数字")
                return
        else:
            self.api_id = DEFAULT_API_ID
            self.api_hash = DEFAULT_API_HASH
        self.save_config()

    def _check_old_sessions(self):
        """启动时检查 sessions 目录的 API 标记，若与当前不一致则提醒。"""
        if not os.path.isdir(self.sessions_dir):
            return
        api_marker = os.path.join(self.sessions_dir, ".api_id")
        try:
            old_marker = open(api_marker, "r").read().strip() if os.path.exists(api_marker) else ""
        except Exception:
            old_marker = ""
        if not old_marker or old_marker == str(self.api_id):
            return
        session_count = sum(1 for f in os.listdir(self.sessions_dir) if f.endswith(".session"))
        if session_count:
            self.update_status(
                f"⚠️ 发现 {session_count} 个旧 API (ID {old_marker}) 的 session 文件，"
                f"登录时将自动清理并重新登录"
            )

    def save_config(self):
        """保存当前状态到配置文件"""
        try:
            config = {
                "lines": self.lines,
                "url_index": self.url_index,
                "num_index": self.num_index,
                "current_index": self.current_index,
                "total_accounts": self.total_accounts,
                "success_count": self.success_count,
                "fail_count": self.fail_count,
                "failed_accounts": self.failed_accounts,
                "text_content": self.text_edit.toPlainText(),
                "api_id": getattr(self, "api_id", DEFAULT_API_ID),
                "api_hash": getattr(self, "api_hash", DEFAULT_API_HASH),
                "ayugram_exe_path": getattr(self, "ayugram_exe_path", ""),
                "language": self.current_language
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            # print("配置已保存")  # 调试用
        except Exception as e:
            print(f"保存配置失败: {e}")

    def load_config(self):
        """从配置文件加载上次的状态"""
        try:
            if not os.path.exists(self.config_file):
                return False

            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 恢复状态
            self.lines = config.get("lines", [])
            self.url_index = config.get("url_index", 0)
            self.num_index = config.get("num_index", 0)
            self.current_index = config.get("current_index", 0)
            self.total_accounts = config.get("total_accounts", 0)
            self.success_count = config.get("success_count", 0)
            self.fail_count = config.get("fail_count", 0)
            self.failed_accounts = config.get("failed_accounts", [])
            text_content = config.get("text_content", "")
            saved_api_id = config.get("api_id", DEFAULT_API_ID)
            saved_api_hash = config.get("api_hash", DEFAULT_API_HASH)
            if isinstance(saved_api_id, int) and saved_api_id > 0 and saved_api_hash:
                self.api_id = saved_api_id
                self.api_hash = saved_api_hash
            else:
                self.api_id = DEFAULT_API_ID
                self.api_hash = DEFAULT_API_HASH
            self.ayugram_exe_path = config.get("ayugram_exe_path", "")

            # 恢复语言设置
            saved_language = config.get("language", Translations.ZH)
            if saved_language in [Translations.ZH, Translations.EN]:
                self.current_language = saved_language
                # 更新语言选择器的选中项
                self.language_combo.blockSignals(True)
                self.language_combo.setCurrentIndex(0 if self.current_language == Translations.ZH else 1)
                self.language_combo.blockSignals(False)
                # 更新UI语言
                self.update_ui_language()

            # 恢复文本框内容
            self.text_edit.setText(text_content)

            # 恢复 AyuGram 路径显示
            if hasattr(self, "ayugram_path_label"):
                self.ayugram_path_label.setText(
                    self.ayugram_exe_path if self.ayugram_exe_path
                    else self.get_text("ayugram_path_placeholder")
                )

            # 恢复 API 输入框（仅当用户曾自定义时显示）
            if hasattr(self, "api_id_edit"):
                if self.api_id != DEFAULT_API_ID:
                    self.api_id_edit.setText(str(self.api_id))
                if self.api_hash != DEFAULT_API_HASH:
                    self.api_hash_edit.setText(self.api_hash)

            # 更新统计信息
            self.update_stats()

            # 更新按钮状态
            if self.failed_accounts:
                self.retry_btn.setEnabled(True)
                self.export_btn.setEnabled(True)

            return True

        except Exception as e:
            print(f"加载配置失败: {e}")
            return False

    def clear_text(self):
        """清空文本"""
        self.text_edit.clear()
        self.lines = []
        self.url_index = 0
        self.num_index = 0
        self.total_accounts = 0
        self.current_index = 0
        self.success_count = 0
        self.fail_count = 0
        self.failed_accounts = []
        self.update_stats()
        self.log_edit.clear()
        self.retry_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.save_config()  # 自动保存配置

    def load_lines(self):
        """加载账号列表"""
        text = self.text_edit.toPlainText().strip()
        self.lines = [line for line in text.splitlines() if "|" in line]
        self.total_accounts = len(self.lines)
        self.update_stats()
        self.save_config()  # 自动保存配置

    def record_failed_account(self, line):
        """记录失败账号"""
        self.failed_accounts.append(line)
        self.fail_count += 1
        self.update_stats()
        self.retry_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.save_config()  # 自动保存配置

    def export_failed_accounts(self):
        """导出失败账号"""
        if not self.failed_accounts:
            QMessageBox.information(self, self.get_text("msg_no_failed_accounts"), "")
            return

        # 保存到文件
        with open(self.failed_file, 'w', encoding='utf-8') as f:
            for account in self.failed_accounts:
                f.write(account + '\n')

        QMessageBox.information(self, "成功", self.get_text("msg_export_success",
                                                             count=len(self.failed_accounts),
                                                             file=os.path.basename(self.failed_file)))

    def retry_failed_accounts(self):
        """重新登录失败账号"""
        if not self.failed_accounts:
            QMessageBox.information(self, "提示", "没有失败账号需要重新登录")
            return

        # 将失败账号放回文本框
        self.text_edit.setText('\n'.join(self.failed_accounts))

        # 重置索引和统计
        self.failed_accounts = []
        self.fail_count = 0
        self.url_index = 0
        self.num_index = 0
        self.current_index = 0

        self.update_stats()
        self.retry_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.save_config()  # 自动保存配置

        QMessageBox.information(self, "提示", "失败账号已加载到列表中，请按F3重新登录")

    def emergency_stop(self):
        """紧急停止：中止当前和后续所有登录任务。"""
        self._stop_requested = True
        self.stop_btn.setEnabled(False)
        self.update_status("🛑 已请求停止，等待当前账号完成后停止…")
        if self.login_worker and self.login_worker.isRunning():
            self.login_worker.terminate()
            self.login_worker = None
        if self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.terminate()
            self.sync_worker = None
        self.update_status("🛑 已停止")

    def extract_next_url(self):
        """提取并打开URL"""
        self.load_lines()
        if self.url_index >= len(self.lines):
            self.update_status("网址提取完毕")
            return

        line = self.lines[self.url_index]
        self.url_index += 1

        match = re.search(r"https?://\S+", line)
        if match:
            url = match.group()
            webbrowser.open(url)
            self.update_status(f"已打开网址：{url}")

        self.save_config()  # 自动保存配置

    def extract_code_from_html(self, url, max_retries=4):
        """从URL提取设备验证码和2fa密码，支持自动重试"""
        for attempt in range(max_retries):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # 提取设备验证码 (id="code")
                code_input = soup.find('input', {'id': 'code'})
                device_code = code_input.get('value', '').strip() if code_input else ''

                # 提取2fa/密码 (id="pass2fa")
                pass_input = soup.find('input', {'id': 'pass2fa'})
                pass_2fa = pass_input.get('value', '').strip() if pass_input else ''

                if device_code:  # 如果成功提取到验证码，立即返回
                    return device_code, pass_2fa

                # 如果没有提取到验证码，等待2秒后重试
                if attempt < max_retries - 1:
                    self.update_status("extract_retry", attempt=attempt + 1)
                    time.sleep(2)

            except Exception as e:
                self.update_status("extract_failed", error=str(e))
                if attempt < max_retries - 1:
                    time.sleep(2)

        return '', ''  # 所有尝试都失败

    def extract_next_number(self):
        """F3：按行取 手机号|URL，用 Telethon API 发码并轮询 URL 获取验证码与 2FA 后登录。"""
        self._stop_requested = False
        self.stop_btn.setEnabled(True)
        self.load_lines()

        if not self.lines:
            self.update_status("⚠️ 账号列表为空，请先粘贴 手机号|验证码URL")
            self.stop_btn.setEnabled(False)
            return

        # 如果所有账号已处理完，重置并重新开始
        if self.num_index >= len(self.lines):
            self.num_index = 0
            self.current_index = 0
            self.success_count = 0
            self.fail_count = 0
            self.failed_accounts = []
            self.retry_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.update_stats()
            self.log_edit.clear()
            self.update_status("🔄 重新开始登录所有账号…")

        self._do_login_current()

    def _do_login_current(self):
        """启动当前 num_index 指向的账号的登录流程。"""
        if self._stop_requested:
            return
        if self.login_worker and self.login_worker.isRunning():
            self.update_status("上一账号登录中，请稍候…")
            return

        line = self.lines[self.num_index].strip()
        parts = line.split("|")
        phone = (parts[0] or "").strip()
        url = (parts[1] or "").strip() if len(parts) > 1 else ""

        if not phone:
            self.num_index += 1
            self.update_stats()
            QTimer.singleShot(100, self._process_next_account)
            return
        if not url or not url.startswith("http"):
            self.update_status(f"❌ 格式错误，需要 手机号|验证码URL：{line[:50]}…")
            self.record_failed_account(line)
            self.num_index += 1
            self.update_stats()
            self.save_config()
            QTimer.singleShot(100, self._process_next_account)
            return

        phone = phone if phone.startswith("+") else "+" + re.sub(r"\D", "", phone)
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 10:
            self.update_status(f"❌ 手机号过短：{phone}")
            self.record_failed_account(line)
            self.num_index += 1
            self.update_stats()
            self.save_config()
            QTimer.singleShot(100, self._process_next_account)
            return

        os.makedirs(self.sessions_dir, exist_ok=True)
        session_path = os.path.join(self.sessions_dir, digits + ".session")

        # 用标记文件记录 sessions 目录使用的 API ID，切换 API 时自动清理旧 session
        api_marker = os.path.join(self.sessions_dir, ".api_id")
        try:
            old_marker = open(api_marker, "r").read().strip() if os.path.exists(api_marker) else ""
            current_marker = str(self.api_id)
            if old_marker and old_marker != current_marker and os.path.exists(session_path):
                try:
                    os.remove(session_path)
                    self.update_status(f"已清理旧 API 的 session: {digits}")
                except PermissionError:
                    self.update_status(f"⚠️ 无法删除旧 session（文件被占用），将尝试覆盖: {digits}")
            with open(api_marker, "w") as f:
                f.write(current_marker)
        except Exception:
            pass

        self.current_index = self.num_index
        self.update_status(f"[{self.current_index + 1}/{len(self.lines)}] 开始登录: {phone}")
        self.update_stats()

        self.login_worker = LoginWorker(
            phone, url, session_path,
            getattr(self, "api_id", DEFAULT_API_ID),
            getattr(self, "api_hash", DEFAULT_API_HASH)
        )
        self.login_worker.status_msg.connect(lambda msg: self.update_status(msg))
        self.login_worker.finished_ok.connect(self._on_login_ok)
        self.login_worker.finished_fail.connect(self._on_login_fail)
        self.login_worker.start()

    def _on_login_ok(self, pass2fa):
        self.login_worker = None
        self.success_count += 1
        done_index = self.num_index
        self.num_index += 1
        self.update_stats()
        self.save_config()
        self.update_status("login_success", current=self.num_index)

        # 若已选择 AyuGram，将本次登录的会话写入其 tdata
        ayugram_path = getattr(self, "ayugram_exe_path", "")
        if ayugram_path and os.path.isfile(ayugram_path) and done_index < len(self.lines):
            line = self.lines[done_index].strip()
            phone = (line.split("|")[0] or "").strip()
            digits = re.sub(r"\D", "", phone)
            if digits:
                session_path = os.path.join(self.sessions_dir, digits + ".session")
                tdata_dir = os.path.join(os.path.dirname(ayugram_path), "tdata")
                if self.sync_worker and self.sync_worker.isRunning():
                    self.update_status("正在同步上一账号到 AyuGram，请稍候…")
                    QTimer.singleShot(3000, self._process_next_account)
                    return
                self.sync_worker = SyncToAyuGramWorker(
                    session_path, tdata_dir,
                    getattr(self, "api_id", DEFAULT_API_ID),
                    getattr(self, "api_hash", DEFAULT_API_HASH),
                    phone=phone,
                    pass2fa=pass2fa or "",
                )
                self.sync_worker.finished_ok.connect(self._on_sync_ayugram_ok)
                self.sync_worker.finished_fail.connect(self._on_sync_ayugram_fail)
                self.sync_worker.start()
                self.update_status("正在将会话写入 AyuGram tdata…")
                return
        # 没有 AyuGram 同步时直接处理下一个
        QTimer.singleShot(2000, self._process_next_account)

    def _on_sync_ayugram_ok(self, msg):
        self.sync_worker = None
        if "SKIP" in msg:
            self.update_status("ℹ️ 该账号已在 AyuGram 中，跳过")
        else:
            self.update_status("✅ 已追加到 AyuGram tdata")
        QTimer.singleShot(2000, self._process_next_account)

    def _on_sync_ayugram_fail(self, err_msg):
        self.sync_worker = None
        self.update_status(f"⚠️ 写入 AyuGram 失败: {err_msg}")
        QTimer.singleShot(2000, self._process_next_account)

    def _on_login_fail(self, err_msg):
        line = self.lines[self.num_index] if self.num_index < len(self.lines) else err_msg
        self.record_failed_account(line)
        self.login_worker = None
        self.num_index += 1
        self.update_stats()
        self.save_config()
        self.update_status(f"❌ 登录失败: {err_msg}")
        QTimer.singleShot(3000, self._process_next_account)

    def _process_next_account(self):
        """自动处理下一个账号（F3 按一次后连续处理所有）"""
        if self._stop_requested:
            self.update_status("🛑 已停止")
            self.stop_btn.setEnabled(False)
            return
        if self.num_index < len(self.lines):
            self._do_login_current()
        else:
            self.stop_btn.setEnabled(False)
            if self.failed_accounts:
                self.update_status("msg_login_complete_with_fail",
                                  success=self.success_count, fail=self.fail_count)
            else:
                self.update_status("msg_login_all_success")

    def closeEvent(self, event):
        """
        程序关闭时的清理工作
        注意：不删除临时截图文件，因为它们可能在下次启动时被使用
        """
        # 临时文件由系统自动管理，不手动删除
        # 这样可以保证重新打开程序时能够正常加载之前的截图配置
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ExtractorApp()
    win.show()
    sys.exit(app.exec_())
