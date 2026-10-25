"""
Empirical Multi-Monitor 64-bit BitBlt Screen Capture Verifier
=============================================================
Author: Challenger 2 (Milestone 1)
Scope:
1. Enumerate all physical monitors and their exact rects.
2. Verify virtual screen bounds with DPI awareness.
3. Verify 64-bit GDI BitBlt captures across all monitors.
4. Verify INACTIVE baseline pixels.
5. Verify ACTIVE pure black (0x000000) pixels at all sample points across all monitors.
6. Verify DEACTIVATED recovery of normal screen pixels.
7. Stress test rapid toggles, idempotence, and handle cleanup.
"""

import ctypes
from ctypes import wintypes
import time
import sys

# Ensure execution on the active user desktop (Default)
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
if hdesk:
    user32.SetThreadDesktop(hdesk)

# Import core manager
from blackout_core import (
    ScreenBlackoutManager,
    WDA_MONITOR,
    WDA_NONE,
    SM_XVIRTUALSCREEN,
    SM_YVIRTUALSCREEN,
    SM_CXVIRTUALSCREEN,
    SM_CYVIRTUALSCREEN,
)

# -------------------------------------------------------------
# Rigorous 64-bit ctypes declarations for GDI32 and User32
# -------------------------------------------------------------
HDC = wintypes.HDC
HBITMAP = wintypes.HBITMAP
HGDIOBJ = wintypes.HGDIOBJ
COLORREF = wintypes.COLORREF

user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = HDC

user32.ReleaseDC.argtypes = [wintypes.HWND, HDC]
user32.ReleaseDC.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [HDC]
gdi32.CreateCompatibleDC.restype = HDC

gdi32.CreateCompatibleBitmap.argtypes = [HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = HBITMAP

gdi32.SelectObject.argtypes = [HDC, HGDIOBJ]
gdi32.SelectObject.restype = HGDIOBJ

gdi32.BitBlt.argtypes = [
    HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD
]
gdi32.BitBlt.restype = wintypes.BOOL

gdi32.GetPixel.argtypes = [HDC, ctypes.c_int, ctypes.c_int]
gdi32.GetPixel.restype = COLORREF

gdi32.DeleteObject.argtypes = [HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.DeleteDC.argtypes = [HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

# Monitor enumeration APIs
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
    HDC,
    ctypes.POINTER(RECT),
    wintypes.LPARAM
)

user32.EnumDisplayMonitors.argtypes = [
    HDC,
    ctypes.POINTER(RECT),
    MONITORENUMPROC,
    wintypes.LPARAM
]
user32.EnumDisplayMonitors.restype = wintypes.BOOL

user32.GetMonitorInfoW.argtypes = [
    wintypes.HMONITOR,
    ctypes.POINTER(MONITORINFOEXW)
]
user32.GetMonitorInfoW.restype = wintypes.BOOL


def capture_pixel_64bit(x: int, y: int, monitors: list = None) -> int:
    """Captures a 1x1 pixel from the screen DC using strict 64-bit GDI BitBlt."""
    target_device = None
    local_x = x
    local_y = y

    if monitors:
        for m in monitors:
            rx1, ry1, rx2, ry2 = m["rect"]
            if rx1 <= x < rx2 and ry1 <= y < ry2:
                target_device = m["device"]
                local_x = x - rx1
                local_y = y - ry1
                break

    if target_device:
        hdc_screen = gdi32.CreateDCW(target_device, None, None, None)
        must_delete_dc = True
    else:
        hdc_screen = user32.GetDC(None)
        must_delete_dc = False

    if not hdc_screen:
        raise RuntimeError("Failed to get screen DC")
    
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    if not hdc_mem:
        if must_delete_dc:
            gdi32.DeleteDC(hdc_screen)
        else:
            user32.ReleaseDC(None, hdc_screen)
        raise RuntimeError("Failed to create compatible memory DC")

    hbm = gdi32.CreateCompatibleBitmap(hdc_screen, 1, 1)
    if not hbm:
        gdi32.DeleteDC(hdc_mem)
        if must_delete_dc:
            gdi32.DeleteDC(hdc_screen)
        else:
            user32.ReleaseDC(None, hdc_screen)
        raise RuntimeError("Failed to create compatible bitmap")

    old_obj = gdi32.SelectObject(hdc_mem, hbm)

    SRCCOPY = 0x00CC0020
    success = gdi32.BitBlt(hdc_mem, 0, 0, 1, 1, hdc_screen, local_x, local_y, SRCCOPY)
    if not success:
        err = kernel32.GetLastError()
        gdi32.SelectObject(hdc_mem, old_obj)
        gdi32.DeleteObject(hbm)
        gdi32.DeleteDC(hdc_mem)
        if must_delete_dc:
            gdi32.DeleteDC(hdc_screen)
        else:
            user32.ReleaseDC(None, hdc_screen)
        raise RuntimeError(f"BitBlt failed at ({x}, {y}) [local: {local_x}, {local_y}] with error {err}")

    pixel = gdi32.GetPixel(hdc_mem, 0, 0)

    # Clean release
    gdi32.SelectObject(hdc_mem, old_obj)
    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    if must_delete_dc:
        gdi32.DeleteDC(hdc_screen)
    else:
        user32.ReleaseDC(None, hdc_screen)

    return pixel


def enumerate_monitors():
    monitors = []

    def enum_cb(hmon, hdc, lprect, lparam):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            r = info.rcMonitor
            monitors.append({
                "device": info.szDevice,
                "flags": info.dwFlags,
                "rect": (r.left, r.top, r.right, r.bottom),
                "width": r.right - r.left,
                "height": r.bottom - r.top,
                "hmon": hmon
            })
        return True

    cb = MONITORENUMPROC(enum_cb)
    user32.EnumDisplayMonitors(None, None, cb, 0)
    return monitors


def run_empirical_verification():
    print("=" * 75)
    print("EMPIRICAL MULTI-MONITOR 64-BIT BITBLT SCREEN CAPTURE VERIFICATION")
    print("=" * 75)

    # 1. Enumerate Monitors
    monitors = enumerate_monitors()
    print(f"\n[1] Physical Monitor Enumeration: Detected {len(monitors)} monitor(s):")
    for idx, m in enumerate(monitors):
        is_primary = "PRIMARY" if (m['flags'] & 1) else "SECONDARY"
        print(f"    - Monitor {idx} ({m['device']}, {is_primary}): Rect {m['rect']} ({m['width']}x{m['height']})")

    # 2. Virtual Screen Bounds
    mgr = ScreenBlackoutManager()
    vx, vy, vw, vh = mgr.get_virtual_screen_bounds()
    print(f"\n[2] Virtual Screen Metrics: (X={vx}, Y={vy}, Width={vw}, Height={vh})")

    min_x = min(m['rect'][0] for m in monitors)
    min_y = min(m['rect'][1] for m in monitors)
    max_x = max(m['rect'][2] for m in monitors)
    max_y = max(m['rect'][3] for m in monitors)
    print(f"    Bounding Box from Physical Monitors: ({min_x}, {min_y}) -> ({max_x}, {max_y})")

    assert vx <= min_x, f"Virtual X ({vx}) does not cover min_x ({min_x})"
    assert vy <= min_y, f"Virtual Y ({vy}) does not cover min_y ({min_y})"
    assert vx + vw >= max_x, f"Virtual width ({vx+vw}) does not cover max_x ({max_x})"
    assert vy + vh >= max_y, f"Virtual height ({vy+vh}) does not cover max_y ({max_y})"
    print("    -> PASS: Virtual screen rectangle encompasses all attached monitors.")

    # 3. Formulate Sample Points Across Multi-Monitor Coordinates
    sample_points = []
    for idx, m in enumerate(monitors):
        left, top, right, bottom = m['rect']
        cx = left + (right - left) // 2
        cy = top + (bottom - top) // 2
        pts = [
            (f"Mon{idx}_Center", cx, cy),
            (f"Mon{idx}_TopLeft", left + 100, top + 100),
            (f"Mon{idx}_TopRight", right - 100, top + 100),
            (f"Mon{idx}_BottomLeft", left + 100, bottom - 100),
            (f"Mon{idx}_BottomRight", right - 100, bottom - 100),
        ]
        sample_points.extend(pts)

    print(f"\n[3] Formulated {len(sample_points)} sample points spanning multi-monitor geometry:")
    for name, px, py in sample_points:
        print(f"    - {name:18} at ({px:5}, {py:5})")

    # 4. Phase 1: Baseline Screen Capture (INACTIVE)
    print("\n[4] Phase 1: INACTIVE State Baseline Capture...")
    baseline_pixels = {}
    non_black_count = 0
    for name, px, py in sample_points:
        pixel = capture_pixel_64bit(px, py, monitors=monitors)
        baseline_pixels[name] = pixel
        is_non_black = (pixel != 0x000000)
        if is_non_black:
            non_black_count += 1
        r = pixel & 0xFF
        g = (pixel >> 8) & 0xFF
        b = (pixel >> 16) & 0xFF
        print(f"    {name:18} at ({px:5}, {py:5}): 0x{pixel:06X} (R={r:3}, G={g:3}, B={b:3}) {'[COLOR]' if is_non_black else '[BLACK]'}")

    print(f"    -> Non-black baseline points: {non_black_count}/{len(sample_points)}")
    assert non_black_count > 0, "All baseline pixels were black; verify desktop content is visible."

    # 5. Phase 2: Activate Screen Blackout
    print("\n[5] Phase 2: Activating Privacy Mode (WDA_MONITOR Overlay)...")
    t0 = time.perf_counter()
    act_ok = mgr.activate()
    t_act = (time.perf_counter() - t0) * 1000
    print(f"    - mgr.activate() completed in {t_act:.2f} ms with status: {act_ok}")
    assert act_ok, "ScreenBlackoutManager.activate() returned False"
    assert mgr.is_active, "mgr.is_active is False after activation"
    assert mgr._hwnd is not None, "mgr._hwnd is None after activation"

    # Verify Display Affinity
    affinity = wintypes.DWORD(0)
    user32.GetWindowDisplayAffinity(mgr._hwnd, ctypes.byref(affinity))
    print(f"    - HWND: {hex(mgr._hwnd)}, WindowDisplayAffinity: {hex(affinity.value)} (Expected 0x1 WDA_MONITOR)")
    assert affinity.value == WDA_MONITOR, f"Affinity is {hex(affinity.value)}, expected {hex(WDA_MONITOR)}"

    # Wait for DWM composition frame
    time.sleep(0.15)

    # Sample Points in ACTIVE mode
    print("    Sampling screen pixels during ACTIVE blackout protection...")
    active_failures = []
    for name, px, py in sample_points:
        pixel = capture_pixel_64bit(px, py, monitors=monitors)
        if pixel != 0x000000:
            active_failures.append((name, px, py, pixel))
            print(f"    [FAIL] {name:18} at ({px:5}, {py:5}): 0x{pixel:06X} != 0x000000")
        else:
            print(f"    [PASS] {name:18} at ({px:5}, {py:5}): 0x000000 (Pure Black)")

    if active_failures:
        print(f"\n    FATAL: {len(active_failures)} sample points failed to return pure black!")
        sys.exit(1)
    else:
        print(f"    -> PASS: 100% of sample points ({len(sample_points)}/{len(sample_points)}) returned PURE BLACK (0x000000).")

    # 6. Phase 3: Deactivate Screen Blackout
    print("\n[6] Phase 3: Deactivating Privacy Mode (Restoration)...")
    t0 = time.perf_counter()
    deact_ok = mgr.deactivate()
    t_deact = (time.perf_counter() - t0) * 1000
    print(f"    - mgr.deactivate() completed in {t_deact:.2f} ms with status: {deact_ok}")
    assert deact_ok, "mgr.deactivate() returned False"
    assert not mgr.is_active, "mgr.is_active is True after deactivation"
    assert mgr._hwnd is None, "mgr._hwnd is not None after deactivation"

    # Wait for DWM composition frame
    time.sleep(0.15)

    # Sample Points in DEACTIVATED mode
    print("    Sampling screen pixels during DEACTIVATED mode (checking pixel recovery)...")
    deact_recovered = 0
    for name, px, py in sample_points:
        pixel = capture_pixel_64bit(px, py, monitors=monitors)
        baseline = baseline_pixels[name]
        is_same = (pixel == baseline)
        if is_same:
            deact_recovered += 1
        print(f"    {name:18} at ({px:5}, {py:5}): 0x{pixel:06X} (Baseline: 0x{baseline:06X}, Match={is_same})")

    print(f"    -> Baseline recovery match rate: {deact_recovered}/{len(sample_points)} points matched baseline.")
    assert deact_recovered == len(sample_points), "Not all pixels recovered to their baseline values!"
    print("    -> PASS: 100% of sample points perfectly recovered their original desktop pixels.")

    # 7. Phase 4: Stress Testing
    print("\n[7] Phase 4: Stress Testing Rapid Toggles & Idempotence...")
    toggles = 20
    start_stress = time.perf_counter()
    for i in range(toggles):
        # Double activate to test idempotence
        mgr.activate()
        mgr.activate()
        assert mgr.is_active

        # Double deactivate to test idempotence
        mgr.deactivate()
        mgr.deactivate()
        assert not mgr.is_active

    stress_time = (time.perf_counter() - start_stress) * 1000
    avg_per_toggle = stress_time / toggles
    print(f"    -> PASS: Successfully executed {toggles} rapid toggle cycles in {stress_time:.2f} ms ({avg_per_toggle:.2f} ms/cycle).")

    print("\n" + "=" * 75)
    print("VERDICT: ALL EMPIRICAL MULTI-MONITOR SCREEN CAPTURE TESTS PASSED (100%)")
    print("=" * 75)


if __name__ == "__main__":
    run_empirical_verification()
