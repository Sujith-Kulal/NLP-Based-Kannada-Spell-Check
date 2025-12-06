"""Utilities for DPI-aware scaling across the application."""

import ctypes


def ensure_per_monitor_awareness():
    """Best-effort attempt to put the process in per-monitor DPI aware mode."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except AttributeError:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    except OSError:
        # DPI awareness already set, ignore
        pass


class DPIScaler:
    """Helper for converting logical pixel values to DPI-aware measurements."""

    LOGPIXELSX = 88

    def __init__(self):
        self.dpi = self._get_system_dpi()

    def _get_system_dpi(self) -> int:
        hdc = ctypes.windll.user32.GetDC(0)
        if not hdc:
            return 96
        try:
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, self.LOGPIXELSX)
            return dpi or 96
        finally:
            ctypes.windll.user32.ReleaseDC(0, hdc)

    @property
    def scale(self) -> float:
        return (self.dpi or 96) / 96.0

    def px(self, value: float) -> int:
        scaled = float(value) * self.scale
        return int(round(scaled))
