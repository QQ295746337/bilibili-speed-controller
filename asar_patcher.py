import os
import shutil
import subprocess
import sys
import tempfile

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

BILIBILI_SEARCH_PATHS = [
    r"E:\B站\bilibili",
    r"C:\Program Files\bilibili",
    r"C:\Program Files (x86)\bilibili",
    r"D:\B站\bilibili",
]

ASAR_PATH = "resources/app.asar"
INJECTION_CODE = (
    "(function(){try{require('electron').app.commandLine.appendSwitch"
    "('remote-debugging-port','9222')}catch(e){}})();"
)


def find_bilibili_install() -> str | None:
    """Find Bilibili installation directory. Returns path or None."""
    paths_to_check = list(BILIBILI_SEARCH_PATHS)

    # Check from running process
    try:
        r = subprocess.run(
            ["wmic", "process", "where", 'name="哔哩哔哩.exe"', "get", "executablepath"],
            capture_output=True, text=True, timeout=5,
            creationflags=_NO_WINDOW,
        )
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.lower().endswith("哔哩哔哩.exe"):
                d = os.path.dirname(line)
                if d not in paths_to_check:
                    paths_to_check.insert(0, d)
                break
    except Exception:
        pass

    # Check registry
    try:
        for key in [
            r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\bilibili",
            r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\bilibili",
        ]:
            r = subprocess.run(
                ["reg", "query", key, "/v", "InstallLocation"],
                capture_output=True, text=True, timeout=5,
                creationflags=_NO_WINDOW,
            )
            for line in r.stdout.splitlines():
                if "InstallLocation" in line:
                    parts = line.split("REG_SZ")
                    if len(parts) > 1:
                        d = parts[-1].strip()
                        if d and d not in paths_to_check:
                            paths_to_check.insert(0, d)
    except Exception:
        pass

    for p in paths_to_check:
        asar = os.path.join(p, ASAR_PATH)
        if os.path.isfile(asar):
            return p
    return None


def is_asr_injected(install_dir: str) -> bool:
    """Check if the asar has already been patched."""
    asar_path = os.path.join(install_dir, ASAR_PATH)
    if not os.path.isfile(asar_path):
        return False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(
                ["npx", "--yes", "@electron/asar", "extract", asar_path, tmp],
                capture_output=True, text=True, timeout=30,
                creationflags=_NO_WINDOW,
            )
            if r.returncode != 0:
                return False
            index_js = os.path.join(tmp, "index.js")
            if os.path.isfile(index_js):
                with open(index_js, "r", encoding="utf-8", errors="ignore") as f:
                    return "remote-debugging-port" in f.read(500)
    except Exception:
        pass
    return False


def has_backup(install_dir: str) -> bool:
    """Check if a backup of the original asar exists."""
    bak = os.path.join(install_dir, "resources", "app.asar.bak")
    return os.path.isfile(bak)


def patch_asar(install_dir: str, status_callback=None) -> bool:
    """Inject CDP-enabling code into app.asar. Returns True on success."""
    asar_path = os.path.join(install_dir, ASAR_PATH)
    bak_path = os.path.join(install_dir, "resources", "app.asar.bak")

    if not os.path.isfile(asar_path):
        if status_callback:
            status_callback(f"未找到 app.asar: {asar_path}")
        return False

    try:
        work_dir = tempfile.mkdtemp(prefix="bili_patch_")

        if status_callback:
            status_callback("正在备份原版 app.asar...")
        shutil.copy2(asar_path, bak_path)

        if status_callback:
            status_callback("正在解包 app.asar...")
        r = subprocess.run(
            ["npx", "--yes", "@electron/asar", "extract", asar_path, work_dir],
            capture_output=True, text=True, timeout=60,
            creationflags=_NO_WINDOW,
        )
        if r.returncode != 0:
            if status_callback:
                status_callback(f"解包失败: {r.stderr[:200]}")
            shutil.rmtree(work_dir, ignore_errors=True)
            return False

        index_js = os.path.join(work_dir, "index.js")
        if not os.path.isfile(index_js):
            if status_callback:
                status_callback("解包后未找到 index.js")
            shutil.rmtree(work_dir, ignore_errors=True)
            return False

        with open(index_js, "r", encoding="utf-8", errors="ignore") as f:
            original = f.read()

        if "remote-debugging-port" in original[:500]:
            if status_callback:
                status_callback("已经注入过，跳过")
            shutil.rmtree(work_dir, ignore_errors=True)
            return True

        with open(index_js, "w", encoding="utf-8") as f:
            f.write(INJECTION_CODE + original)

        if status_callback:
            status_callback("正在重新打包 app.asar...")
        r = subprocess.run(
            ["npx", "--yes", "@electron/asar", "pack", work_dir, asar_path],
            capture_output=True, text=True, timeout=60,
            creationflags=_NO_WINDOW,
        )
        shutil.rmtree(work_dir, ignore_errors=True)

        if r.returncode != 0:
            if status_callback:
                status_callback(f"打包失败: {r.stderr[:200]}")
            return False

        if status_callback:
            status_callback("注入成功！")
        return True

    except Exception as e:
        if status_callback:
            status_callback(f"错误: {e}")
        return False


def restore_asar(install_dir: str, status_callback=None) -> bool:
    """Restore original app.asar from backup. Returns True on success."""
    bak_path = os.path.join(install_dir, "resources", "app.asar.bak")
    asar_path = os.path.join(install_dir, ASAR_PATH)

    if not os.path.isfile(bak_path):
        if status_callback:
            status_callback("未找到备份文件")
        return False

    try:
        shutil.copy2(bak_path, asar_path)
        if status_callback:
            status_callback("已恢复原版")
        return True
    except Exception as e:
        if status_callback:
            status_callback(f"恢复失败: {e}")
        return False
