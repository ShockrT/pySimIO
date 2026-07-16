from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSizePolicy, QVBoxLayout,
)

from persistence.project_store import ProjectStore
from core.plc_conn_mgr import PLCConnectionManager


class PLCConnectionDialog(QDialog):
    def __init__(self, store: ProjectStore, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("Connect to PLC")
        self.plc_name_input = QLineEdit()
        self.plc_name_input.setPlaceholderText("e.g., MainPLC01")
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("e.g., 192.168.1.10")
        self.slot_input = QLineEdit("0")

        connect_btn = QPushButton("Connect")
        cancel_btn = QPushButton("Cancel")
        for button in (connect_btn, cancel_btn):
            button.setMinimumHeight(36)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        connect_btn.clicked.connect(self.connect_to_plc)
        cancel_btn.clicked.connect(self.reject)

        layout = QVBoxLayout(self)
        for label, editor in (("PLC Name:", self.plc_name_input), ("PLC IP Address:", self.ip_input), ("Slot Number:", self.slot_input)):
            layout.addWidget(QLabel(label))
            layout.addWidget(editor)
        buttons = QHBoxLayout()
        buttons.addWidget(connect_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        self.plc_connection = None

    def connect_to_plc(self):
        ip = self.ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "Missing Address", "Enter the PLC IP address.")
            return
        try:
            slot = int(self.slot_input.text().strip() or "0")
        except ValueError:
            QMessageBox.warning(self, "Invalid Slot", "Slot must be an integer.")
            return
        plc = PLCConnectionManager(ip, slot, self.plc_name_input.text())
        if not plc.connect():
            QMessageBox.critical(self, "Connection Failed", f"Could not connect to PLC at {ip}/{slot}")
            return
        self.plc_connection = plc
        self.store.upsert_plc_profile({"name": plc.name, "ip_address": plc.ip_address, "slot": plc.slot})
        self.accept()
