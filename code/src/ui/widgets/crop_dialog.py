"""正方形头像裁剪对话框。"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider,
)
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QImage


class CropDialog(QDialog):
    """正方形裁剪对话框。

    用法:
        dlg = CropDialog(image_path, parent=self)
        if dlg.exec_():
            dlg.save_cropped(save_path)
    """

    def __init__(self, image_path: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("裁剪头像 - 请裁剪为正方形")
        self.setMinimumSize(420, 500)
        self._pixmap = QPixmap(image_path)
        self._crop_size = min(self._pixmap.width(), self._pixmap.height())
        self._crop_x = (self._pixmap.width() - self._crop_size) // 2
        self._crop_y = (self._pixmap.height() - self._crop_size) // 2
        self._dragging = False
        self._drag_start = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        hint = QLabel("拖拽选框调整裁剪区域，下方滑块调整大小")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #999; font-size: 17px;")
        layout.addWidget(hint)

        # 图片预览（带裁剪框）
        self._preview = _CropPreview(self)
        self._preview.setPixmap(self._pixmap)
        self._preview.setCropRect(self._crop_x, self._crop_y, self._crop_size)
        layout.addWidget(self._preview, 1)

        # 裁剪大小滑块
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("选框大小:"))
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(40)
        self._slider.setMaximum(min(self._pixmap.width(), self._pixmap.height()))
        self._slider.setValue(self._crop_size)
        self._slider.valueChanged.connect(self._on_slider)
        size_row.addWidget(self._slider, 1)
        layout.addLayout(size_row)

        # 按钮
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        confirm_btn = QPushButton("确认裁剪")
        confirm_btn.setStyleSheet(
            "background-color: #07C160; color: white; border: none; "
            "border-radius: 4px; padding: 8px 20px; font-weight: 600;"
        )
        confirm_btn.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

    def _on_slider(self, value: int) -> None:
        self._crop_size = value
        # 保持选框在图片范围内
        self._crop_x = max(0, min(self._crop_x, self._pixmap.width() - value))
        self._crop_y = max(0, min(self._crop_y, self._pixmap.height() - value))
        self._preview.setCropRect(self._crop_x, self._crop_y, value)

    def get_cropped(self) -> QPixmap:
        """返回裁剪后的正方形图像。"""
        return self._pixmap.copy(self._crop_x, self._crop_y, self._crop_size, self._crop_size)

    def save_cropped(self, save_path: str) -> bool:
        """保存裁剪后的图像到文件。"""
        cropped = self.get_cropped()
        return cropped.save(save_path, "PNG")


class _CropPreview(QLabel):
    """带裁剪框拖拽的图片预览。"""

    def __init__(self, dialog: CropDialog, parent=None) -> None:
        super().__init__(parent)
        self._dlg = dialog
        self._crop_rect = QRect()
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)

    def setCropRect(self, x: int, y: int, size: int) -> None:
        self._crop_rect = QRect(x, y, size, size)
        self.update()

    def setPixmap(self, pixmap: QPixmap) -> None:
        self._full_pixmap = pixmap
        self._scaled = pixmap.scaled(
            self.width() - 20, self.height() - 20,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self._scale_x = pixmap.width() / max(1, self._scaled.width())
        self._scale_y = pixmap.height() / max(1, self._scaled.height())
        super().setPixmap(self._scaled)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._scaled.isNull():
            return
        x = int(self._crop_rect.x() / self._scale_x) + (self.width() - self._scaled.width()) // 2
        y = int(self._crop_rect.y() / self._scale_y) + (self.height() - self._scaled.height()) // 2
        w = int(self._crop_rect.width() / self._scale_x)
        h = int(self._crop_rect.height() / self._scale_y)

        painter = QPainter(self)
        # 用 QPainterPath 挖洞：外层全屏 + 内层裁剪区域（反向填充）
        from PyQt5.QtGui import QPainterPath
        from PyQt5.QtCore import QRectF
        outer = QPainterPath()
        outer.addRect(QRectF(self.rect()))
        inner = QPainterPath()
        inner.addRect(QRectF(x, y, w, h))
        mask = outer.subtracted(inner)

        painter.fillPath(mask, QColor(0, 0, 0, 100))
        # 裁剪框绿色边框
        painter.setPen(QPen(QColor("#07C160"), 2))
        painter.drawRect(x, y, w, h)
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._dlg._dragging = True
            self._dlg._drag_start = event.pos()

    def mouseMoveEvent(self, event) -> None:
        if self._dlg._dragging:
            dx = int((event.pos().x() - self._dlg._drag_start.x()) * self._scale_x)
            dy = int((event.pos().y() - self._dlg._drag_start.y()) * self._scale_y)
            self._dlg._crop_x = max(0, min(
                self._dlg._crop_x + dx,
                self._dlg._pixmap.width() - self._dlg._crop_size
            ))
            self._dlg._crop_y = max(0, min(
                self._dlg._crop_y + dy,
                self._dlg._pixmap.height() - self._dlg._crop_size
            ))
            self._dlg._drag_start = event.pos()
            self.setCropRect(
                self._dlg._crop_x, self._dlg._crop_y, self._dlg._crop_size
            )

    def mouseReleaseEvent(self, event) -> None:
        self._dlg._dragging = False
