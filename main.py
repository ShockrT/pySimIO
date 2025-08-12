# main.py
import sys
from PyQt6.QtWidgets import QApplication
from core.plc_conn_mgr import PLCConnectionManager
from gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)

    plc = PLCConnectionManager()
    plc.connect_if_needed()

    win = MainWindow(plc=plc)
    win.resize(1100, 700)
    win.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
