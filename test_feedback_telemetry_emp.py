"""
Empirical Verification Suite for Milestone 2:
FeedbackDialog Modal Behavior, Singleton Deduplication, Telemetry Accuracy & Fallback URL Verification.

Authored by: Challenger 2 (teamwork_preview_challenger_m2_2)
"""

import unittest
import tkinter as tk
from tkinter import messagebox
import platform
import sys
import os
import urllib.parse
import threading
import time
import ctypes
from ctypes import wintypes
from unittest.mock import patch, MagicMock

# Import targets from app and blackout_core
from app import BlackoutApp, FeedbackDialog, __version__, user32, GA_ROOT
from blackout_core import ScreenBlackoutManager, WDA_EXCLUDEFROMCAPTURE

# Win32 API for inspecting window affinity and state
user32.GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowDisplayAffinity.restype = wintypes.BOOL

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL


class TestFeedbackDialogEmpirical(unittest.TestCase):
    def setUp(self):
        # Initialize app with Tkinter update
        self.app = BlackoutApp()
        self.app.update()

    def tearDown(self):
        try:
            if hasattr(self, 'app') and self.app:
                # Close any open dialogs first
                if getattr(self.app, '_feedback_dialog', None) is not None:
                    try:
                        self.app._feedback_dialog.destroy()
                    except Exception:
                        pass
                self.app.on_closing()
        except Exception:
            pass

    # ==========================================
    # 1. MODAL BEHAVIOR & GRAB VERIFICATION
    # ==========================================
    def test_modal_grab_active(self):
        """Verify grab is active on dialog and main window is modal-blocked."""
        self.app.open_feedback()
        self.app.update()

        dialog = self.app._feedback_dialog
        self.assertIsNotNone(dialog, "Feedback dialog should be instantiated")
        self.assertTrue(dialog.winfo_exists(), "Feedback dialog window must exist")

        # 1. Grab check
        grab_status = dialog.grab_status()
        self.assertIn(grab_status, ("local", "global"), f"Expected dialog to hold grab, got {grab_status}")
        
        # Verify app recognizes dialog as current grab widget
        current_grab = self.app.grab_current()
        self.assertEqual(current_grab, dialog, f"Expected current grab to be dialog, got {current_grab}")

        # 2. Transient check
        transient_master = dialog.transient()
        # In Tkinter, transient() returns master widget or its path
        self.assertTrue(
            str(transient_master) == str(self.app) or transient_master == self.app,
            f"Expected transient parent to be app, got {transient_master}"
        )

        # 3. Topmost attribute check
        is_topmost = dialog.attributes("-topmost")
        self.assertTrue(bool(is_topmost), "Feedback dialog must have -topmost enabled")

        # 4. Grab release on destruction
        dialog.destroy()
        self.app.update()
        self.assertIsNone(self.app.grab_current(), "Grab must be released when dialog is destroyed")
        self.assertIsNone(self.app._feedback_dialog, "Parent reference _feedback_dialog must be None after destroy")

    # ==========================================
    # 2. SINGLETON DEDUPLICATION & FOCUS BEHAVIOR
    # ==========================================
    def test_singleton_deduplication_and_focus(self):
        """Verify calling open_feedback multiple times preserves single dialog and focuses it."""
        self.app.open_feedback()
        self.app.update()

        dialog_1 = self.app._feedback_dialog
        self.assertIsNotNone(dialog_1)

        # Record count of toplevel children
        initial_toplevels = [w for w in self.app.children.values() if isinstance(w, tk.Toplevel)]
        self.assertEqual(len(initial_toplevels), 1, "Should have exactly 1 toplevel initially")

        # Call open_feedback 5 times rapidly
        for i in range(5):
            self.app.open_feedback()
            self.app.update()

        current_toplevels = [w for w in self.app.children.values() if isinstance(w, tk.Toplevel)]
        self.assertEqual(len(current_toplevels), 1, f"Expected 1 toplevel, found {len(current_toplevels)}")
        self.assertIs(self.app._feedback_dialog, dialog_1, "Dialog instance must be identical (singleton)")

        # Test withdrawn/hidden window restoration
        dialog_1.withdraw()
        self.app.update()
        self.assertEqual(dialog_1.state(), "withdrawn", "Dialog should be withdrawn for test")

        # Calling open_feedback should deiconify and bring to front
        self.app.open_feedback()
        self.app.update()
        self.assertNotEqual(dialog_1.state(), "withdrawn", "Dialog must be deiconified by open_feedback")

        # Close dialog and open again: must create a new valid instance cleanly
        dialog_1.destroy()
        self.app.update()
        self.assertIsNone(self.app._feedback_dialog)

        self.app.open_feedback()
        self.app.update()
        dialog_2 = self.app._feedback_dialog
        self.assertIsNotNone(dialog_2)
        self.assertTrue(dialog_2.winfo_exists())
        self.assertIsNot(dialog_1, dialog_2, "A new dialog instance should be created after destruction")

    # ==========================================
    # 3. TELEMETRY ACCURACY & DYNAMIC STATE
    # ==========================================
    def test_telemetry_accuracy_and_state_reflection(self):
        """Verify telemetry payload contains real, non-dummy system info and tracks privacy state."""
        # --- Case A: Privacy INACTIVE ---
        self.assertFalse(self.app.mgr.is_active, "Manager should start Inactive")
        self.app.open_feedback()
        self.app.update()

        dialog = self.app._feedback_dialog
        telemetry_inactive = dialog._collect_telemetry()
        print("\n[Collected Telemetry - Inactive]:\n", telemetry_inactive)

        # 1. Non-dummy checks
        self.assertNotIn("Unavailable", telemetry_inactive, "Telemetry fields should not be 'Unavailable' on valid system")
        self.assertNotIn("Unknown", telemetry_inactive, "Telemetry fields should not be 'Unknown'")
        self.assertNotIn("dummy", telemetry_inactive.lower(), "Telemetry contains dummy placeholder")

        # 2. Field content assertions
        expected_os = platform.platform()
        self.assertIn(expected_os, telemetry_inactive, f"OS Platform must match real platform: {expected_os}")

        expected_py = f"{platform.python_version()} ({platform.architecture()[0]})"
        self.assertIn(expected_py, telemetry_inactive, f"Python version must match real python: {expected_py}")

        pw = self.app.winfo_screenwidth()
        ph = self.app.winfo_screenheight()
        self.assertIn(f"{pw}x{ph}", telemetry_inactive, f"Primary screen must match winfo dimensions: {pw}x{ph}")

        vx, vy, vw, vh = self.app.mgr.get_virtual_screen_bounds()
        self.assertIn(f"({vx}, {vy}) {vw}x{vh}", telemetry_inactive, "Virtual screen bounds must match mgr bounds")

        self.assertIn("- **Blackout State:** Inactive", telemetry_inactive)
        self.assertIn(f"- **App Version:** v{__version__}", telemetry_inactive)

        dialog.destroy()
        self.app.update()

        # --- Case B: Privacy ACTIVE ---
        self.app.mgr.activate()
        self.app.update()
        self.assertTrue(self.app.mgr.is_active)

        self.app.open_feedback()
        self.app.update()
        dialog_active = self.app._feedback_dialog
        telemetry_active = dialog_active._collect_telemetry()
        print("\n[Collected Telemetry - Active]:\n", telemetry_active)

        self.assertIn("- **Blackout State:** Active", telemetry_active)
        self.assertIn(f"({vx}, {vy}) {vw}x{vh}", telemetry_active)

        dialog_active.destroy()
        self.app.mgr.deactivate()
        self.app.update()

    # ==========================================
    # 4. FALLBACK URL ESCAPING & SYNTAX INTEGRITY
    # ==========================================
    def test_fallback_url_escaping_adversarial(self):
        """Stress-test fallback URL construction with adversarial, unicode, and control characters."""
        self.app.open_feedback()
        self.app.update()
        dialog = self.app._feedback_dialog

        telemetry = dialog._collect_telemetry()

        # Test cases with complex adversarial payloads
        test_cases = [
            (
                "Standard Bug",
                "Simple one-line bug description."
            ),
            (
                "Special & Query Chars: ? = & # % + / \\ ' \"",
                "Line 1: param=val&foo=bar\nLine 2: 100% working? #anchor + addition\nBackslash: C:\\Users\\Name\nQuotes: 'single' and \"double\""
            ),
            (
                "Markdown & Syntax Injections: <div> **bold** `code`",
                "### Heading 3\n- Item 1\n- Item 2\n```python\nprint('hello world & test')\n```\n<script>alert('xss')</script>"
            ),
            (
                "Unicode & Emojis: 🛡️ 🚀 🔒 日本語 Тест",
                "Testing full UTF-8 emojis: 🚀 💬 🛡️ ⚠️\nAccents: à é î ö ù\nCyrillic: Привет мир\nEast Asian: こんにちは 世界"
            ),
            (
                "Extreme Length Test: " + ("A" * 200),
                "Long text: " + ("Details with lots of words. " * 100)
            )
        ]

        for subject, details in test_cases:
            captured_url = None

            def mock_open(url):
                nonlocal captured_url
                captured_url = url
                return True

            with patch("webbrowser.open", side_effect=mock_open), \
                 patch("tkinter.messagebox.showinfo") as mock_info:
                
                # Execute fallback logic
                dialog._fallback_browser(subject, details, telemetry)
                self.app.update()

            self.assertIsNotNone(captured_url, f"webbrowser.open should be called for subject: {subject[:30]}")

            # 1. URL syntax verification
            parsed = urllib.parse.urlparse(captured_url)
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "github.com")
            self.assertEqual(parsed.path, f"/{dialog.repo_slug}/issues/new")

            # 2. Query string parsing
            query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            self.assertIn("title", query_params)
            self.assertIn("body", query_params)

            title_val = query_params["title"][0]
            body_val = query_params["body"][0]

            # 3. Round-trip decoded text integrity
            expected_title = f"[User Feedback] {subject}"
            self.assertEqual(title_val, expected_title, f"Title mismatch for: {subject}")

            self.assertIn(details, body_val, "Decoded body must contain user details verbatim")
            self.assertIn("### Feedback Submitted via App", body_val)
            self.assertIn("### Diagnostic Telemetry", body_val)
            self.assertIn(platform.platform(), body_val, "Decoded body must contain telemetry platform")

            # Ensure dialog was destroyed by fallback
            self.assertFalse(dialog.winfo_exists())

            # Reopen for next test iteration
            if subject != test_cases[-1][0]:
                self.app.open_feedback()
                self.app.update()
                dialog = self.app._feedback_dialog

    # ==========================================
    # 5. DISPLAY AFFINITY ON FEEDBACK DIALOG
    # ==========================================
    def test_feedback_dialog_display_affinity(self):
        """Verify FeedbackDialog applies WDA_EXCLUDEFROMCAPTURE to exclude itself from screen capture."""
        self.app.open_feedback()
        self.app.update()
        dialog = self.app._feedback_dialog

        dialog.update_idletasks()
        hwnd = user32.GetAncestor(dialog.winfo_id(), GA_ROOT) or dialog.winfo_id()
        self.assertTrue(bool(user32.IsWindow(hwnd)), "Dialog HWND must be a valid Win32 window")

        affinity = wintypes.DWORD(0)
        ret = user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(affinity))
        self.assertTrue(ret, "GetWindowDisplayAffinity Win32 call must succeed")
        print(f"\n[FeedbackDialog HWND={hex(hwnd)} Display Affinity]: {hex(affinity.value)}")

        # WDA_EXCLUDEFROMCAPTURE is 0x00000011 (or WDA_MONITOR 0x1)
        self.assertIn(
            affinity.value,
            (WDA_EXCLUDEFROMCAPTURE, 0x11, 0x1),
            f"Expected WDA_EXCLUDEFROMCAPTURE (0x11) or WDA_MONITOR (0x1), got {hex(affinity.value)}"
        )

        dialog.destroy()
        self.app.update()

    # ==========================================
    # 6. FORM VALIDATION & SUBMISSION BEHAVIOR
    # ==========================================
    def test_form_validation_rejects_empty(self):
        """Verify empty or whitespace-only inputs trigger warning without submitting."""
        self.app.open_feedback()
        self.app.update()
        dialog = self.app._feedback_dialog

        invalid_inputs = [
            ("", ""),
            ("   ", "   "),
            ("Valid Subject", ""),
            ("", "Valid Details"),
            ("   ", "Valid Details"),
            ("Valid Subject", "   \n\t  ")
        ]

        for subj, det in invalid_inputs:
            dialog.entry_subject.delete(0, tk.END)
            dialog.entry_subject.insert(0, subj)
            dialog.txt_feedback.delete("1.0", tk.END)
            dialog.txt_feedback.insert("1.0", det)

            with patch("tkinter.messagebox.showwarning") as mock_warn, \
                 patch("threading.Thread") as mock_thread:
                dialog.submit_feedback()
                mock_warn.assert_called_once()
                mock_thread.assert_not_called()
                self.assertEqual(dialog.btn_submit["text"], "🚀 Submit to GitHub")

        dialog.destroy()
        self.app.update()

    # ==========================================
    # 7. SUCCESSFUL SUBMISSION PIPELINE
    # ==========================================
    def test_successful_submission_pipeline(self):
        """Verify successful gh command triggers _on_success and cleans up dialog."""
        self.app.open_feedback()
        dialog = self.app._feedback_dialog

        dialog.entry_subject.insert(0, "Feature Idea: Tray Icon")
        dialog.txt_feedback.insert("1.0", "Would love a system tray icon option.")

        success_called = threading.Event()

        def mock_proc(*args, **kwargs):
            proc = MagicMock()
            proc.returncode = 0
            proc.stdout = "https://github.com/pikadexofc/blackout-privacy/issues/42\n"
            return proc

        # Patch _on_success to signal completion and exit mainloop
        orig_on_success = dialog._on_success
        def wrapped_on_success():
            with patch("tkinter.messagebox.showinfo"):
                orig_on_success()
                success_called.set()
                self.app.quit()

        dialog._on_success = wrapped_on_success

        with patch("subprocess.run", side_effect=mock_proc):
            dialog.submit_feedback()
            timer_id = self.app.after(2000, self.app.quit)
            self.app.mainloop()
            try:
                self.app.after_cancel(timer_id)
            except Exception:
                pass

        self.assertTrue(success_called.is_set(), "_on_success should be called after gh returncode 0")
        self.assertFalse(dialog.winfo_exists(), "Dialog must be destroyed after successful submission")
        self.assertIsNone(self.app._feedback_dialog, "Parent reference must be reset to None")

    # ==========================================
    # 8. DIRECT WIN32 SYSTEM METRIC TELEMETRY CORRELATION
    # ==========================================
    def test_telemetry_win32_system_metrics_correlation(self):
        """Cross-verify telemetry numbers against direct raw Win32 User32 GetSystemMetrics."""
        SM_CXSCREEN = 0
        SM_CYSCREEN = 1
        SM_XVIRTUALSCREEN = 76
        SM_YVIRTUALSCREEN = 77
        SM_CXVIRTUALSCREEN = 78
        SM_CYVIRTUALSCREEN = 79

        raw_cx = user32.GetSystemMetrics(SM_CXSCREEN)
        raw_cy = user32.GetSystemMetrics(SM_CYSCREEN)
        raw_vx = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        raw_vy = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        raw_vw = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        raw_vh = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

        self.app.open_feedback()
        self.app.update()
        dialog = self.app._feedback_dialog
        telemetry = dialog._collect_telemetry()

        print(f"\n[Raw Win32 Metrics]: Primary={raw_cx}x{raw_cy}, Virtual=({raw_vx}, {raw_vy}) {raw_vw}x{raw_vh}")

        # Check virtual bounds correlation
        expected_v_str = f"({raw_vx}, {raw_vy}) {raw_vw}x{raw_vh}"
        self.assertIn(expected_v_str, telemetry, f"Telemetry virtual screen must match Win32 metrics: {expected_v_str}")

        # Check primary screen
        expected_p_str = f"{raw_cx}x{raw_cy}"
        self.assertIn(expected_p_str, telemetry, f"Telemetry primary screen must match Win32 metrics: {expected_p_str}")

        dialog.destroy()
        self.app.update()

    # ==========================================
    # 9. CONCURRENCY & RESILIENCE TEST
    # ==========================================
    def test_destruction_during_background_worker(self):
        """Verify closing the dialog while background worker runs does not crash the application."""
        self.app.open_feedback()
        dialog = self.app._feedback_dialog

        dialog.entry_subject.insert(0, "Test Background Race")
        dialog.txt_feedback.insert("1.0", "Details test")

        # Simulate a slow gh process
        worker_started = threading.Event()
        worker_can_finish = threading.Event()

        def slow_proc(*args, **kwargs):
            worker_started.set()
            worker_can_finish.wait(timeout=2.0)
            proc = MagicMock()
            proc.returncode = 1
            return proc

        def do_destroy():
            dialog.destroy()
            worker_can_finish.set()
            self.app.after(300, self.app.quit)

        with patch("subprocess.run", side_effect=slow_proc), \
             patch("webbrowser.open") as mock_browser, \
             patch("tkinter.messagebox.showinfo"), \
             patch("tkinter.messagebox.showerror"):
            
            # Start submission
            dialog.submit_feedback()
            
            # Wait for worker thread to start, then schedule destroy in mainloop
            self.app.after(50, do_destroy)
            timer_id = self.app.after(2000, self.app.quit)
            self.app.mainloop()
            try:
                self.app.after_cancel(timer_id)
            except Exception:
                pass

        self.assertIsNone(self.app._feedback_dialog)
        # The app should remain fully alive and healthy
        self.assertTrue(self.app.winfo_exists(), "Main application window must remain intact")


if __name__ == "__main__":
    unittest.main(verbosity=2)
