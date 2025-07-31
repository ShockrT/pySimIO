from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal
from core.data import FlowPath, Valve
import json

class FlowPathConfigWizard(QtWidgets.QDialog):
    flow_path_saved = pyqtSignal(str)  # Emit the new flow path name

    def __init__(self, plc):
        super().__init__()
        self.plc = plc
        self.fp = FlowPath()
        self.setWindowTitle("Flow Path Configuration")
        self.resize(400, 300)

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QGridLayout()
        layout.addLayout(form)

        form.addWidget(QtWidgets.QLabel("Flow Path Name:"), 0, 0)
        self.name_edit = QtWidgets.QLineEdit()
        form.addWidget(self.name_edit, 0, 1, 1, 2)

        form.addWidget(QtWidgets.QLabel("Description:"), 1, 0)
        self.desc_edit = QtWidgets.QLineEdit()
        form.addWidget(self.desc_edit, 1, 1, 1, 2)

        self.listbox = QtWidgets.QListWidget()
        self.listbox.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        for valve in self.plc.valve_list:
            self.listbox.addItem(valve.name)
        form.addWidget(self.listbox, 2, 1, 1, 2)

        save = QtWidgets.QPushButton("Save")
        save.clicked.connect(self.save_flow_path)
        form.addWidget(save, 0, 3)

    def save_flow_path(self):
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.critical(self, "Error", "Flow path must have a name.")
            return
        fp = FlowPath()
        fp.name = name
        fp.description = self.desc_edit.text().strip()
        for item in self.listbox.selectedItems():
            v = Valve()
            v.name = item.text()
            fp.segments.append(v)

        serialized = { fp.name: fp.serialize_fp() }
        self.plc.flow_paths.append(fp)
        try:
            with open("../assets/flowpaths.json") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        data.update(serialized)
        with open("../assets/flowpaths.json", "w") as f:
            json.dump(data, f, indent=4)
        self.flow_path_saved.emit(name)
        self.accept()
