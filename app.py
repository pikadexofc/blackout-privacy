"""
Blackout Privacy - Native Windows Application
=============================================
A sleek, single-button privacy switch for screen sharing.
Turn your entire screen black to Google Meet, Zoom, Teams, Discord,
while you keep working normally.

Includes:
- Large single Toggle Button (OFF -> ON)
- Global Hotkey: Ctrl + Alt + B
- Compact GitHub Feedback submission
- Auto-protection (excluded from screen capture)
"""

import sys
import os
import threading
import subprocess
import webbrowser
import urllib.parse
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk, messagebox

from blackout_core import ScreenBlackoutManager, WDA_EXCLUDEFROMCAPTURE

user32 = ctypes.windll.user32

# Hotkey constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
HOTKEY_ID = 1001

class FeedbackDialog(tk.Toplevel):
    def __init__(self, parent, repo_slug="pikadexofc/blackout-privacy"):
        super().__init__(parent)
        self.repo_slug = repo_slug
        self.title("Feedback & Ideas")
        self.geometry("420x360")
        self.resizable(False, False)
        self.configure(bg="#121316")
        self.attributes("-topmost", True)

        # Center dialog relative to parent
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        self.geometry(f"+{px + (pw-420)//2}+{py + (ph-360)//2}")

        lbl_title = tk.Label(
            self,
            text="Share Your Feedback",
            font=("Segoe UI", 13, "bold"),
            bg="#121316",
            fg="#f2f1ee"
        )
        lbl_title.pack(pady=(16, 4))

        lbl_sub = tk.Label(
            self,
            text="Your feedback goes directly to our GitHub project tracker.",
            font=("Segoe UI", 8),
            bg="#121316",
            fg="#888890"
        )
        lbl_sub.pack(pady=(0, 12))

        lbl_subject = tk.Label(
            self,
            text="Subject / Summary:",
            font=("Segoe UI", 9, "bold"),
            bg="#121316",
            fg="#cbc8be",
            anchor="w"
        )
        lbl_subject.pack(fill="x", padx=20)

        self.entry_subject = tk.Entry(
            self,
            font=("Segoe UI", 10),
            bg="#1c1d22",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#2d3038",
            highlightcolor="#2d81ff"
        )
        self.entry_subject.pack(fill="x", padx=20, pady=(4, 10), ipady=4)

        lbl_details = tk.Label(
            self,
            text="Details & Thoughts:",
            font=("Segoe UI", 9, "bold"),
            bg="#121316",
            fg="#cbc8be",
            anchor="w"
        )
        lbl_details.pack(fill="x", padx=20)

        self.txt_feedback = tk.Text(
            self,
            height=6,
            font=("Segoe UI", 9),
            bg="#1c1d22",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#2d3038",
            highlightcolor="#2d81ff",
            wrap="word"
        )
        self.txt_feedback.pack(fill="x", padx=20, pady=(4, 14))

        btn_frame = tk.Frame(self, bg="#121316")
        btn_frame.pack(fill="x", padx=20, pady=(0, 16))

        self.btn_submit = tk.Button(
            btn_frame,
            text="🚀 Submit to GitHub",
            font=("Segoe UI", 9, "bold"),
            bg="#2d81ff",
            fg="#ffffff",
            activebackground="#1e60cc",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self.submit_feedback
        )
        self.btn_submit.pack(side="right", ipady=6, ipadx=12)

        self.btn_cancel = tk.Button(
            btn_frame,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#23252b",
            fg="#a0a0a8",
            activebackground="#2e313a",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=(0, 10), ipady=6, ipadx=12)

    def submit_feedback(self):
        subject = self.entry_subject.get().strip()
        details = self.txt_feedback.get("1.0", tk.END).strip()

        if not subject or not details:
            messagebox.showwarning("Incomplete", "Please provide both a subject and details.", parent=self)
            return

        self.btn_submit.config(state="disabled", text="Submitting...")

        # Run submission in background thread to keep UI smooth
        def worker():
            success = False
            error_msg = ""
            try:
                # Attempt gh CLI issue creation first
                cmd = [
                    "gh", "issue", "create",
                    "--repo", self.repo_slug,
                    "--title", f"[User Feedback] {subject}",
                    "--body", f"### Feedback Submitted via App\n\n**Summary:** {subject}\n\n**Details:**\n{details}\n\n---\n*Submitted from Blackout Privacy Windows App*"
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if proc.returncode == 0:
                    success = True
                else:
                    error_msg = proc.stderr
            except Exception as e:
                error_msg = str(e)

            if success:
                self.after(0, lambda: self._on_success())
            else:
                self.after(0, lambda: self._fallback_browser(subject, details))

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self):
        messagebox.showinfo("Thank You!", "Your feedback was sent directly to GitHub!", parent=self)
        self.destroy()

    def _fallback_browser(self, subject, details):
        # Fallback to browser URL opening prefilled GitHub Issue
        title_q = urllib.parse.quote(f"[User Feedback] {subject}")
        body_q = urllib.parse.quote(f"### Feedback Submitted via App\n\n{details}\n\n*Platform: Windows 10/11*")
        url = f"https://github.com/{self.repo_slug}/issues/new?title={title_q}&body={body_q}"
        try:
            webbrowser.open(url)
            messagebox.showinfo(
                "Feedback Ready",
                "Opened your browser to complete submission on GitHub Issues.",
                parent=self
            )
        except Exception:
            messagebox.showerror("Error", "Could not submit directly. Please visit the GitHub repo issues page.", parent=self)
        self.destroy()


class BlackoutApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.mgr = ScreenBlackoutManager()
        self.title("Blackout Privacy")
        self.geometry("380x310")
        self.resizable(False, False)
        self.configure(bg="#121316")

        # Keep on top so user can access it easily during meetings
        self.attributes("-topmost", True)

        self._setup_ui()
        self._protect_self_from_capture()
        self._register_global_hotkey()

        # Clean exit on close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _setup_ui(self):
        # Header / Status indicator bar
        header_frame = tk.Frame(self, bg="#121316")
        header_frame.pack(fill="x", padx=20, pady=(16, 8))

        self.status_dot = tk.Canvas(header_frame, width=12, height=12, bg="#121316", highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 8), pady=2)
        self._dot = self.status_dot.create_oval(2, 2, 10, 10, fill="#22c55e", outline="")

        self.lbl_status = tk.Label(
            header_frame,
            text="STREAM VISIBLE (Normal)",
            font=("Segoe UI", 9, "bold"),
            bg="#121316",
            fg="#22c55e"
        )
        self.lbl_status.pack(side="left")

        # Subtext explaining state
        self.lbl_info = tk.Label(
            self,
            text="Click below to turn your screen black for viewers.",
            font=("Segoe UI", 8),
            bg="#121316",
            fg="#8c8d94",
            wraplength=340
        )
        self.lbl_info.pack(padx=20, pady=(0, 14))

        # Main Big Single Button
        self.btn_privacy = tk.Button(
            self,
            text="🔒 TURN SCREEN BLACK\n(Privacy On)",
            font=("Segoe UI", 12, "bold"),
            bg="#1e293b",
            fg="#38bdf8",
            activebackground="#334155",
            activeforeground="#38bdf8",
            relief="flat",
            cursor="hand2",
            padx=16,
            pady=16,
            command=self.toggle_privacy
        )
        self.btn_privacy.pack(fill="x", padx=24, pady=6)

        # Global hotkey prompt
        lbl_hotkey = tk.Label(
            self,
            text="Global Hotkey: Ctrl + Alt + B",
            font=("Consolas", 8),
            bg="#121316",
            fg="#60626a"
        )
        lbl_hotkey.pack(pady=(6, 16))

        # Divider
        divider = tk.Frame(self, height=1, bg="#202228")
        divider.pack(fill="x", padx=24, pady=(0, 12))

        # Bottom row with Feedback button and Exit
        bottom_frame = tk.Frame(self, bg="#121316")
        bottom_frame.pack(fill="x", padx=24, pady=(0, 14))

        self.btn_feedback = tk.Button(
            bottom_frame,
            text="💬 Feedback",
            font=("Segoe UI", 8, "bold"),
            bg="#1c1d22",
            fg="#a1a1aa",
            activebackground="#27272a",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self.open_feedback
        )
        self.btn_feedback.pack(side="left", ipady=4, ipadx=8)

        lbl_version = tk.Label(
            bottom_frame,
            text="v1.0.0 • Blackout Privacy",
            font=("Segoe UI", 8),
            bg="#121316",
            fg="#52525b"
        )
        lbl_version.pack(side="right", pady=4)

    def _protect_self_from_capture(self):
        """Prevents this control window from appearing on screen share if desired."""
        try:
            self.update_idletasks()
            hwnd = user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def _register_global_hotkey(self):
        """Registers global Ctrl + Alt + B hotkey so user can toggle from any window."""
        self.update_idletasks()
        self.hwnd = user32.GetParent(self.winfo_id()) or self.winfo_id()
        # Register Hotkey 'B' = 0x42
        reg = user32.RegisterHotKey(self.hwnd, HOTKEY_ID, MOD_CONTROL | MOD_ALT, 0x42)
        if reg:
            self._start_hotkey_listener()

    def _start_hotkey_listener(self):
        """Background message pump to capture WM_HOTKEY events."""
        def listener():
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
                if msg.message == 0x0312 and msg.wParam == HOTKEY_ID: # WM_HOTKEY
                    self.after(0, self.toggle_privacy)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        t = threading.Thread(target=listener, daemon=True)
        t.start()

    def toggle_privacy(self):
        is_active = self.mgr.toggle()
        if is_active:
            # Active (Blacked Out) UI State
            self.status_dot.itemconfig(self._dot, fill="#ef4444")
            self.lbl_status.config(text="● BLACKOUT ACTIVE (Viewers See Black)", fg="#ef4444")
            self.lbl_info.config(
                text="🛡️ Screen is 100% black to Google Meet/Zoom. You can work privately.",
                fg="#f87171"
            )
            self.btn_privacy.config(
                text="🛡️ SCREEN BLACKED OUT\n(Click to Resume Sharing)",
                bg="#7f1d1d",
                fg="#fecaca",
                activebackground="#991b1b",
                activeforeground="#fef2f2"
            )
        else:
            # Inactive (Normal) UI State
            self.status_dot.itemconfig(self._dot, fill="#22c55e")
            self.lbl_status.config(text="● STREAM VISIBLE (Normal)", fg="#22c55e")
            self.lbl_info.config(
                text="Click below to turn your screen black for viewers.",
                fg="#8c8d94"
            )
            self.btn_privacy.config(
                text="🔒 TURN SCREEN BLACK\n(Privacy On)",
                bg="#1e293b",
                fg="#38bdf8",
                activebackground="#334155",
                activeforeground="#38bdf8"
            )

    def open_feedback(self):
        FeedbackDialog(self)

    def on_closing(self):
        if self.mgr.is_active:
            self.mgr.deactivate()
        try:
            user32.UnregisterHotKey(self.hwnd, HOTKEY_ID)
        except Exception:
            pass
        self.destroy()


def main():
    app = BlackoutApp()
    app.mainloop()

if __name__ == "__main__":
    main()
