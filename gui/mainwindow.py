from PyQt6 import QtWidgets
from functools import partial


from PyQt6.QtCore import pyqtSignal

from core.data import ControlVariable, FlowPath, Valve
from gui.modelconfigwizard import ModelConfigWizard

MODEL_TYPES = ["None", "Flow", "Pressure", "Temperature", "Level"]
COLUMN_HEADINGS = ["Analog Input", "Active", "Device Type", "Value", "Model"]
COLUMN_WIDTHS = [150, 60, 120, 80, 120]

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, opc_interface, plc_simulator, plc):
        super().__init__()
        self.opc_interface = opc_interface
        self.plc_simulator = plc_simulator
        self.plc = plc
        self.pv_list = plc.pv_list
        self.setWindowTitle("pySIMIO")
        self.resize(800, 600)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        header = QtWidgets.QHBoxLayout()
        for heading, width in zip(COLUMN_HEADINGS, COLUMN_WIDTHS):
            lbl = QtWidgets.QLabel(heading)
            lbl.setFixedWidth(width)
            lbl.setStyleSheet("font-weight: bold;")
            header.addWidget(lbl)
        layout.addLayout(header)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        container = QtWidgets.QWidget()
        scroll.setWidget(container)
        table_layout = QtWidgets.QVBoxLayout(container)

        for pv in self.pv_list:
            row = QtWidgets.QHBoxLayout()
            name = QtWidgets.QLabel(pv.name)
            name.setFixedWidth(COLUMN_WIDTHS[0])
            chk = QtWidgets.QCheckBox()
            chk.setChecked(pv.active if hasattr(pv, "active") else False)
            chk.stateChanged.connect(lambda _, pv=pv: pv.toggle_active())
            chk.setFixedWidth(COLUMN_WIDTHS[1])

            dtype = QtWidgets.QLabel(pv.model or "")
            dtype.setFixedWidth(COLUMN_WIDTHS[2])

            value = QtWidgets.QLabel(f"{pv.value}")
            value.setFixedWidth(COLUMN_WIDTHS[3])

            btn = QtWidgets.QPushButton("Configure Model")
            btn.clicked.connect(partial(self.open_model_config, pv))
            btn.setFixedWidth(COLUMN_WIDTHS[4])

            for widget in (name, chk, dtype, value, btn):
                row.addWidget(widget)
            table_layout.addLayout(row)

    def open_model_config(self, pv):
        dlg = ModelConfigWizard(self.plc, pv)
        dlg.exec()

