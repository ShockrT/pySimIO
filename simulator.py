# v1.0
# Simulation Model
#
#

import time
from data import ProcessVariable

PLC_PATH = "DS3::[CAUSTIC]"

class PLCSimulator:
    def __init__(self, opc_interface):
        self.opc_interface = opc_interface
        self.simulating = False

    def simulate(self, process_variables: [ProcessVariable]):
        self.simulating = True
        models = {pv: SimulationModel(pv, self.opc_interface) for pv in process_variables}
        while self.simulating:
            for pv, model in models.items():
                pv.value = model.compute_value()
                self.opc_interface.write_tag(pv.name, pv.value)
            time.sleep(1)

    def stop_simulation(self):
        self.simulating = False

class SimulationModel:
    def __init__(self, process_variable: ProcessVariable, opc_interface):
        self.process_variable = process_variable
        self.opc_interface = opc_interface

    def compute_value(self):
        control_variable_value = self.opc_interface.read_tag(f"{PLC_PATH}{self.process_variable.cvTag}") or 0.0

        pv_eu_min = self.opc_interface.read_tag(f"{PLC_PATH}{self.process_variable.name}.Cfg_PVEUMin")
        pv_eu_max = self.opc_interface.read_tag(f"{PLC_PATH}{self.process_variable.name}.Cfg_PVEUMax")
        pv_value = self.opc_interface.read_tag(f"{PLC_PATH}{self.process_variable.name}.Val")

        # Convert the pv value into a percentage of its range
        pv_value_as_percent = pv_value * (100 / (pv_eu_max - pv_eu_min))

        if self.process_variable.cvRelationship == "direct":
            sim_value_as_percent = pv_value_as_percent + (control_variable_value - pv_value_as_percent) * 0.1
            # Convert simulated value back to E.U.
            sim_value = sim_value_as_percent * (pv_eu_max - pv_eu_min) / 100 + pv_eu_min
            return sim_value
        else:
            return 100 - (control_variable_value * 0.5)
