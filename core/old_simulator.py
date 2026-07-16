from core.data import AnalogSensor, Valve
import time
PLC_PATH = "DS3::[CAUSTIC]"

class PLCSimulator:
    def __init__(self, opc_interface):
        self.opc_interface = opc_interface
        self.simulating = False

    def simulate(self, process_variables: [AnalogSensor]):
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
    def __init__(self, process_variable: AnalogSensor, opc_interface):
        self.pv = process_variable
        self.opc_interface = opc_interface

    def compute_value(self) -> float:
        # Read the current values for the PV, CV, and EUMin/Max from the PLC
        cv_value = self.opc_interface.read_tag(f"{PLC_PATH}{self.pv.cv[0].name}") or 0.0
        pv_eu_min = self.opc_interface.read_tag(f"{PLC_PATH}{self.pv.name}.Cfg_PVEUMin") or 0.0
        pv_eu_max = self.opc_interface.read_tag(f"{PLC_PATH}{self.pv.name}.Cfg_PVEUMax") or 100.0
        pv_value = self.opc_interface.read_tag(f"{PLC_PATH}{self.pv.name}.Val")

        # Convert the pv value into a percentage of its range
        pv_value_as_percent = pv_value * (100 / (pv_eu_max - pv_eu_min))

        # If the PV's relationship to the CV is direct, the PV should increase when the CV increases
        if self.pv.cv_relationship == "direct":
            sim_value_as_percent = pv_value_as_percent + (cv_value - pv_value_as_percent) * self.pv.sim_rate
        else:
            sim_value_as_percent = pv_value_as_percent - (cv_value - pv_value_as_percent) * self.pv.sim_rate
        # Convert simulated value back to E.U.
        sim_value = sim_value_as_percent * (pv_eu_max - pv_eu_min) / 100 + pv_eu_min
        return sim_value
