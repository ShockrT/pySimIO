from pySimIO.data import ProcessVariable
from pySimIO.data import FlowPath

class PVModel:
    model_id = None
    def __init__(self):
        self.conditions = {
            "has_cv": False,
        }
        self.is_configured = False
        self.flow_path = FlowPath()

    def check_config(self, pv: ProcessVariable):
        if pv.cvTag == "":
            self.conditions["has_cv"] = False
        else:
            self.conditions["has_cv"] = True
        # If any condition is false, the model is not configured
        for condition in self.conditions.values():
            if not condition:
                self.is_configured = False
                return
        self.is_configured = True

class Flow(PVModel):
    flow_path = FlowPath
    model_id = 1
    def __init__(self):
        super().__init__()

    def check_config(self, pv: ProcessVariable):
        if pv.cvTag == "":
            self.conditions["has cv"] = False
        else:
            self.conditions["has cv"] = True
        # If any condition is false, the model is not configured
        for condition in self.conditions.values():
            if not condition:
                self.is_configured = False
                return
        self.is_configured = True


class Pressure:
    model_id = 2
    def __init__(self):
        self.conditions = {
            "has cv": False,
        }
        self.is_configured = False

    def check_config(self, pv: ProcessVariable):
        if pv.cvTag == "":
            self.conditions["has cv"] = False
        else:
            self.conditions["has cv"] = True
        # If any condition is false, the model is not configured
        for condition in self.conditions.values():
            if not condition:
                self.is_configured = False
                return
        self.is_configured = True


class Temperature:
    model_id = 3
    def __init__(self):
        self.conditions = {
            "heat path open": False,
            "cool path open": False,
        }
        self.heat_path = FlowPath
        self.cool_path = FlowPath
        self.heat_rate = 0.0
        self.cool_rate = 0.0

class Level:
    model_id = 4
    def __init__(self):
        self.conditions = {
            "inlet_path_open": False,
            "outlet_path_open": False,
        }
        self.inlet_paths = [FlowPath]
        self.outlet_paths = [FlowPath]
        self.inlet_flows = [0.0]
        self.outlet_flows = [0.0]
