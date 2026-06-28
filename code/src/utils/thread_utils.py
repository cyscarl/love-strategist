"""线程工具 —— QThread 异步封装。

用法:
    worker = AsyncWorker()
    worker.finished.connect(on_result)
    worker.error.connect(on_error)
    worker.run(lambda: slow_function(arg1, arg2))
"""

from typing import Callable, Any

from PyQt5.QtCore import QTimer


def debounce_button(btn, seconds: int = 5) -> None:
    """点击后禁用按钮 N 秒，防止重复点击。"""
    btn.setEnabled(False)
    original_text = btn.text()
    QTimer.singleShot(seconds * 1000, lambda: _restore_btn(btn, original_text))

def _restore_btn(btn, text: str) -> None:
    btn.setEnabled(True)
    btn.setText(text)

from PyQt5.QtCore import QObject, QThread, pyqtSignal


class _Runner(QObject):
    """在 QThread 中执行目标函数的 QObject。"""
    finished = pyqtSignal(object)  # result
    error = pyqtSignal(str)        # error message

    def __init__(self, target: Callable, parent=None) -> None:
        super().__init__(parent)
        self._target = target

    def run(self) -> None:
        """执行目标函数（在 QThread 中调用）。"""
        try:
            result = self._target()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AsyncWorker(QObject):
    """异步任务执行器。

    将耗时操作（LLM 调用、批量数据库查询）放入 QThread，
    通过 pyqtSignal 通知调用方结果。

    Signals:
        finished(result): 任务成功完成，携带返回值
        error(message): 任务失败，携带错误信息
        started(): 任务开始执行
    """

    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    started = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._runner: _Runner | None = None

    def run(self, target: Callable[[], Any]) -> None:
        """在后台线程中执行 target。

        Args:
            target: 无参 callable，返回值会通过 finished 信号发出
        """
        # 等待上一次线程自然结束
        if self._thread is not None:
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(3000)  # 等最多3秒
                if self._thread.isRunning():
                    self._thread.terminate()
                    self._thread.wait(1000)
            self._thread.deleteLater()

        self._thread = QThread()
        self._runner = _Runner(target)

        self._runner.moveToThread(self._thread)

        # 接线
        self._thread.started.connect(self._runner.run)
        self._runner.finished.connect(self._on_finished)
        self._runner.error.connect(self._on_error)
        self._thread.started.connect(self.started.emit)

        # 启动
        self._thread.start()

    def _on_finished(self, result: Any) -> None:
        """Runner 完成 → 转发信号 + 清理线程。"""
        self.finished.emit(result)
        self._cleanup()

    def _on_error(self, message: str) -> None:
        """Runner 出错 → 转发信号 + 清理线程。"""
        self.error.emit(message)
        self._cleanup()

    def _cleanup(self) -> None:
        """清理 QThread。"""
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(3000)
            if self._thread.isRunning():
                self._thread.terminate()
                self._thread.wait(1000)
            self._thread.deleteLater()
            self._thread = None
            self._runner = None

    def is_running(self) -> bool:
        """检查是否有任务正在运行。"""
        return self._thread is not None and self._thread.isRunning()
