"""PyQt5-based suggestion popup for Grammarly-style replacements."""

from __future__ import annotations

from typing import Sequence

from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class QtSuggestionPopup(QWidget):
    """Floating suggestion window that mimics Grammarly's list widget."""

    suggestion_chosen = pyqtSignal(str)
    popup_closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        self.setFocusPolicy(Qt.NoFocus)

        self._list = QListWidget(self)
        self._list.setFocusPolicy(Qt.NoFocus)
        self._list.setSelectionMode(QListWidget.SingleSelection)
        self._list.itemClicked.connect(self._emit_selection)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._list)
        self.setLayout(layout)

        self._current_position = QPoint(0, 0)

    def show_suggestions(self, suggestions: Sequence[str], position: QPoint):
        self._list.clear()
        for suggestion in suggestions:
            QListWidgetItem(suggestion, self._list)

        if self._list.count():
            self._list.setCurrentRow(0)

        self._current_position = position
        self.move(position)
        if suggestions:
            self.show()
            self.raise_()
        else:
            self.hide()

    def navigate(self, delta: int):
        if not self.isVisible() or not self._list.count():
            return
        new_row = (self._list.currentRow() + delta) % self._list.count()
        self._list.setCurrentRow(new_row)

    def current_text(self) -> str:
        item = self._list.currentItem()
        return item.text() if item else ''

    def hide_popup(self):
        if self.isVisible():
            self.hide()
            self.popup_closed.emit()

    def _emit_selection(self, item: QListWidgetItem):
        if item:
            self.suggestion_chosen.emit(item.text())
            self.hide_popup()

    def focusOutEvent(self, event):  # type: ignore[override]
        self.hide_popup()
        event.accept()

    def keyPressEvent(self, event):  # type: ignore[override]
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.suggestion_chosen.emit(self.current_text())
            self.hide_popup()
        elif event.key() == Qt.Key_Escape:
            self.hide_popup()
        elif event.key() in (Qt.Key_Up, Qt.Key_Down):
            self.navigate(-1 if event.key() == Qt.Key_Up else 1)
        else:
            super().keyPressEvent(event)
