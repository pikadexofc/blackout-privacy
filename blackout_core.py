"""
Blackout Core Engine
====================
Provides hardware/DWM-accelerated screen blackout protection for screen sharing
(Google Meet, Zoom, Teams, WebRTC, OBS, Discord) on Windows 10/11.

Technical Mechanism:
- Spans virtual desktop bounds across all active monitors.
- Employs WS_EX_LAYERED, WS_EX_TRANSPARENT, and WS_EX_TOPMOST.
- Sets alpha to 1 (near zero opacity, invisible to human eye, click-through).
- Applies SetWindowDisplayAffinity(hwnd, WDA_MONITOR).
- Result: Screen capture APIs (DWM/DXGI/BitBlt) receive opaque solid black,
  while physical monitor remains 100% visible and interactive.
"""

import ctypes
from ctypes import wintypes
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("blackout_core")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

# Enable Per-Monitor v2 DPI Awareness
try:
    if hasattr(user32, "SetProcessDpiAwarenessContext"):
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

# Win32 Constants
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011

WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_POPUP = 0x80000000

LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002

SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
SW_SHOW = 5

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

# Exact 64-bit ctypes types
LRESULT = ctypes.c_int64
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('style', wintypes.UINT),
        ('lpfnWndProc', WNDPROC),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', wintypes.HINSTANCE),
        ('hIcon', wintypes.HANDLE),
        ('hCursor', wintypes.HANDLE),
        ('hbrBackground', wintypes.HBRUSH),
        ('lpszMenuName', wintypes.LPCWSTR),
        ('lpszClassName', wintypes.LPCWSTR),
        ('hIconSm', wintypes.HANDLE)
    ]


# User32 64-bit API signatures
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT

user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wintypes.ATOM

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,      # dwExStyle
    wintypes.LPCWSTR,    # lpClassName
    wintypes.LPCWSTR,    # lpWindowName
    wintypes.DWORD,      # dwStyle
    ctypes.c_int,        # X
    ctypes.c_int,        # Y
    ctypes.c_int,        # nWidth
    ctypes.c_int,        # nHeight
    wintypes.HWND,       # hWndParent
    wintypes.HMENU,      # hMenu
    wintypes.HINSTANCE,  # hInstance
    wintypes.LPVOID      # lpParam
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.UpdateWindow.argtypes = [wintypes.HWND]
user32.UpdateWindow.restype = wintypes.BOOL

user32.SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND,
    wintypes.COLORREF,
    wintypes.BYTE,
    wintypes.DWORD
]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL

user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.SetWindowDisplayAffinity.restype = wintypes.BOOL

user32.GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowDisplayAffinity.restype = wintypes.BOOL

user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None

# Kernel32 64-bit API signatures
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

kernel32.GetLastError.argtypes = []
kernel32.GetLastError.restype = wintypes.DWORD

# GDI32 64-bit API signatures
gdi32.GetStockObject.argtypes = [ctypes.c_int]
gdi32.GetStockObject.restype = wintypes.HGDIOBJ

_overlay_class_atom = None


def _wnd_proc(hwnd, msg, wparam, lparam):
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


_wnd_proc_callback = WNDPROC(_wnd_proc)


def _ensure_class_registered():
    global _overlay_class_atom
    if _overlay_class_atom is not None:
        return _overlay_class_atom

    wc = WNDCLASSEXW()
    wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
    wc.style = 0
    wc.lpfnWndProc = _wnd_proc_callback
    wc.cbClsExtra = 0
    wc.cbWndExtra = 0
    wc.hInstance = kernel32.GetModuleHandleW(None)
    wc.hIcon = None
    wc.hCursor = None
    wc.hbrBackground = gdi32.GetStockObject(4)  # BLACK_BRUSH
    wc.lpszMenuName = None
    wc.lpszClassName = "BlackoutScreenPrivacyOverlayClass"
    wc.hIconSm = None

    _overlay_class_atom = user32.RegisterClassExW(ctypes.byref(wc))
    if not _overlay_class_atom:
        err = kernel32.GetLastError()
        # 1410 = ERROR_CLASS_ALREADY_EXISTS
        if err != 1410:
            raise RuntimeError(f"Failed to register overlay window class. Error code: {err}")
    return _overlay_class_atom


class ScreenBlackoutManager:
    """
    Controls the screen blackout overlay state.
    """
    def __init__(self):
        self._hwnd = None
        self._is_active = False

    @property
    def is_active(self) -> bool:
        return self._is_active

    def get_virtual_screen_bounds(self):
        """Returns (x, y, width, height) covering all attached monitors."""
        x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

        # Fallback to primary monitor if virtual metrics return 0
        if w <= 0 or h <= 0:
            x = 0
            y = 0
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
        return x, y, w, h

    def activate(self) -> bool:
        """
        Activates privacy mode: Screen becomes pitch black to any screen sharing
        stream, while remaining fully visible and interactive locally.
        """
        if self._is_active and self._hwnd and user32.IsWindow(self._hwnd):
            return True

        _ensure_class_registered()
        x, y, w, h = self.get_virtual_screen_bounds()
        logger.info(f"Activating Blackout Overlay across virtual screen: {x},{y} {w}x{h}")

        ex_style = (
            WS_EX_TOPMOST
            | WS_EX_LAYERED
            | WS_EX_TRANSPARENT
            | WS_EX_TOOLWINDOW
            | WS_EX_NOACTIVATE
        )
        hinstance = kernel32.GetModuleHandleW(None)

        hwnd = user32.CreateWindowExW(
            ex_style,
            "BlackoutScreenPrivacyOverlayClass",
            "ScreenPrivacyShield",
            WS_POPUP,
            x, y, w, h,
            None, None, hinstance, None
        )

        if not hwnd:
            err = kernel32.GetLastError()
            logger.error(f"Failed to create privacy overlay window: Error {err}")
            return False

        self._hwnd = hwnd

        # Set alpha to 1 (near zero opacity, visually transparent to human eye)
        # Windows DWM still renders it, triggering the affinity black block on capture.
        user32.SetLayeredWindowAttributes(hwnd, 0, 1, LWA_ALPHA)
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        user32.UpdateWindow(hwnd)

        # Set Display Affinity to WDA_MONITOR (0x1)
        # DWM forces this window to display ONLY on physical monitor, replacing capture with black.
        affinity_res = user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)
        if not affinity_res:
            err = kernel32.GetLastError()
            logger.warning(f"SetWindowDisplayAffinity returned {affinity_res}, error {err}")

        self._is_active = True
        logger.info("Blackout privacy protection is now ACTIVE.")
        return True

    def deactivate(self) -> bool:
        """
        Deactivates privacy mode: Screen capture immediately resumes normal view.
        """
        if self._hwnd:
            if user32.IsWindow(self._hwnd):
                user32.SetWindowDisplayAffinity(self._hwnd, WDA_NONE)
                user32.ShowWindow(self._hwnd, SW_HIDE)
                user32.DestroyWindow(self._hwnd)
            self._hwnd = None

        self._is_active = False
        logger.info("Blackout privacy protection is DEACTIVATED.")
        return True

    def toggle(self) -> bool:
        """Toggles between active and inactive states. Returns new active state."""
        if self._is_active:
            self.deactivate()
        else:
            self.activate()
        return self._is_active


__all__ = [
    "ScreenBlackoutManager",
    "WDA_NONE",
    "WDA_MONITOR",
    "WDA_EXCLUDEFROMCAPTURE",
    "WS_EX_TOPMOST",
    "WS_EX_TRANSPARENT",
    "WS_EX_TOOLWINDOW",
    "WS_EX_LAYERED",
    "WS_EX_NOACTIVATE",
    "WS_POPUP",
    "LWA_COLORKEY",
    "LWA_ALPHA",
    "SW_HIDE",
    "SW_SHOWNOACTIVATE",
    "SW_SHOW",
    "SM_XVIRTUALSCREEN",
    "SM_YVIRTUALSCREEN",
    "SM_CXVIRTUALSCREEN",
    "SM_CYVIRTUALSCREEN",
]
