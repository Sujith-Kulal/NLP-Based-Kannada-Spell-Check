"""PyQt5 overlay window that draws Grammarly-style wavy underlines."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

import win32gui
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt5.QtWidgets import QWidget


WORD_PATTERN = re.compile(r'[^\s\n\r\t.,!?;:]+')


class TextLayoutEngine:
    """Maps document text into per-word pixel coordinates using QFont metrics."""

    def __init__(self, font_family: str = 'Nirmala UI', font_size: int = 16):
        self.set_font(font_family, font_size)

    def set_font(self, family: str, size: int):
        self.font = QFont(family, size)
        self.metrics = QFontMetrics(self.font)
        self.line_height = self.metrics.lineSpacing()

    def measure(self, text: str) -> int:
        return self.metrics.horizontalAdvance(text) if text else 0

    def layout(self, text: str) -> List[Dict[str, object]]:
        records: List[Dict[str, object]] = []
        if not text:
            return records

        y = 0
        global_index = 0
        for raw_line in text.splitlines(keepends=True):
            line = raw_line.rstrip('\r\n')
            newline_len = len(raw_line) - len(line)
            baseline = y + self.metrics.ascent()
            cursor_x = 0
            last_index = 0

            for match in WORD_PATTERN.finditer(line):
                start = match.start()
                end = match.end()
                if start > last_index:
                    cursor_x += self.measure(line[last_index:start])
                token = match.group(0)
                width = self.measure(token)
                records.append({
                    'word': token,
                    'start': global_index + start,
                    'end': global_index + end,
                    'x': cursor_x,
                    'baseline_y': baseline,
                    'width': width,
                })
                cursor_x += width
                last_index = end

            y += self.line_height
            global_index += len(line) + newline_len

        return records

    def locate(self, records: List[Dict[str, object]], word: str, preferred_index: Optional[int] = None):
        matches = [rec for rec in records if rec['word'] == word]
        if not matches:
            return None
        if preferred_index is not None:
            for rec in matches:
                if rec['start'] <= preferred_index < rec['end']:
                    return rec
        return matches[-1]


class QtOverlay(QWidget):
    """Frameless, click-through window that paints Grammarly-style underlines."""

    def __init__(self, parent=None, *, font_family: str = 'Nirmala UI', font_size: int = 16):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.layout_engine = TextLayoutEngine(font_family, font_size)
        self._underlines: List[Dict[str, object]] = []
        self._target_hwnd: Optional[int] = None
        self._window_rect = (0, 0, 0, 0)

        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(50)
        self._sync_timer.timeout.connect(self._sync_geometry)
        self._sync_timer.start()

    def set_font(self, family: str, size: int):
        self.layout_engine.set_font(family, size)
        self.update()

    def measure_word(self, word: str) -> int:
        return self.layout_engine.measure(word)

    def layout_text(self, text: str) -> List[Dict[str, object]]:
        return self.layout_engine.layout(text)

    def set_target_window(self, hwnd: int):
        self._target_hwnd = hwnd
        self._sync_geometry()

    def update_underlines(self, hwnd: int, full_text: str, targets: List[Dict[str, object]]):
        if not hwnd or not full_text or not targets:
            self.clear()
            return

        self.set_target_window(hwnd)
        layout_records = self.layout_engine.layout(full_text)
        new_underlines: List[Dict[str, object]] = []
        for target in targets:
            match = self.layout_engine.locate(layout_records, target['word'], target.get('char_index'))
            if not match:
                continue
            baseline = match['baseline_y'] + self.layout_engine.metrics.descent() / 2
            new_underlines.append({
                'word_id': target['id'],
                'x': match['x'],
                'y': baseline,
                'width': match['width'],
                'color': target.get('color', 'red'),
            })

        self._underlines = new_underlines
        if self._underlines:
            if not self.isVisible():
                self.show()
            self.update()
        else:
            self.clear()

    def clear(self):
        self._underlines.clear()
        self.hide()

    def _sync_geometry(self):
        if not self._target_hwnd:
            return
        try:
            rect = win32gui.GetWindowRect(self._target_hwnd)
        except win32gui.error:
            self._target_hwnd = None
            self.clear()
            return

        self._window_rect = rect
        left, top, right, bottom = rect
        width = max(1, right - left)
        height = max(1, bottom - top)
        self.setGeometry(left, top, width, height)

    def paintEvent(self, event):  # type: ignore[override]
        if not self._underlines:
            event.accept()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        for info in self._underlines:
            color = QColor(255, 0, 0) if info['color'] == 'red' else QColor(255, 165, 0)
            pen = QPen(color, 2, Qt.SolidLine)
            painter.setPen(pen)
            self._draw_wave(painter, int(info['x']), int(info['y']), int(info['width']))

        painter.end()
        event.accept()

    def _draw_wave(self, painter: QPainter, x_start: int, y: int, width: int):
        amplitude = 2
        wavelength = 6
        end_x = x_start + width
        toggle = False
        x = x_start
        while x < end_x:
            next_x = min(x + wavelength, end_x)
            offset = amplitude if toggle else -amplitude
            painter.drawLine(x, y + offset, next_x, y - offset)
            toggle = not toggle
            x = next_x
