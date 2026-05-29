import threading
import tkinter as tk
from tkinter import messagebox, ttk

from bilibili_manager import DEFAULT_DEBUG_PORT, is_bilibili_running, is_debug_port_open
from cdp_controller import CDPController

SPEEDS = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]


class BilibiliSpeedApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("B站倍速控制")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#F5F5F5")

        self._center_window()

        self.cdp = CDPController(port=DEFAULT_DEBUG_PORT)
        self.connected = False
        self.current_speed = 1.0

        self._build_ui()
        self._update_button_states()
        self._periodic_check()

    def _center_window(self):
        self.root.update_idletasks()
        w = 280
        h = 260
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # -- Status frame --
        status_frame = ttk.Frame(self.root, padding=(10, 10, 10, 5))
        status_frame.pack(fill=tk.X)

        self.status_label = ttk.Label(
            status_frame, text="等待连接...", anchor=tk.CENTER, font=("", 10)
        )
        self.status_label.pack(fill=tk.X)

        self.bili_status_label = ttk.Label(
            status_frame, text="", anchor=tk.CENTER, font=("", 8), foreground="gray"
        )
        self.bili_status_label.pack(fill=tk.X)

        ttk.Separator(self.root).pack(fill=tk.X, padx=10)

        # -- Speed buttons --
        btn_frame = ttk.Frame(self.root, padding=(10, 10))
        btn_frame.pack(fill=tk.BOTH, expand=True)

        self.speed_buttons: dict[float, tk.Button] = {}
        for idx, speed in enumerate(SPEEDS):
            row = idx // 3
            col = idx % 3
            is_last = idx == len(SPEEDS) - 1
            text = f"{speed:.1f}x" if speed != int(speed) else f"{int(speed)}x"
            btn = tk.Button(
                btn_frame,
                text=text,
                font=("Microsoft YaHei UI", 13, "bold"),
                width=5,
                relief=tk.RAISED,
                command=lambda s=speed: self._on_speed_click(s),
            )
            if is_last and len(SPEEDS) % 3 == 1:
                btn.grid(row=row, column=0, columnspan=3, sticky="ew", pady=3)
            else:
                btn.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            self.speed_buttons[speed] = btn

        for c in range(3):
            btn_frame.columnconfigure(c, weight=1)

        ttk.Separator(self.root).pack(fill=tk.X, padx=10)

        # -- Action buttons --
        action_frame = ttk.Frame(self.root, padding=(10, 5, 10, 10))
        action_frame.pack(fill=tk.X)

        self.connect_btn = ttk.Button(
            action_frame, text="连接B站", command=self._on_connect
        )
        self.connect_btn.pack(fill=tk.X, pady=2)

        self.refresh_btn = ttk.Button(
            action_frame, text="刷新检测", command=self._on_refresh
        )
        self.refresh_btn.pack(fill=tk.X)

    # ------------------------------------------------------------------
    # Button states
    # ------------------------------------------------------------------

    def _update_button_states(self):
        state = tk.NORMAL if self.connected else tk.DISABLED
        for btn in self.speed_buttons.values():
            btn.config(state=state)
        self._highlight_active_speed()

    def _highlight_active_speed(self):
        for speed, btn in self.speed_buttons.items():
            if speed == self.current_speed and self.connected:
                btn.config(bg="#3399FF", fg="white", activebackground="#2979CC")
            elif speed <= 2.0:
                btn.config(bg="#E0E0E0", fg="black", activebackground="#CCCCCC")
            else:
                btn.config(bg="#FFE0B2", fg="black", activebackground="#FFCC80")

    # ------------------------------------------------------------------
    # Speed control
    # ------------------------------------------------------------------

    def _on_speed_click(self, speed: float):
        if not self.connected:
            return
        self.current_speed = speed
        self._highlight_active_speed()

        def worker():
            try:
                count = self.cdp.set_speed(speed)
                self.root.after(0, lambda: self._on_speed_result(count, speed))
            except Exception as e:
                self.root.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_speed_result(self, count: int, speed: float):
        if count > 0:
            self.status_label.config(
                text=f"已连接 · 当前 {speed}x", foreground="green"
            )
        else:
            self.status_label.config(
                text="未找到视频 · 打开视频后点刷新", foreground="orange"
            )

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _on_connect(self):
        if not is_debug_port_open():
            if not is_bilibili_running():
                messagebox.showwarning(
                    "未检测到B站",
                    "B站似乎没有运行。\n请先手动打开B站客户端。\n\n"
                    "如果已打开，请检查是否使用本工具修改过的版本。",
                )
            else:
                messagebox.showwarning(
                    "调试端口未开启",
                    "检测到B站正在运行但调试端口未开启。\n"
                    "请确认 app.asar 已被修改。",
                )
            return
        self._do_connect()

    def _do_connect(self):
        self.status_label.config(text="正在连接...", foreground="gray")

        def worker():
            try:
                targets = self.cdp.discover_video_targets()
                self.root.after(0, lambda: self._on_connected(len(targets)))
            except Exception as e:
                self.root.after(0, lambda: self._on_error(f"连接失败: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_connected(self, video_count: int):
        self.connected = True
        self._update_button_states()
        if video_count == 0:
            self.status_label.config(
                text="已连接 · 无视频（打开视频后点刷新）", foreground="orange"
            )
        else:
            self.status_label.config(
                text=f"已连接 · {video_count}个视频 · 当前 {self.current_speed}x",
                foreground="green",
            )
            self._on_speed_click(self.current_speed)

    def _on_refresh(self):
        """Re-discover targets."""
        if not is_debug_port_open():
            self.connected = False
            self._update_button_states()
            self.status_label.config(text="连接已断开", foreground="red")
            return
        self._do_connect()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _on_error(self, msg: str):
        self.status_label.config(text=msg[:60], foreground="red")

    def _periodic_check(self):
        running = is_bilibili_running()
        port_open = is_debug_port_open()

        if running and port_open:
            self.bili_status_label.config(text="B站运行中 · 调试端口已开启", foreground="green")
            if not self.connected:
                self.connect_btn.config(state=tk.NORMAL)
        elif running:
            self.bili_status_label.config(text="B站运行中 · 调试端口未开启", foreground="orange")
            self.connect_btn.config(state=tk.NORMAL)
        else:
            self.bili_status_label.config(text="B站未运行", foreground="gray")
            self.connect_btn.config(state=tk.NORMAL)

        if self.connected and not port_open:
            self.connected = False
            self._update_button_states()
            self.status_label.config(text="连接已断开", foreground="red")

        self.root.after(3000, self._periodic_check)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = BilibiliSpeedApp()
    app.run()
