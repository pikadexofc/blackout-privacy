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
import platform
import queue
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk, messagebox

from blackout_core import ScreenBlackoutManager, WDA_EXCLUDEFROMCAPTURE

__version__ = "1.0.0"

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
HOTKEY_ID = 1001
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
PM_NOREMOVE = 0x0000
GA_ROOT = 2

# User32 & Kernel32 64-bit API signatures
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL

user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL

user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL

user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
user32.PeekMessageW.restype = wintypes.BOOL

user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = ctypes.c_int64

user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL

user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND

user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND

user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.SetWindowDisplayAffinity.restype = wintypes.BOOL

kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

kernel32.GetLastError.argtypes = []
kernel32.GetLastError.restype = wintypes.DWORD


def init_dpi_awareness():
    """Initializes Windows Per-Monitor v2 DPI awareness for crisp rendering on high-DPI displays."""
    try:
        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
            user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        else:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass


# Initialize DPI awareness early at module import
init_dpi_awareness()

class FeedbackDialog(tk.Toplevel):
    def __init__(self, parent, repo_slug="pikadexofc/blackout-privacy"):
        super().__init__(parent)
        self.parent = parent
        self.repo_slug = repo_slug
        self.title("Feedback & Ideas")
        self.geometry("420x360")
        self.resizable(False, False)
        self.configure(bg="#121316")
        self.attributes("-topmost", True)

        # Make dialog modal and transient to parent
        self.transient(parent)

        # Center dialog relative to parent
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        self.geometry(f"+{px + (pw-420)//2}+{py + (ph-360)//2}")

        self._setup_ui()
        self._protect_self_from_capture()

        # Modal grab directs all input to this dialog
        self.grab_set()

        # Handle close protocols
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _setup_ui(self):
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
            fg="#94a3b8"
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
            fg="#cbd5e1",
            activebackground="#2e313a",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=(0, 10), ipady=6, ipadx=12)

    def _protect_self_from_capture(self):
        """Prevents the feedback dialog from appearing on screen share."""
        try:
            self.update_idletasks()
            hwnd = (
                user32.GetAncestor(self.winfo_id(), GA_ROOT)
                or user32.GetParent(self.winfo_id())
                or self.winfo_id()
            )
            user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def _collect_telemetry(self):
        """Auto-collects diagnostic system information for feedback reports."""
        try:
            os_plat = platform.platform()
        except Exception:
            os_plat = sys.platform

        try:
            py_ver = f"{platform.python_version()} ({platform.architecture()[0]})"
        except Exception:
            py_ver = sys.version.split()[0]

        try:
            pw = self.parent.winfo_screenwidth()
            ph = self.parent.winfo_screenheight()
            primary_res = f"{pw}x{ph}"
        except Exception:
            primary_res = "Unavailable"

        try:
            vx, vy, vw, vh = self.parent.mgr.get_virtual_screen_bounds()
            v_bounds_str = f"({vx}, {vy}) {vw}x{vh}"
        except Exception:
            v_bounds_str = "Unavailable"

        try:
            is_active = "Active" if self.parent.mgr.is_active else "Inactive"
        except Exception:
            is_active = "Unknown"

        return (
            "### Diagnostic Telemetry\n"
            f"- **OS Platform:** {os_plat}\n"
            f"- **Python Version:** {py_ver}\n"
            f"- **Primary Screen:** {primary_res}\n"
            f"- **Virtual Screen Bounds:** {v_bounds_str}\n"
            f"- **Blackout State:** {is_active}\n"
            f"- **App Version:** v{__version__}"
        )

    def submit_feedback(self):
        subject = self.entry_subject.get().strip()
        details = self.txt_feedback.get("1.0", tk.END).strip()

        if not subject or not details:
            messagebox.showwarning("Incomplete", "Please provide both a subject and details.", parent=self)
            return

        self.btn_submit.config(state="disabled", text="Submitting...")

        telemetry = self._collect_telemetry()
        body = (
            f"### Feedback Submitted via App\n\n"
            f"**Summary:** {subject}\n\n"
            f"**Details:**\n{details}\n\n"
            f"---\n\n"
            f"{telemetry}\n\n"
            f"---\n*Submitted from Blackout Privacy Windows App*"
        )

        def worker():
            success = False
            try:
                cmd = [
                    "gh", "issue", "create",
                    "--repo", self.repo_slug,
                    "--title", f"[User Feedback] {subject}",
                    "--body", body
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if proc.returncode == 0:
                    success = True
            except Exception:
                success = False

            if success:
                self.after(0, self._on_success)
            else:
                self.after(0, lambda: self._fallback_browser(subject, details, telemetry))

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self):
        messagebox.showinfo("Thank You!", "Your feedback was sent directly to GitHub!", parent=self)
        self.destroy()

    def _fallback_browser(self, subject, details, telemetry):
        title_q = urllib.parse.quote(f"[User Feedback] {subject}")
        body_text = (
            f"### Feedback Submitted via App\n\n"
            f"{details}\n\n"
            f"---\n\n"
            f"{telemetry}\n\n"
            f"---\n*Submitted from Blackout Privacy Windows App*"
        )
        body_q = urllib.parse.quote(body_text)
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

    def destroy(self):
        try:
            self.grab_release()
        except Exception:
            pass
        if hasattr(self.parent, "_feedback_dialog"):
            self.parent._feedback_dialog = None
        super().destroy()


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

        self._feedback_dialog = None
        self._hotkey_thread_id = None
        self._hotkey_thread = None
        self._hotkey_started = threading.Event()
        self._hotkey_queue = queue.Queue()
        self._is_closing = False

        self._setup_ui()
        self._protect_self_from_capture()
        self._start_hotkey_listener()
        self._poll_hotkey_queue()

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
            command=lambda: self.toggle_privacy()
        )
        self.btn_privacy.pack(fill="x", padx=24, pady=6)

        # Global hotkey prompt (WCAG 2.1 AA text contrast: #94a3b8 on #121316 is 7.2:1)
        self.lbl_hotkey = tk.Label(
            self,
            text="Global Hotkey: Ctrl + Alt + B",
            font=("Consolas", 8),
            bg="#121316",
            fg="#94a3b8"
        )
        self.lbl_hotkey.pack(pady=(6, 16))

        # Divider
        divider = tk.Frame(self, height=1, bg="#202228")
        divider.pack(fill="x", padx=24, pady=(0, 12))

        # Bottom row with Feedback button and Version label
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

        # Version label (WCAG 2.1 AA text contrast: #71717a on #121316)
        self.lbl_version = tk.Label(
            bottom_frame,
            text=f"v{__version__} • Blackout Privacy",
            font=("Segoe UI", 8),
            bg="#121316",
            fg="#71717a"
        )
        self.lbl_version.pack(side="right", pady=4)

    def _protect_self_from_capture(self):
        """Prevents this control window from appearing on screen share."""
        try:
            self.update_idletasks()
            hwnd = (
                user32.GetAncestor(self.winfo_id(), GA_ROOT)
                or user32.GetParent(self.winfo_id())
                or self.winfo_id()
            )
            user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def _start_hotkey_listener(self):
        """Dedicated background message pump capturing thread-level WM_HOTKEY."""
        self._hotkey_started.clear()

        def listener():
            self._hotkey_thread_id = kernel32.GetCurrentThreadId()
            # Force message queue creation for this background thread
            msg = wintypes.MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_NOREMOVE)

            reg = user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_ALT, 0x42)
            self._hotkey_started.set()
            if not reg:
                return

            try:
                while True:
                    ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                    if ret <= 0:
                        break
                    if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                        self._hotkey_queue.put(True)
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            finally:
                user32.UnregisterHotKey(None, HOTKEY_ID)

        self._hotkey_thread = threading.Thread(target=listener, daemon=True)
        self._hotkey_thread.start()
        self._hotkey_started.wait(timeout=1.0)

    def _drain_hotkey_queue(self):
        while not self._hotkey_queue.empty():
            try:
                self._hotkey_queue.get_nowait()
                self.toggle_privacy()
            except queue.Empty:
                break

    def _poll_hotkey_queue(self):
        if self._is_closing:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._drain_hotkey_queue()
        if not self._is_closing:
            try:
                self._poll_timer_id = self.after(10, self._poll_hotkey_queue)
            except Exception:
                pass

    def update(self):
        self._drain_hotkey_queue()
        super().update()

    def toggle_privacy(self):
        is_active = self.mgr.toggle()
        if is_active:
            # Active (Blacked Out) UI State
            self.status_dot.itemconfig(self._dot, fill="#ef4444")
            self.lbl_status.config(text="BLACKOUT ACTIVE (Viewers See Black)", fg="#ef4444")
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
            self.lbl_status.config(text="STREAM VISIBLE (Normal)", fg="#22c55e")
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
        """Opens the feedback dialog or focuses an existing open instance."""
        if self._feedback_dialog is not None:
            try:
                if self._feedback_dialog.winfo_exists():
                    self._feedback_dialog.deiconify()
                    self._feedback_dialog.lift()
                    self._feedback_dialog.focus_force()
                    return
            except Exception:
                pass
        self._feedback_dialog = FeedbackDialog(self)

    def on_closing(self):
        """Clean shutdown hook releasing privacy overlay and hotkey thread."""
        if self._is_closing:
            return
        self._is_closing = True

        if hasattr(self, "_poll_timer_id") and self._poll_timer_id:
            try:
                self.after_cancel(self._poll_timer_id)
            except Exception:
                pass

        if self.mgr.is_active:
            self.mgr.deactivate()
        if self._hotkey_thread_id:
            try:
                user32.PostThreadMessageW(self._hotkey_thread_id, WM_QUIT, 0, 0)
                if self._hotkey_thread and self._hotkey_thread.is_alive():
                    self._hotkey_thread.join(timeout=0.3)
            except Exception:
                pass
        try:
            user32.UnregisterHotKey(None, HOTKEY_ID)
        except Exception:
            pass
        try:
            if self.winfo_exists():
                self.destroy()
        except Exception:
            pass


def main():
    init_dpi_awareness()
    app = BlackoutApp()
    app.mainloop()


if __name__ == "__main__":
    main()
