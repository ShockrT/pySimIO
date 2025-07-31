from PyQt6 import QtWidgets



MODEL_TYPES = ["None", "Flow", "Pressure", "Temperature", "Level"]


class ModelConfigWizard(QtWidgets.QDialog):
    def __init__(self, plc, pv):
        super().__init__()
        self.plc = plc
        self.pv = pv
        self.setWindowTitle(f"Configure Model: {pv.name}")
        self.resize(400, 300)

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QHBoxLayout()
        layout.addLayout(form)

        form.addWidget(QtWidgets.QLabel("Model Type:"))
        self.cmb = QtWidgets.QComboBox()
        self.cmb.addItems(MODEL_TYPES)
        self.cmb.setCurrentText(pv.model_type or "None")
        self.cmb.currentTextChanged.connect(self.on_model_select)
        form.addWidget(self.cmb)

        self.save_btn = QtWidgets.QPushButton("Save Model")
        self.save_btn.clicked.connect(self.save_model)
        form.addWidget(self.save_btn)

        self.container = QtWidgets.QWidget()
        layout.addWidget(self.container)
        self.inner_layout = QtWidgets.QVBoxLayout(self.container)

        self.update_model_view()

    def on_model_select(self, text):
        self.pv.model_type = text
        self.update_model_view()

    def update_model_view(self):
        # Clear existing
        for i in reversed(range(self.inner_layout.count())):
            self.inner_layout.itemAt(i).widget().setParent(None)

        # Default CV list
        lbl = QtWidgets.QLabel("Control Variables:")
        self.inner_layout.addWidget(lbl)
        self.listbox = QtWidgets.QListWidget()
        self.listbox.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        for cv in self.plc.cv_list:
            self.listbox.addItem(cv.name)
        self.inner_layout.addWidget(self.listbox)

        if self.pv.model_type == "Flow":
            lbl = QtWidgets.QLabel("Flow Path:")
            self.inner_layout.addWidget(lbl)
            self.fp_combo = QtWidgets.QComboBox()
            self.fp_combo.addItems(self.get_flow_path_names())
            self.fp_combo.currentTextChanged.connect(self.on_flow_path_select)
            self.inner_layout.addWidget(self.fp_combo)
            btn = QtWidgets.QPushButton("Create New Flow Path")
            btn.clicked.connect(self.create_new_flow_path)
            self.inner_layout.addWidget(btn)

    def on_flow_path_select(self, text):
        if hasattr(self.pv, "model") and self.pv.model:
            self.pv.model.flow_path.name = text

    def create_new_flow_path(self):
        dlg = FlowPathConfigWizard(self.plc)
        dlg.flow_path_saved.connect(self.on_new_flow_path_created)  # connect signal
        dlg.exec()

    def save_model(self):
        self.pv.cv.clear()
        for item in self.listbox.selectedItems():
            cv = ControlVariable()
            cv.name = item.text()
            self.pv.cv.append(cv)
        data = { self.pv.name: self.pv.serialize_pv() }

        try:
            with open("pv_models.json", "r") as f:
                existing = json.load(f)
        except FileNotFoundError:
            existing = {}
        existing.update(data)
        with open("pv_models.json", "w") as f:
            json.dump(existing, f, indent=4)
        self.accept()

    def get_flow_path_names(self):
        fp_names = []
        try:
            with open("../assets/flowpaths.json", "r") as fp_file:
                # Reading existing data
                fp_data = json.load(fp_file)
                for key, value in fp_data.items():
                    fp_names.append(f"{key} - {value["description"]}")
        except FileNotFoundError:
            pass
        return fp_names

    def on_new_flow_path_created(self, new_flow_path_name):
        # Refresh combo box contents
        self.fp_combo.clear()
        self.fp_combo.addItems(self.get_flow_path_names())
        self.fp_combo.setCurrentText(new_flow_path_name)  # Optional: auto-select the newly added one
