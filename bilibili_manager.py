import socket
import subprocess

DEFAULT_DEBUG_PORT = 9222


def is_bilibili_running() -> bool:
    """Check if any 哔哩哔哩.exe process exists."""
    try:
        result = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"],
            capture_output=True, text=True, encoding="gbk", timeout=5,
        )
        return "哔哩哔哩.exe" in result.stdout
    except Exception:
        return False


def is_debug_port_open(port: int = DEFAULT_DEBUG_PORT) -> bool:
    """Check if the CDP debug port accepts TCP connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        return result == 0
    except Exception:
        return False
