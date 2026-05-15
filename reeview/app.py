import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def run() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ReeView")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
