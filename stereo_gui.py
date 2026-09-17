#!/usr/bin/env python3

import tkinter as tk
import subprocess
import os
import sys

class StereoControl:
    def __init__(self):
        self.process = None
        self.capture_process = None
        self.root = tk.Tk()
        self.root.title("Stereo Depth 控制面板")
        self.root.geometry("300x150")
        self.root.resizable(False, False)

        self.status_label = tk.Label(self.root, text="状态: 未启动", fg="gray", font=("", 12))
        self.status_label.pack(pady=15)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(btn_frame, text="开始", width=10, height=2,
                                   command=self.start_stereo, bg="#4CAF50", fg="white")
        self.start_btn.pack(side=tk.LEFT, padx=10)

        self.stop_btn = tk.Button(btn_frame, text="停止", width=10, height=2,
                                  command=self.stop_stereo, bg="#f44336", fg="white",
                                  state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=10)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_stereo(self):
        if self.process is not None:
            return

        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "stereo_depth_filters.py")
        capture_path = os.path.join(script_dir, "startCapture.py")

        self.process = subprocess.Popen(
            [sys.executable, script_path],
            cwd=script_dir
        )
        self.capture_process = subprocess.Popen(
            [sys.executable, capture_path],
            cwd=script_dir
        )

        self.status_label.config(text="状态: 运行中", fg="green")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

    def stop_stereo(self):
        if self.process is None:
            return

        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
        self.process = None

        if self.capture_process is not None:
            self.capture_process.terminate()
            try:
                self.capture_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.capture_process.kill()
            self.capture_process = None

        self.status_label.config(text="状态: 已停止", fg="gray")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def on_close(self):
        self.stop_stereo()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    StereoControl().run()
