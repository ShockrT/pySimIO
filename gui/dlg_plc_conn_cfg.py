from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                             QHBoxLayout, QPushButton, QMessageBox, QSizePolicy)

class PLCConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to PLC")
        #self.setFixedSize(300, 150)

        self.plc_name_input = QLineEdit()
        self.plc_name_input.setPlaceholderText("e.g., MainPLC01")

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("e.g., 192.168.1.10")

        self.slot_input = QLineEdit()
        self.slot_input.setPlaceholderText("e.g., 0")

        connect_btn = QPushButton("Connect")
        cancel_btn = QPushButton("Cancel")

        for btn in (connect_btn, cancel_btn):
            btn.setMinimumHeight(36)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        connect_btn.clicked.connect(self.connect_to_plc)
        cancel_btn.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("PLC Name:"))
        layout.addWidget(self.plc_name_input)
        layout.addWidget(QLabel("PLC IP Address:"))
        layout.addWidget(self.ip_input)
        layout.addWidget(QLabel("Slot Number:"))
        layout.addWidget(self.slot_input)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(connect_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.plc_connection = None  # Will store the PLCConnectionManager instance

    def connect_to_plc(self):
        from core.plc_conn_mgr import PLCConnectionManager  # Lazy import
        ip = self.ip_input.text().strip()
        try:
            slot = int(self.slot_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid Slot", "Slot must be an integer.")
            return

        plc = PLCConnectionManager(ip, slot)
        if plc.connect():
            self.plc_connection = plc
            self.accept()
        else:
            QMessageBox.critical(self, "Connection Failed", f"Could not connect to PLC at {ip}/{slot}")
