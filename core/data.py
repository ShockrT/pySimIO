PLANT_PAX_MODULES = ["P_ANALOG_INPUT", "P_ANALOG_OUTPUT", "P_DISCRETE_INPUT", "P_DISCRETE_OUTPUT",
                     "P_VALVE_DISCRETE", "P_VARIABLE_SPEED_DRIVE", "P_MOTOR_DISCRETE", "P_PID", "P_D4SD"]
PV_MODULE_TYPES = ["P_ANALOG_INPUT"]
CV_MODULE_TYPES = ["P_VARIABLE_SPEED_DRIVE", "P_PID", "P_ANALOG_OUTPUT"]
VALVE_TYPES = ["P_VALVE_DISCRETE"]
MODEL_TYPES = ["flow", "pressure", "temperature", "level"]

class ProcessVariable:
    def __init__(self):
        self.name = ""
        self.active = False # True = Sim Active
        self.cv = [] # List of type ControlVariable
        self.EUMin = 0.0
        self.EUMax = 100.0
        self.value = 0.0
        self.simRate = 0.1
        self.model_configured = False
        self.model_type = ""
        self.model = None
        self.cvTag = ""

    def toggle_active(self):
        self.active = not self.active
        print(f"Active status toggled for: {self.name}")

    def serialize_pv(self):
        serialized_pv =  {
                "name": self.name,
                "active": self.active,
                "cv dict": {},
                "EU Min": self.EUMin,
                "EU Max": self.EUMax,
                "model configured": self.model_configured,
                "model type": self.model_type,
                "model": self.model,
            }
        for count, cv in enumerate(self.cv):
            serialized_pv.update({"cv dict": cv.serialize_cv()})
        return serialized_pv

    # def print_properties(self):
    #     print(f"Name: {self.name}")
    #     print(f"EUMin: {self.EUMin}")
    #     print(f"EUMax: {self.EUMax}")
    #     print(f"Value: {self.value}")
    #     print(f"cvName: {self.cv}")
    #     print(f"cvRelationship: {self.cvRelationship}")

    # def check_model(self, device_type: str) -> bool:
    #     if device_type in self.DEVICE_TYPES:
    #         match device_type:
    #             case "flow":
    #                 pass

class ControlVariable:
    def __init__(self):
        self.name = ""
        self.EUMin = 0.0
        self.EUMax = 100.0
        self.value = 0.0
        self.gain = 1.0 # Impact on PV

    def serialize_cv(self):
        serialized_cv = {
            "name": self.name,
            "EU Min": self.EUMin,
            "EU Max": self.EUMax,
            "gain": self.gain,
        }
        return serialized_cv

class Valve:
    def __init__(self):
        self.name = ""
        self.is_open = False

class PLCData:
    def __init__(self):
        self.pax_modules_list = [] # All PlantPAx modules found in tag export
        self.pv_list = [] # List of process variables in the PLC (type: ProcessVariable)
        self.cv_list = [] # List of CV Names (strings)
        self.valve_list = []
        self.flow_paths = []
        # module_dict is a dictionary whose keys are the PlantPAx module types
        # and whose values are lists of PlantPAx modules (represented as dictionaries) with that data type
        self.module_dict = {}

    def print_tags(self):
        for pv in self.pv_list:
            print(pv.name)

    def get_plant_pax_modules(self, input_data):
        # Get list of all controller-scoped PlantPAx module tags from the input data
        all_pax_tags_list = [item for item in input_data
                           if item["DATATYPE"] in PLANT_PAX_MODULES and str(item["SCOPE"]) == "nan"]
        # Create new dictionary for each PlantPAx module tag
        for tag in all_pax_tags_list:
            new_module = {"Name": str(tag["NAME"]),
                          "Description": str(tag["DESCRIPTION"]),
                          "Data Type": str(tag["DATATYPE"])}
            # Add the new module to the PlantPAx module dictionary
            try:
                self.module_dict[new_module["Data Type"]].append(new_module)
            except KeyError:
                self.module_dict[new_module["Data Type"]] = [new_module]
            # Create new Process Variable object and add to list of Process Variables
            if new_module["Data Type"] in PV_MODULE_TYPES:
                new_pv = ProcessVariable()
                new_pv.name = new_module["Name"]
                self.pv_list.append(new_pv)
            # Populate a list of possible control variables based on data type
            if new_module["Data Type"] in CV_MODULE_TYPES:
                new_cv = ControlVariable()
                new_cv.name = new_module["Name"]
                self.cv_list.append(new_cv)
            # Populate a list of valves based on data type
            if new_module["Data Type"] in VALVE_TYPES:
                new_valve = Valve()
                new_valve.name = new_module["Name"]
                self.valve_list.append(new_valve)


class FlowPath:
    def __init__(self):
        self.name = ""
        self.description = ""
        # Each segment is a valve in the path
        self.segments = [] # List of valve names (strings)

    def serialize_fp(self):
        serialized_fp = {
            "name": self.name,
            "description": self.description,
        }
        for seg in enumerate(self.segments):
            serialized_fp.update({"segments": self.serialize_segments()})
        return serialized_fp

    def serialize_segments(self):
        serialized_seg = []
        for seg in self.segments:
            serialized_seg.append(seg.name)
        return serialized_seg