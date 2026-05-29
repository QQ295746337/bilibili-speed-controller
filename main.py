import os
import threading
import tkinter as tk
from tkinter import ttk

from bilibili_manager import DEFAULT_DEBUG_PORT, is_bilibili_running, is_debug_port_open
from cdp_controller import CDPController
from asar_patcher import find_bilibili_install, is_asr_injected, has_backup, patch_asar, restore_asar

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
        self._bili_install = find_bilibili_install()

        self._build_ui()
        self._update_button_states()
        self._periodic_check()

    def _center_window(self):
        self.root.update_idletasks()
        w, h = 290, 340
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # -- Status --
        sf = ttk.Frame(self.root, padding=(10, 8, 10, 2))
        sf.pack(fill=tk.X)

        self.status_label = ttk.Label(sf, text="等待连接...", anchor=tk.CENTER, font=("", 10))
        self.status_label.pack(fill=tk.X)
        self.sub_label = ttk.Label(sf, text="", anchor=tk.CENTER, font=("", 8), foreground="gray")
        self.sub_label.pack(fill=tk.X)

        ttk.Separator(self.root).pack(fill=tk.X, padx=10)

        # -- Speed buttons --
        bf = ttk.Frame(self.root, padding=(10, 8))
        bf.pack(fill=tk.BOTH, expand=True)

        self.speed_buttons: dict[float, tk.Button] = {}
        for idx, speed in enumerate(SPEEDS):
            row, col = idx // 3, idx % 3
            is_last = idx == len(SPEEDS) - 1
            text = f"{speed:.1f}x" if speed != int(speed) else f"{int(speed)}x"
            btn = tk.Button(
                bf, text=text, font=("Microsoft YaHei UI", 13, "bold"),
                width=5, relief=tk.RAISED,
                command=lambda s=speed: self._on_speed_click(s),
            )
            if is_last and len(SPEEDS) % 3 == 1:
                btn.grid(row=row, column=0, columnspan=3, sticky="ew", pady=3)
            else:
                btn.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            self.speed_buttons[speed] = btn

        for c in range(3):
            bf.columnconfigure(c, weight=1)

        ttk.Separator(self.root).pack(fill=tk.X, padx=10)

        # -- Actions --
        af = ttk.Frame(self.root, padding=(10, 5, 10, 10))
        af.pack(fill=tk.X)

        self.connect_btn = ttk.Button(af, text="连接B站", command=self._on_connect)
        self.connect_btn.pack(fill=tk.X, pady=2)

        self.refresh_btn = ttk.Button(af, text="刷新检测", command=self._on_refresh)
        self.refresh_btn.pack(fill=tk.X, pady=1)

        # Patch/restore row
        prf = ttk.Frame(af)
        prf.pack(fill=tk.X)
        prf.columnconfigure(0, weight=1)
        prf.columnconfigure(1, weight=1)

        self._patch_label = ttk.Label(
            af, text="", anchor=tk.CENTER, font=("", 8), foreground="gray"
        )
        self._patch_label.pack(fill=tk.X, pady=(4, 0))

        self.patch_btn = ttk.Button(prf, text="一键注入CDP", command=self._on_patch)
        self.patch_btn.grid(row=0, column=0, padx=1, sticky="ew")

        self.restore_btn = ttk.Button(prf, text="恢复原版", command=self._on_restore)
        self.restore_btn.grid(row=0, column=1, padx=1, sticky="ew")

        self._update_patch_status()

    # ------------------------------------------------------------------
    # Patch status
    # ------------------------------------------------------------------

    def _update_patch_status(self):
        if not self._bili_install:
            self._patch_label.config(text="未找到B站安装", foreground="gray")
            self.patch_btn.config(state=tk.DISABLED)
            self.restore_btn.config(state=tk.DISABLED)
        elif is_asr_injected(self._bili_install):
            self._patch_label.config(text="CDP已注入", foreground="green")
            self.patch_btn.config(state=tk.DISABLED)
            self.restore_btn.config(state=tk.NORMAL if has_backup(self._bili_install) else tk.DISABLED)
        else:
            self._patch_label.config(
                text="B站已找到 · 需注入CDP", foreground="orange"
            )
            self.patch_btn.config(state=tk.NORMAL)
            self.restore_btn.config(state=tk.NORMAL if has_backup(self._bili_install) else tk.DISABLED)

    # ------------------------------------------------------------------
    # Button states
    # ------------------------------------------------------------------

    def _update_button_states(self):
        state = tk.NORMAL if self.connected else tk.DISABLED
        for b in self.speed_buttons.values():
            b.config(state=state)
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
                self.root.after(0, lambda: self._set_status(str(e), "red"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_speed_result(self, count: int, speed: float):
        if count > 0:
            self._set_status(f"已连接 · 当前 {speed}x", "green")
        else:
            self._set_status("未找到视频 · 打开视频后点刷新", "orange")

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _on_connect(self):
        if not is_bilibili_running():
            self._set_status("B站未运行 · 请先打开B站客户端", "orange")
            return
        if not is_debug_port_open():
            self._set_status("调试端口未开启 · 请先注入CDP", "orange")
            return
        self._do_connect()

    def _do_connect(self):
        self._set_status("正在连接...", "gray")

        def worker():
            try:
                targets = self.cdp.discover_video_targets()
                self.root.after(0, lambda: self._on_connected(len(targets)))
            except Exception as e:
                self.root.after(0, lambda: self._set_status(f"连接失败: {e}", "red"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_connected(self, video_count: int):
        self.connected = True
        self._update_button_states()
        if video_count == 0:
            self._set_status("已连接 · 无视频（打开视频后点刷新）", "orange")
        else:
            self._set_status(f"已连接 · {video_count}个视频 · 当前 {self.current_speed}x", "green")
            self._on_speed_click(self.current_speed)

    def _on_refresh(self):
        if not is_debug_port_open():
            self.connected = False
            self._update_button_states()
            self._set_status("连接已断开", "red")
            return
        self._do_connect()

    # ------------------------------------------------------------------
    # Patch / Restore
    # ------------------------------------------------------------------

    def _on_patch(self):
        if not self._bili_install:
            self._patch_label.config(text="未找到B站安装", foreground="red")
            return
        if is_bilibili_running():
            self._set_status("请先关闭B站再注入", "orange")
            return

        self.patch_btn.config(state=tk.DISABLED)
        self.restore_btn.config(state=tk.DISABLED)

        def cb(msg):
            self.root.after(0, lambda: self._patch_label.config(text=msg))

        def worker():
            ok = patch_asar(self._bili_install, status_callback=cb)
            self.root.after(0, lambda: self._patch_done(ok))

        threading.Thread(target=worker, daemon=True).start()

    def _patch_done(self, ok: bool):
        self._update_patch_status()
        if ok:
            self._patch_label.config(text="CDP注入成功！请重新打开B站", foreground="green")
            self._set_status("注入成功 · 请重新打开B站后点击连接", "green")
        else:
            self._patch_label.config(text="注入失败 · 请检查npm是否安装", foreground="red")

    def _on_restore(self):
        if not self._bili_install or not has_backup(self._bili_install):
            return
        if is_bilibili_running():
            self._set_status("请先关闭B站再恢复", "orange")
            return

        self.patch_btn.config(state=tk.DISABLED)
        self.restore_btn.config(state=tk.DISABLED)

        def cb(msg):
            self.root.after(0, lambda: self._patch_label.config(text=msg))

        def worker():
            ok = restore_asar(self._bili_install, status_callback=cb)
            self.root.after(0, lambda: self._restore_done(ok))

        threading.Thread(target=worker, daemon=True).start()

    def _restore_done(self, ok: bool):
        self._update_patch_status()
        if ok:
            self._patch_label.config(text="已恢复原版", foreground="green")
        else:
            self._patch_label.config(text="恢复失败", foreground="red")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, text: str, color: str):
        self.status_label.config(text=text, foreground=color)

    def _periodic_check(self):
        running = is_bilibili_running()
        port_open = is_debug_port_open()

        if running and port_open:
            self.sub_label.config(text="B站运行中 · 调试端口已开启", foreground="green")
        elif running:
            self.sub_label.config(text="B站运行中 · 调试端口未开启", foreground="orange")
        else:
            self.sub_label.config(text="B站未运行", foreground="gray")

        if self.connected and not port_open:
            self.connected = False
            self._update_button_states()
            self._set_status("连接已断开", "red")

        self._update_patch_status()
        self.root.after(3000, self._periodic_check)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = BilibiliSpeedApp()
    app.run()
