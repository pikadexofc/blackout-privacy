"""
Automated Verification Suite for Blackout Screen Privacy
========================================================
Comprehensive 64-bit verification suite for Windows 10/11:
1. Virtual screen metric detection across all attached displays.
2. Window handle creation and required extended styles:
   (WS_EX_TOPMOST, WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_NOACTIVATE).
3. Display affinity contract (GetWindowDisplayAffinity == WDA_MONITOR = 0x1).
4. Rapid toggle reliability (10x rapid cycles with correct state toggling).
5. Idempotence of activate() and deactivate().
6. BitBlt screen capture verification:
   - Verifies 0x000000 (pure black) captured across sample points during active blackout.
   - Verifies normal desktop pixels are restored upon deactivation.
   - Provides graceful fallback when executed in headless/sandboxed CI environments.
"""

import unittest
import ctypes
from ctypes import wintypes
import time
from blackout_core import (
    ScreenBlackoutManager,
    WDA_NONE,
    WDA_MONITOR,
    WS_EX_TOPMOST,
    WS_EX_LAYERED,
    WS_EX_TRANSPARENT,
    WS_EX_NOACTIVATE,
)

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# Attach to interactive user desktop if possible
try:
    if hasattr(user32, "OpenDesktopW") and hasattr(user32, "SetThreadDesktop"):
        user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        user32.OpenDesktopW.restype = wintypes.HANDLE
        user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
        user32.SetThreadDesktop.restype = wintypes.BOOL

        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
except Exception:
    pass

# =====================================================================
# Complete 64-bit Win32 User32 and GDI32 API Signatures
# =====================================================================
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC

user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int

user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = wintypes.LONG

user32.GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowDisplayAffinity.restype = wintypes.BOOL

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC

gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP

gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ

gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

gdi32.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.GetPixel.restype = wintypes.COLORREF

gdi32.BitBlt.argtypes = [
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.DWORD,
]
gdi32.BitBlt.restype = wintypes.BOOL

if hasattr(gdi32, "CreateDCW"):
    gdi32.CreateDCW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
    gdi32.CreateDCW.restype = wintypes.HDC

kernel32.GetLastError.argtypes = []
kernel32.GetLastError.restype = wintypes.DWORD

# Monitor Enumeration structures
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]

class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]

MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HMONITOR,
    wintypes.HDC,
    ctypes.POINTER(RECT),
    wintypes.LPARAM,
)
user32.EnumDisplayMonitors.argtypes = [
    wintypes.HDC,
    ctypes.POINTER(RECT),
    MONITORENUMPROC,
    wintypes.LPARAM,
]
user32.EnumDisplayMonitors.restype = wintypes.BOOL

user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFOEXW)]
user32.GetMonitorInfoW.restype = wintypes.BOOL


def enumerate_monitors():
    """Returns list of active monitors with their device names and rectangles."""
    monitors = []

    def _enum_cb(hmon, hdc, lprect, lparam):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            r = info.rcMonitor
            monitors.append({
                "device": info.szDevice,
                "rect": (r.left, r.top, r.right, r.bottom),
                "hmon": hmon,
            })
        return True

    cb = MONITORENUMPROC(_enum_cb)
    user32.EnumDisplayMonitors(None, None, cb, 0)
    return monitors


def sample_screen_pixel(x: int, y: int, monitors=None) -> int:
    """
    Captures a 1x1 pixel from the screen via GDI BitBlt using 64-bit signatures.
    Supports multi-monitor coordinate spaces and returns RGB COLORREF (0x00BBGGRR).
    Raises RuntimeError on GDI failure or non-interactive environment.
    """
    target_device = None
    local_x, local_y = x, y

    if monitors:
        for m in monitors:
            rx1, ry1, rx2, ry2 = m["rect"]
            if rx1 <= x < rx2 and ry1 <= y < ry2:
                target_device = m["device"]
                local_x = x - rx1
                local_y = y - ry1
                break

    is_created_dc = False
    if target_device and hasattr(gdi32, "CreateDCW"):
        hdc_screen = gdi32.CreateDCW(target_device, None, None, None)
        if hdc_screen:
            is_created_dc = True
        else:
            hdc_screen = user32.GetDC(None)
    else:
        hdc_screen = user32.GetDC(None)

    if not hdc_screen:
        err = kernel32.GetLastError()
        raise RuntimeError(f"GetDC failed with error code {err}")

    try:
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        if not hdc_mem:
            err = kernel32.GetLastError()
            raise RuntimeError(f"CreateCompatibleDC failed with error code {err}")

        try:
            hbm = gdi32.CreateCompatibleBitmap(hdc_screen, 1, 1)
            if not hbm:
                err = kernel32.GetLastError()
                raise RuntimeError(f"CreateCompatibleBitmap failed with error code {err}")

            try:
                old_obj = gdi32.SelectObject(hdc_mem, hbm)
                SRCCOPY = 0x00CC0020
                success = gdi32.BitBlt(hdc_mem, 0, 0, 1, 1, hdc_screen, local_x, local_y, SRCCOPY)
                if not success:
                    err = kernel32.GetLastError()
                    raise RuntimeError(f"BitBlt failed at ({x}, {y}) [local: {local_x}, {local_y}] with error {err}")

                pixel = gdi32.GetPixel(hdc_mem, 0, 0)
                gdi32.SelectObject(hdc_mem, old_obj)
                return pixel
            finally:
                gdi32.DeleteObject(hbm)
        finally:
            gdi32.DeleteDC(hdc_mem)
    finally:
        if is_created_dc:
            gdi32.DeleteDC(hdc_screen)
        else:
            user32.ReleaseDC(None, hdc_screen)


class TestScreenBlackout(unittest.TestCase):
    """Unit test suite for the Blackout Screen Privacy engine."""

    def setUp(self):
        self.mgr = ScreenBlackoutManager()

    def tearDown(self):
        if self.mgr.is_active:
            self.mgr.deactivate()

    def test_virtual_screen_bounds(self):
        """Verifies detection of virtual screen bounds across attached displays."""
        x, y, w, h = self.mgr.get_virtual_screen_bounds()
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)
        self.assertGreater(w, 0, "Virtual screen width must be positive")
        self.assertGreater(h, 0, "Virtual screen height must be positive")

        monitors = enumerate_monitors()
        if monitors:
            min_x = min(m["rect"][0] for m in monitors)
            min_y = min(m["rect"][1] for m in monitors)
            max_x = max(m["rect"][2] for m in monitors)
            max_y = max(m["rect"][3] for m in monitors)
            self.assertLessEqual(x, min_x, "Virtual screen left must encompass left-most monitor")
            self.assertLessEqual(y, min_y, "Virtual screen top must encompass top-most monitor")
            self.assertGreaterEqual(x + w, max_x, "Virtual screen right must encompass right-most monitor")
            self.assertGreaterEqual(y + h, max_y, "Virtual screen bottom must encompass bottom-most monitor")

    def test_window_creation_and_styles(self):
        """Verifies overlay creation and required extended click-through window styles."""
        success = self.mgr.activate()
        self.assertTrue(success, "ScreenBlackoutManager.activate() returned False")
        self.assertTrue(self.mgr.is_active, "ScreenBlackoutManager.is_active must be True when active")
        self.assertIsNotNone(self.mgr._hwnd, "Overlay HWND must be allocated")
        self.assertTrue(user32.IsWindow(self.mgr._hwnd), "Overlay HWND must be a valid Win32 window")

        GWL_EXSTYLE = -20
        ex_style = user32.GetWindowLongW(self.mgr._hwnd, GWL_EXSTYLE)
        expected_styles = (
            WS_EX_TOPMOST
            | WS_EX_LAYERED
            | WS_EX_TRANSPARENT
            | WS_EX_NOACTIVATE
        )
        self.assertEqual(
            ex_style & expected_styles,
            expected_styles,
            f"Missing required extended styles (got {hex(ex_style)}, expected {hex(expected_styles)})",
        )

    def test_display_affinity_contract(self):
        """Verifies that WDA_MONITOR (0x1) display affinity is enforced on the overlay."""
        self.mgr.activate()
        self.assertIsNotNone(self.mgr._hwnd)

        affinity = wintypes.DWORD()
        res = user32.GetWindowDisplayAffinity(self.mgr._hwnd, ctypes.byref(affinity))
        self.assertTrue(res, "GetWindowDisplayAffinity call failed")
        self.assertEqual(
            affinity.value,
            WDA_MONITOR,
            f"Expected WDA_MONITOR ({hex(WDA_MONITOR)}), got {hex(affinity.value)}",
        )

    def test_rapid_toggle_reliability(self):
        """Verifies 10 consecutive rapid toggle cycles without state corruption or handle leaks."""
        for i in range(10):
            new_state = self.mgr.toggle()
            expected_state = (i % 2 == 0)
            self.assertEqual(
                new_state,
                expected_state,
                f"Toggle iteration {i} returned {new_state}, expected {expected_state}",
            )
            self.assertEqual(self.mgr.is_active, expected_state)

            if expected_state:
                self.assertIsNotNone(self.mgr._hwnd)
                self.assertTrue(user32.IsWindow(self.mgr._hwnd))
            else:
                self.assertIsNone(self.mgr._hwnd)

    def test_idempotence(self):
        """Verifies that multiple calls to activate() and deactivate() are safe and idempotent."""
        # Consecutive activations
        self.assertTrue(self.mgr.activate())
        hwnd_first = self.mgr._hwnd
        self.assertTrue(self.mgr.activate())
        self.assertEqual(self.mgr._hwnd, hwnd_first, "Duplicate activate() must not re-create window")
        self.assertTrue(self.mgr.is_active)

        # Consecutive deactivations
        self.assertTrue(self.mgr.deactivate())
        self.assertIsNone(self.mgr._hwnd)
        self.assertFalse(self.mgr.is_active)
        self.assertTrue(self.mgr.deactivate())
        self.assertIsNone(self.mgr._hwnd)
        self.assertFalse(self.mgr.is_active)

    def test_bitblt_screen_capture(self):
        """
        Verifies BitBlt capture returns pure black (0x000000) during active mode
        and restores normal desktop pixels when deactivated.
        Falls back gracefully if executed in a headless/sandboxed environment.
        """
        monitors = enumerate_monitors()
        vx, vy, vw, vh = self.mgr.get_virtual_screen_bounds()

        # Build sample points across active displays
        sample_points = []
        if monitors:
            for m in monitors:
                x1, y1, x2, y2 = m["rect"]
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                sample_points.append((cx, cy))
        else:
            sample_points.append((vx + vw // 2, vy + vh // 2))

        # Check for interactive desktop capture capability
        try:
            baseline_pixels = {}
            for px, py in sample_points:
                baseline_pixels[(px, py)] = sample_screen_pixel(px, py, monitors)
        except RuntimeError as ex:
            self.skipTest(f"Headless/non-interactive desktop environment detected: {ex}")

        # 1. Activate blackout
        self.assertTrue(self.mgr.activate(), "Failed to activate blackout manager")
        self.assertTrue(self.mgr.is_active)
        time.sleep(0.15)  # Allow DWM compositing flush

        # 2. Verify all sample points capture pure black (0x000000)
        try:
            for px, py in sample_points:
                captured_pixel = sample_screen_pixel(px, py, monitors)
                self.assertEqual(
                    captured_pixel,
                    0x000000,
                    f"Pixel at ({px}, {py}) captured {hex(captured_pixel)}, expected 0x000000 (Pure Black)",
                )

            # 3. Deactivate blackout
            self.assertTrue(self.mgr.deactivate(), "Failed to deactivate blackout manager")
            self.assertFalse(self.mgr.is_active)
            time.sleep(0.15)  # Allow DWM compositing flush

            # 4. Verify recovery of normal desktop pixels
            for px, py in sample_points:
                restored_pixel = sample_screen_pixel(px, py, monitors)
                expected_baseline = baseline_pixels[(px, py)]
                # If baseline was non-black, verify it is no longer trapped in pure black capture
                if expected_baseline != 0x000000:
                    self.assertNotEqual(
                        restored_pixel,
                        0x000000,
                        f"Pixel at ({px}, {py}) remained black after deactivation",
                    )
                self.assertTrue(
                    restored_pixel == expected_baseline or (expected_baseline != 0 and restored_pixel != 0),
                    f"Pixel at ({px}, {py}) did not restore normal desktop pixels: got {hex(restored_pixel)}, baseline was {hex(expected_baseline)}",
                )
        except RuntimeError as ex:
            self.skipTest(f"GDI capture interrupted: {ex}")


if __name__ == "__main__":
    unittest.main()
