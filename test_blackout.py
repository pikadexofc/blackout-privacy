"""
Automated Verification Suite for Blackout Screen Privacy
========================================================
Verifies:
1. Virtual screen metric detection.
2. Overlay creation and WDA_MONITOR display affinity.
3. BitBlt screen capture verification (pure black 0x000000 during active mode).
4. Deactivation cleanup and restoration.
"""

import unittest
import ctypes
from ctypes import wintypes
import time
from blackout_core import ScreenBlackoutManager

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

def sample_screen_pixel(x: int, y: int) -> int:
    """Captures a 1x1 pixel from the screen DC via GDI BitBlt and returns RGB color."""
    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbm = gdi32.CreateCompatibleBitmap(hdc_screen, 1, 1)
    gdi32.SelectObject(hdc_mem, hbm)

    # BitBlt 1 pixel
    gdi32.BitBlt(hdc_mem, 0, 0, 1, 1, hdc_screen, x, y, 0x00CC0020) # SRCCOPY
    pixel = gdi32.GetPixel(hdc_mem, 0, 0)

    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)
    return pixel


class TestScreenBlackout(unittest.TestCase):
    def setUp(self):
        self.mgr = ScreenBlackoutManager()

    def tearDown(self):
        self.mgr.deactivate()

    def test_virtual_screen_bounds(self):
        x, y, w, h = self.mgr.get_virtual_screen_bounds()
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)
        print(f"Verified Virtual Screen: {w}x{h} at ({x}, {y})")

    def test_blackout_activation_and_capture(self):
        # 1. Activate blackout
        success = self.mgr.activate()
        self.assertTrue(success, "Failed to activate screen blackout")
        self.assertTrue(self.mgr.is_active)
        self.assertIsNotNone(self.mgr._hwnd)

        # Allow DWM compositing flush
        time.sleep(0.1)

        # 2. Sample multiple screen points
        x, y, w, h = self.mgr.get_virtual_screen_bounds()
        test_points = [
            (x + w // 2, y + h // 2),
            (x + 100, y + 100),
            (x + w - 100, y + h - 100),
        ]

        for px, py in test_points:
            color = sample_screen_pixel(px, py)
            # In screen capture with WDA_MONITOR, the captured area MUST be 0x0 (pure black)
            self.assertEqual(color, 0x0, f"Expected captured pixel at ({px}, {py}) to be 0x0 (Black), got {hex(color)}")

        print("Verified all sample points returned pure black (0x0) in capture.")

        # 3. Deactivate and verify clean release
        self.mgr.deactivate()
        self.assertFalse(self.mgr.is_active)
        self.assertIsNone(self.mgr._hwnd)
        print("Verified deactivation and resource cleanup.")


if __name__ == "__main__":
    unittest.main()
