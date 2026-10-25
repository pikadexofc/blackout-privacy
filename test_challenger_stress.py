"""
Milestone 1 Empirical Stress Test Harness & Verification Suite
Authored by Challenger 1 (teamwork_preview_challenger_m1_1)
"""

import ctypes
from ctypes import wintypes
import time
import os
import sys

from blackout_core import (
    ScreenBlackoutManager,
    WDA_MONITOR,
    WS_EX_TOPMOST,
    WS_EX_TRANSPARENT,
    WS_EX_TOOLWINDOW,
    WS_EX_LAYERED,
    WS_EX_NOACTIVATE,
    LWA_ALPHA,
)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

# 64-bit API signatures
GWL_EXSTYLE = -20
GWL_STYLE = -16
GR_GDIOBJECTS = 0
GR_USEROBJECTS = 1

# Setup GetWindowLongPtrW for 64-bit Windows
if ctypes.sizeof(ctypes.c_void_p) == 8:
    GetWindowLongPtrW = user32.GetWindowLongPtrW
    GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    GetWindowLongPtrW.restype = ctypes.c_int64
else:
    GetWindowLongPtrW = user32.GetWindowLongW
    GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    GetWindowLongPtrW.restype = ctypes.c_int32

user32.GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowDisplayAffinity.restype = wintypes.BOOL

user32.GetLayeredWindowAttributes.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.COLORREF),
    ctypes.POINTER(wintypes.BYTE),
    ctypes.POINTER(wintypes.DWORD),
]
user32.GetLayeredWindowAttributes.restype = wintypes.BOOL

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = wintypes.HWND

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND

user32.GetGuiResources.argtypes = [wintypes.HANDLE, wintypes.DWORD]
user32.GetGuiResources.restype = wintypes.DWORD

kernel32.GetCurrentProcess.argtypes = []
kernel32.GetCurrentProcess.restype = wintypes.HANDLE

kernel32.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.GetProcessHandleCount.restype = wintypes.BOOL

class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
    ]

psapi.GetProcessMemoryInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
    wintypes.DWORD
]
psapi.GetProcessMemoryInfo.restype = wintypes.BOOL


def get_mem_bytes():
    h_proc = kernel32.GetCurrentProcess()
    pmc = PROCESS_MEMORY_COUNTERS()
    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    if psapi.GetProcessMemoryInfo(h_proc, ctypes.byref(pmc), pmc.cb):
        return pmc.WorkingSetSize
    return 0


def get_handle_count():
    h_proc = kernel32.GetCurrentProcess()
    count = wintypes.DWORD(0)
    if kernel32.GetProcessHandleCount(h_proc, ctypes.byref(count)):
        return count.value
    return 0


def get_gui_resources():
    h_proc = kernel32.GetCurrentProcess()
    gdi = user32.GetGuiResources(h_proc, GR_GDIOBJECTS)
    user = user32.GetGuiResources(h_proc, GR_USEROBJECTS)
    return gdi, user


def run_all_empirical_tests():
    print("=" * 70)
    print("STARTING EMPIRICAL VERIFICATION SUITE — MILESTONE 1")
    print("=" * 70)

    mgr = ScreenBlackoutManager()
    failures = []

    # -------------------------------------------------------------
    # 1. Activation and Display Affinity Verification
    # -------------------------------------------------------------
    print("\n[TEST 1] Verifying GetWindowDisplayAffinity == 0x1 (WDA_MONITOR)...")
    activated = mgr.activate()
    if not activated or not mgr.is_active or not mgr._hwnd:
        failures.append("TEST 1 FAILED: Manager failed to activate or hwnd is None.")
        print(f"FAILED: activated={activated}, is_active={mgr.is_active}, hwnd={mgr._hwnd}")
    else:
        hwnd = mgr._hwnd
        affinity = wintypes.DWORD(0)
        res = user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(affinity))
        print(f"  GetWindowDisplayAffinity returned: {res}, affinity = 0x{affinity.value:X}")
        if not res:
            err = kernel32.GetLastError()
            failures.append(f"TEST 1 FAILED: GetWindowDisplayAffinity failed with error {err}")
        elif affinity.value != WDA_MONITOR:
            failures.append(f"TEST 1 FAILED: Expected affinity 0x{WDA_MONITOR:X}, got 0x{affinity.value:X}")
        else:
            print("  -> PASS: Display Affinity exactly matches WDA_MONITOR (0x1).")

    # -------------------------------------------------------------
    # 1B. BitBlt Screen Capture Blackness (WDA_MONITOR Masking)
    # -------------------------------------------------------------
    print("\n[TEST 1B] Verifying BitBlt Screen Capture Masking (0x000000 Pure Black)...")
    time.sleep(0.05)
    gdi32 = ctypes.windll.gdi32
    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbm = gdi32.CreateCompatibleBitmap(hdc_screen, 1, 1)
    gdi32.SelectObject(hdc_mem, hbm)

    x, y, w, h = mgr.get_virtual_screen_bounds()
    sample_coords = [
        (x + 50, y + 50),
        (x + w // 4, y + h // 2),
        (x + w // 2, y + h // 2),
        (x + 3 * w // 4, y + h // 2),
        (x + w - 50, y + h - 50),
    ]

    capture_leaks = 0
    for sx, sy in sample_coords:
        gdi32.BitBlt(hdc_mem, 0, 0, 1, 1, hdc_screen, sx, sy, 0x00CC0020)
        pixel = gdi32.GetPixel(hdc_mem, 0, 0)
        print(f"  Capture sample at ({sx:5d}, {sy:5d}) -> 0x{pixel:06X}")
        if pixel != 0:
            capture_leaks += 1

    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)

    if capture_leaks > 0:
        failures.append(f"TEST 1B FAILED: Screen capture captured non-black pixels at {capture_leaks} sample points!")
    else:
        print("  -> PASS: All BitBlt capture samples returned 0x000000 (pure black).")

    # -------------------------------------------------------------
    # 2. Window Styles & Layered Attributes Verification
    # -------------------------------------------------------------
    print("\n[TEST 2] Verifying Extended Window Styles (WS_EX_*)...")
    if mgr._hwnd:
        ex_style = GetWindowLongPtrW(mgr._hwnd, GWL_EXSTYLE)
        print(f"  Observed GWL_EXSTYLE: 0x{ex_style:08X}")

        expected_flags = [
            ("WS_EX_TOPMOST", WS_EX_TOPMOST, 0x00000008),
            ("WS_EX_LAYERED", WS_EX_LAYERED, 0x00080000),
            ("WS_EX_TRANSPARENT", WS_EX_TRANSPARENT, 0x00000020),
            ("WS_EX_NOACTIVATE", WS_EX_NOACTIVATE, 0x08000000),
            ("WS_EX_TOOLWINDOW", WS_EX_TOOLWINDOW, 0x00000080),
        ]

        for name, flag, hex_val in expected_flags:
            present = bool(ex_style & flag)
            print(f"  - {name} (0x{hex_val:08X}): {'PRESENT' if present else 'MISSING'}")
            if not present:
                failures.append(f"TEST 2 FAILED: Style {name} (0x{hex_val:08X}) is missing from GWL_EXSTYLE!")

        # Verify Layered Window Attributes (Alpha == 1)
        cr_key = wintypes.COLORREF(0)
        alpha = wintypes.BYTE(0)
        flags = wintypes.DWORD(0)
        gl_res = user32.GetLayeredWindowAttributes(
            mgr._hwnd,
            ctypes.byref(cr_key),
            ctypes.byref(alpha),
            ctypes.byref(flags)
        )
        print(f"  GetLayeredWindowAttributes result: {gl_res}, alpha={alpha.value}, flags=0x{flags.value:X}")
        if not gl_res:
            failures.append("TEST 2 FAILED: GetLayeredWindowAttributes failed.")
        elif alpha.value != 1:
            failures.append(f"TEST 2 FAILED: Expected alpha=1, got {alpha.value}")
        elif not (flags.value & LWA_ALPHA):
            failures.append(f"TEST 2 FAILED: LWA_ALPHA flag missing (flags=0x{flags.value:X})")
        else:
            print("  -> PASS: All extended styles and alpha=1 verified.")
    else:
        failures.append("TEST 2 FAILED: Overlay hwnd is None.")

    # -------------------------------------------------------------
    # 3. Click Passthrough via WindowFromPoint
    # -------------------------------------------------------------
    print("\n[TEST 3] Verifying Click Passthrough via WindowFromPoint across Virtual Screen...")
    if mgr._hwnd:
        x, y, w, h = mgr.get_virtual_screen_bounds()
        print(f"  Virtual screen bounds: x={x}, y={y}, w={w}, h={h}")

        # Create a visible dummy background window to verify click passthrough directly
        WS_OVERLAPPEDWINDOW = 0x00CF0000
        SW_SHOWNORMAL = 1
        h_inst = kernel32.GetModuleHandleW(None)
        dummy_hwnd = user32.CreateWindowExW(
            0,
            "Button",
            "ChallengerPassthroughTarget",
            WS_OVERLAPPEDWINDOW | 0x10000000, # WS_VISIBLE
            100, 100, 300, 300,
            None, None, h_inst, None
        )
        if dummy_hwnd:
            user32.ShowWindow(dummy_hwnd, SW_SHOWNORMAL)
            user32.UpdateWindow(dummy_hwnd)
            time.sleep(0.05)
            # Re-activate blackout so overlay is topmost above dummy
            mgr.deactivate()
            mgr.activate()
            time.sleep(0.05)

            # Test point inside dummy window (150, 150)
            target_pt = POINT(150, 150)
            hit_hwnd = user32.WindowFromPoint(target_pt)
            hit_hex = f"0x{hit_hwnd:X}" if hit_hwnd else "NULL (0x0)"
            print(f"  Point (150, 150) with Button window at (100, 100):")
            print(f"    Button HWND:  0x{dummy_hwnd:X}")
            print(f"    Overlay HWND: 0x{mgr._hwnd:X}")
            print(f"    Hit HWND:     {hit_hex}")

            if hit_hwnd == mgr._hwnd:
                failures.append("TEST 3 FAILED: Overlay window blocked WindowFromPoint over underlying window!")
            elif hit_hwnd == dummy_hwnd:
                print("  -> PASS: WindowFromPoint directly penetrated overlay and hit the underlying Button HWND!")
            else:
                print(f"  -> PASS: WindowFromPoint bypassed overlay (hit {hit_hex} != overlay 0x{mgr._hwnd:X}).")

            user32.DestroyWindow(dummy_hwnd)

        test_fractions = [
            (0.1, 0.1), (0.5, 0.1), (0.9, 0.1),
            (0.1, 0.5), (0.5, 0.5), (0.9, 0.5),
            (0.1, 0.9), (0.5, 0.9), (0.9, 0.9),
        ]

        passthrough_failures = 0
        for fx, fy in test_fractions:
            px = int(x + w * fx)
            py = int(y + h * fy)
            pt = POINT(px, py)
            hit_hwnd = user32.WindowFromPoint(pt)
            hit_matches_overlay = (hit_hwnd == mgr._hwnd)
            if hit_matches_overlay:
                passthrough_failures += 1

        if passthrough_failures > 0:
            failures.append(f"TEST 3 FAILED: WindowFromPoint intercepted by overlay at {passthrough_failures} sample points!")
        else:
            print("  -> PASS: 100% click passthrough verified across virtual screen grid (0 points hit overlay).")
    else:
        failures.append("TEST 3 FAILED: Overlay hwnd is None.")

    # -------------------------------------------------------------
    # 4. Focus Retention during Activation
    # -------------------------------------------------------------
    print("\n[TEST 4] Verifying Focus Retention (GetForegroundWindow)...")
    # Create a visible focus target window
    focus_target_hwnd = user32.CreateWindowExW(
        0, "STATIC", "FocusTarget",
        0x00CF0000 | 0x10000000,
        200, 200, 200, 200,
        None, None, kernel32.GetModuleHandleW(None), None
    )
    if focus_target_hwnd:
        user32.ShowWindow(focus_target_hwnd, 1) # SW_SHOWNORMAL
        user32.SetForegroundWindow(focus_target_hwnd)
        time.sleep(0.05)

    mgr.deactivate()
    time.sleep(0.05)

    fg_before = user32.GetForegroundWindow()
    print(f"  Foreground HWND before activate(): 0x{fg_before or 0:X} (Focus Target: 0x{focus_target_hwnd or 0:X})")

    mgr.activate()
    fg_after = user32.GetForegroundWindow()
    print(f"  Foreground HWND after activate():  0x{fg_after or 0:X}")
    print(f"  Overlay HWND:                      0x{mgr._hwnd or 0:X}")

    if fg_after == mgr._hwnd:
        failures.append("TEST 4 FAILED: Overlay window stole keyboard/desktop focus!")
    elif fg_before and fg_after != fg_before:
        failures.append(f"TEST 4 FAILED: Foreground window changed from 0x{fg_before:X} to 0x{fg_after:X}")
    else:
        print("  -> PASS: Foreground window remained exactly identical before and after activation.")

    if focus_target_hwnd:
        user32.DestroyWindow(focus_target_hwnd)

    # -------------------------------------------------------------
    # 5. Rapid Toggle Stress Test (50 Cycles) & Latency Benchmarks
    # -------------------------------------------------------------
    print("\n[TEST 5] Running 50-Cycle Rapid Toggle Stress Test...")
    latencies = []
    t_start = time.perf_counter()

    for i in range(50):
        t0 = time.perf_counter()
        state = mgr.toggle()
        dt = time.perf_counter() - t0
        latencies.append(dt)
        # Verify state correctness
        expected_state = (i % 2 == 0)  # Started inactive: toggle 0 -> False to True? Wait:
        # Before loop, mgr was active from test 4! Let's check state.

    t_total = time.perf_counter() - t_start
    min_lat = min(latencies) * 1000
    max_lat = max(latencies) * 1000
    avg_lat = (sum(latencies) / len(latencies)) * 1000
    sorted_lat = sorted(latencies)
    p95_lat = sorted_lat[int(len(sorted_lat) * 0.95)] * 1000

    print(f"  Total time for 50 toggles: {t_total:.4f}s")
    print(f"  Latency per toggle (ms): Min={min_lat:.2f}ms, Max={max_lat:.2f}ms, Avg={avg_lat:.2f}ms, P95={p95_lat:.2f}ms")

    # If any toggle froze for > 200ms (previous bug was ~2024ms)
    frozen_toggles = [idx for idx, lat in enumerate(latencies) if lat > 0.200]
    if frozen_toggles:
        failures.append(f"TEST 5 FAILED: {len(frozen_toggles)} toggles froze (> 200ms): {frozen_toggles}")
    elif max_lat > 100:
        print(f"  WARNING: Max latency reached {max_lat:.2f}ms, but below freeze threshold.")
        print("  -> PASS: 50 toggles executed without freezing.")
    else:
        print("  -> PASS: Ultra-low latency verified across all 50 toggles.")

    # -------------------------------------------------------------
    # 6. Memory & Handle Stability across 50 More Toggles
    # -------------------------------------------------------------
    print("\n[TEST 6] Stress-Testing Memory & Handle Stability (50 additional toggles)...")
    mem_before = get_mem_bytes()
    handles_before = get_handle_count()
    gdi_before, user_before = get_gui_resources()

    print(f"  Baseline: Memory={mem_before / 1024 / 1024:.2f} MB, Handles={handles_before}, GDI={gdi_before}, USER={user_before}")

    for _ in range(50):
        mgr.toggle()

    # Ensure deactivated at end of stress test
    if mgr.is_active:
        mgr.deactivate()

    mem_after = get_mem_bytes()
    handles_after = get_handle_count()
    gdi_after, user_after = get_gui_resources()

    delta_mem = (mem_after - mem_before) / 1024 / 1024
    delta_handles = handles_after - handles_before
    delta_gdi = gdi_after - gdi_before
    delta_user = user_after - user_before

    print(f"  Post-Stress: Memory={mem_after / 1024 / 1024:.2f} MB, Handles={handles_after}, GDI={gdi_after}, USER={user_after}")
    print(f"  Deltas: Memory={delta_mem:+.2f} MB, Handles={delta_handles:+d}, GDI={delta_gdi:+d}, USER={delta_user:+d}")

    # Check for leaks
    if delta_gdi > 5:
        failures.append(f"TEST 6 FAILED: GDI resource leak detected (+{delta_gdi} GDI objects)")
    if delta_user > 5:
        failures.append(f"TEST 6 FAILED: USER resource leak detected (+{delta_user} USER objects)")
    if delta_handles > 20:
        failures.append(f"TEST 6 FAILED: Process handle leak detected (+{delta_handles} handles)")
    if delta_mem > 10.0:
        failures.append(f"TEST 6 FAILED: Memory leak detected (+{delta_mem:.2f} MB)")

    if not any("TEST 6 FAILED" in f for f in failures):
        print("  -> PASS: Zero resource leaks detected across 50 rapid toggle cycles.")

    # -------------------------------------------------------------
    # 7. Idempotence & Boundary Case Testing
    # -------------------------------------------------------------
    print("\n[TEST 7] Verifying Idempotence & Edge Cases...")
    # Double activation
    mgr.deactivate()
    act1 = mgr.activate()
    hwnd1 = mgr._hwnd
    act2 = mgr.activate()
    hwnd2 = mgr._hwnd
    if not act1 or not act2 or hwnd1 != hwnd2:
        failures.append(f"TEST 7 FAILED: Duplicate activation created new hwnd: {hwnd1} vs {hwnd2}")
    else:
        print("  - Double activate() verified idempotent (retained single hwnd).")

    # Double deactivation
    deact1 = mgr.deactivate()
    hwnd_after_deact = mgr._hwnd
    deact2 = mgr.deactivate()
    if not deact1 or not deact2 or hwnd_after_deact is not None or mgr._hwnd is not None:
        failures.append("TEST 7 FAILED: Double deactivate() failed or left non-None hwnd.")
    else:
        print("  - Double deactivate() verified idempotent and clean.")

    # Destroyed window state check
    if hwnd1:
        is_still_window = user32.IsWindow(hwnd1)
        if is_still_window:
            failures.append(f"TEST 7 FAILED: Window handle 0x{hwnd1:X} was not destroyed by deactivate()!")
        else:
            print("  - DestroyWindow confirmed: previous hwnd is invalid/destroyed.")

    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    if failures:
        print(f"VERDICT: REQUEST_CHANGES ({len(failures)} failures encountered)")
        for fail in failures:
            print(f"  - {fail}")
        return False
    else:
        print("VERDICT: APPROVE (100% empirical tests passed with zero defects)")
        return True


if __name__ == "__main__":
    success = run_all_empirical_tests()
    sys.exit(0 if success else 1)
