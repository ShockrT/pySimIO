import tkinter as tk
from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Combobox
from models import *
from data import ProcessVariable, PLCData, Valve, FlowPath
from functools import partial
import json

from pySimIO.data import ControlVariable

COLUMN_HEADINGS = ["Analog Input", "Active", "Device Type", "Value", "Model"]
COLUMN_WIDTHS = [30, 10, 20, 20, 20]
MODEL_TYPES = ["None", "Flow", "Pressure", "Temperature", "Level"]


class GUI:
    def __init__(self, opc_interface, plc_simulator, plc: PLCData):
        self.simulation_thread = None
        self.opc_interface = opc_interface
        self.plc_simulator = plc_simulator
        self.plc_data = plc
        self.pv_list = plc.pv_list

        # Create the main window
        self.root = tk.Tk()
        #self.root.geometry("600x300")
        self.root.config(padx=20, pady=20)
        self.root.title("pySIMIO")

        # Create the main frame
        self.main_frame = Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=True)

        # Create header frame
        self.header_frame = Frame(self.main_frame, background="purple")
        self.header_frame.pack(fill=BOTH)

        # Create a canvas inside the main frame
        self.canvas = Canvas(self.main_frame, background="red")
        scrollbar = Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)

        # Create scrollable frame
        self.table_frame = Frame(self.canvas, background="yellow")
        self.table_frame.pack(side=TOP, fill=BOTH, expand=True)

        # Attach scrollable frame to canvas
        self.window_id = self.canvas.create_window((0, 0), window=self.table_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        # Pack canvas and scrollbar
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Ensure width of table frame equals width of canvas
        self.canvas.bind("<Configure>", self.update_scroll_region)

        # Create table headers
        for col_num, col_name in enumerate(COLUMN_HEADINGS):
            Label(self.header_frame,
                  text=col_name,
                  font=("Arial", 10, "bold"),
                  borderwidth=2,
                  relief="solid",
                  width=COLUMN_WIDTHS[col_num]).pack(side=LEFT, fill=BOTH, expand=True)

        # Add the data to the table
        for pv in self.pv_list:
            row_frame = Frame(self.table_frame, background="green")
            new_label = Label(row_frame, text=pv.name)
            new_label.configure(width=COLUMN_WIDTHS[0])
            new_checkbox = Checkbutton(row_frame, command=pv.toggle_active)
            new_checkbox.configure(width=COLUMN_WIDTHS[1])
            new_device_type_label = Label(row_frame, text=pv.model)
            new_device_type_label.configure(width=COLUMN_WIDTHS[2])
            new_value_label = Label(row_frame, text=f"{pv.value}")
            new_value_label.configure(width=COLUMN_WIDTHS[3])
            new_modelcfg_button = Button(row_frame,
                                         text="Configure Model",
                                         command=partial(self.open_model_config, pv))
            new_modelcfg_button.configure(width=COLUMN_WIDTHS[4])
            # Pack new row underneath previous one
            row_frame.pack(side=TOP, fill=BOTH, expand=True)
            # Pack row widgets left to right
            new_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_checkbox.pack(side=LEFT, fill=BOTH, expand=True)
            new_device_type_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_value_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_modelcfg_button.pack(side=LEFT, fill=BOTH, expand=True)

    def update_scroll_region(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.itemconfig(self.window_id, width=self.canvas.winfo_width())  # Set table width = canvas width

    def create_tag_table(self, master):
        for pv in self.pv_list:
            new_label = Label(self.table_frame, text=pv.name)
            new_label.configure(width=COLUMN_WIDTHS[0])
            new_checkbox = Checkbutton(self.table_frame, command=pv.toggle_active)
            new_checkbox.configure(width=COLUMN_WIDTHS[1])
            new_device_type_label = Label(self.table_frame, text=pv.model)
            new_device_type_label.configure(width=COLUMN_WIDTHS[2])
            new_cv_label = Label(self.table_frame, text=pv.cvTag)
            new_cv_label.configure(width=COLUMN_WIDTHS[3])
            new_value_label = Label(self.table_frame, text=f"{pv.value}")
            new_value_label.configure(width=COLUMN_WIDTHS[4])
            new_modelcfg_button = Button(self.table_frame,
                                         text="Configure Model",
                                         command=partial(self.open_model_config, pv))
            new_modelcfg_button.configure(width=COLUMN_WIDTHS[5])
            new_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_checkbox.pack(side=LEFT, fill=BOTH, expand=True)
            new_device_type_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_cv_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_value_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_modelcfg_button.pack(side=LEFT, fill=BOTH, expand=True)

    def open_model_config(self, pv: ProcessVariable):
        model_config_wizard = ModelConfigWizard(pv, plc=self.plc_data)

    #  def start_simulation(self):
    #     active_tags = [self.tree.item(item)['values'][0] for item in self.tree.get_children() if
    #                    self.tree.item(item)['values'][1] == "True"]
    #     #self.simulation_thread = threading.Thread(target=self.plc_simulator.simulate, args=(active_tags,))
    #     self.simulation_thread.start()
    #
    # def stop_simulation(self):
    #     self.plc_simulator.stop_simulation()

    def run(self):
        self.root.mainloop()


class ModelConfigWizard:
    def __init__(self, pv: ProcessVariable, plc: PLCData):
        self.window = tk.Tk()
        self.window.config(padx=20, pady=20)
        self.window.title(f"Model Configuration Wizard for {pv.name}")
        self.canvas = Canvas(self.window)
        self.plc = plc
        self.pv = pv
        self.model_view = ModelUI(self.window, pv=self.pv, plc=self.plc)

        model_type_label = Label(self.window, text="Model Type: ")
        model_type_label.grid(row=0, column=0)
        self.model_select_combobox = Combobox(self.window, values=MODEL_TYPES)
        self.model_select_combobox.bind("<<ComboboxSelected>>", self.on_model_select)
        self.model_select_combobox.grid(row=0, column=1)
        self.save_button = Button(self.window, text="Save Model", command=self.save_model)
        self.save_button.grid(row=0, column=2)

    def on_model_select(self, event):
        self.pv.model_type = self.model_select_combobox.get()
        self.update_model_view(self.pv)

    def update_model_view(self, pv):
        if pv.model_type == "Flow":
            model = Flow()
            self.model_view = FlowModelUI(self.window, pv=self.pv, plc=self.plc)

    def save_model(self):
        self.pv.cv.clear()
        for item in self.model_view.cv_listbox.curselection():
            cv = ControlVariable()
            cv.name = item.get()
            self.pv.cv.append(cv)  # Tie the control variable objects to the process variable model
        # TODO 3) Write process variable model to a file
        new_data = {
            self.pv.name: self.pv.serialize_pv(),
        }
        try:
            with open("pv_models.json", "r") as file:
                # Reading existing data
                data = json.load(file)
        except FileNotFoundError:
            with open("pv_models.json", "w") as file:
                json.dump(new_data, file, sort_keys=True, indent=4)
        else:
            # Update existing data with new data
            data.update(new_data)
            with open("pv_models.json", "w") as file:
                json.dump(data, file , indent=4)
        finally:
            self.window.destroy()

class ModelUI:
    def __init__(self, window, pv: ProcessVariable, plc):
        self.plc = plc
        self.pv = pv
        self.model = ""
        # Create a frame to contain all model data
        self.model_frame = Frame(window, borderwidth="2", relief="ridge")
        self.model_frame.grid(row=1, column=0, columnspan=2)
        # Create a frame to contain all control variable data
        cv_frame = Frame(self.model_frame)
        cv_frame.grid(row=0, column=0)
        cv_label = Label(cv_frame, text="Control Variables: ")
        cv_label.grid(row=0, column=0)
        self.cv_listbox = Listbox(cv_frame, selectmode="multiple")
        for item in self.plc.cv_list:
            self.cv_listbox.insert(END, item.name)
        # self.cv_listbox.bind("<<ListboxSelect>>", self.on_cv_select)
        self.cv_listbox.grid(row=0, column=1)
        # TODO 2) Add spinbox to setting cv Gain property

class FlowModelUI(ModelUI):
    def __init__(self, window, pv: ProcessVariable, plc):
        super().__init__(window, pv, plc)
        self.model = Flow

        flow_path_label = Label(self.model_frame, text="Flow Path: ")
        flow_path_label.grid(row=2, column=0)
        self.flow_path_select_combobox = Combobox(self.model_frame, values=self.get_flow_path_names())
        self.flow_path_select_combobox.bind("<<ComboboxSelected>>", self.on_flow_path_select)
        self.flow_path_select_combobox.grid(row=2, column=1)
        self.create_fp_button = Button(self.model_frame, text="Create New Flow Path", command=self.create_new_flow_path)
        self.create_fp_button.grid(row=2, column=2)

    # Get the list of selected CVs and add them to the process variable model
    def on_cv_select(self, event):
        widget = event.widget
        selection = widget.curselection()
        self.pv.cv.clear()
        for item in selection:
            cv = ControlVariable()
            cv.name = widget.get(item)
            self.pv.cv.append(cv)  # Tie the control variable objects to the process variable model
        # for count, cv in enumerate(self.pv.cv):
        #     print(f"{count}: {cv.name}")

    def on_valve_select(self, event):
        widget = event.widget
        selection = widget.curselection()
        self.pv.cv.clear()
        for item in selection:
            cv = ControlVariable()
            cv.name = widget.get(item)
            self.pv.cv.append(cv)  # Tie the control variable objects to the process variable model
        # for count, cv in enumerate(self.pv.cv):
        #     print(f"{count}: {cv.name}")

    def on_flow_path_select(self, event):
        self.model.flow_path.name = self.flow_path_select_combobox.get()
        # self.update_display(self.pv)
        print(f"Flow Path Name: {self.model.flow_path.name}")

    def create_new_flow_path(self):
        fp_wizard = FlowPathConfigWizard(self.plc)

    def get_flow_path_names(self):
        fp_names = []
        try:
            with open("flowpaths.json", "r") as fp_file:
                # Reading existing data
                fp_data = json.load(fp_file)
                for key, value in fp_data.items():
                    fp_names.append(f"{key} - {value["description"]}")
        except FileNotFoundError:
            pass
        return fp_names


class FlowPathConfigWizard:
    def __init__(self, plc: PLCData):
        self.plc = plc
        self.fp = FlowPath()
        self.window = tk.Tk()
        self.window.config(padx=20, pady=20, width=700, height=700)
        self.window.title("Flow Path Configuration Wizard")
        self.canvas = Canvas(self.window)
        # Create a frame to contain all flow path data
        fp_frame = Frame(self.window, borderwidth="2", relief="ridge")
        fp_frame.grid(row=1, column=0, columnspan=2)
        save_fp_button = Button(fp_frame, text="Save", command=self.save_flow_path)
        save_fp_button.grid(row=0, column=3)
        Label(fp_frame, text="Flow Path Name: ").grid(row=0, column=0)
        self.fp_name_entry = Entry(fp_frame)
        self.fp_name_entry.grid(row=0, column=1, columnspan=2)
        Label(fp_frame, text="Flow Path Description: ").grid(row=1, column=0)
        self.fp_desc_entry = Entry(fp_frame)
        self.fp_desc_entry.grid(row=1, column=1, columnspan=2)
        self.valve_listbox = Listbox(fp_frame, selectmode="multiple")
        for item in self.plc.valve_list:
            self.valve_listbox.insert(END, item.name)
        #self.valve_listbox.bind("<<ListboxSelect>>", self.on_cv_select)
        self.valve_listbox.grid(row=2, column=1)


    def save_flow_path(self):
        new_fp = FlowPath()
        # Save the properties (name and segment definitions) of the new flow path
        new_fp.name = self.fp_name_entry.get()
        new_fp.description = self.fp_desc_entry.get()
        selection = self.valve_listbox.curselection()
        new_fp.segments.clear()
        for item in selection:
            new_valve = Valve()
            new_valve.name = self.valve_listbox.get(item)
            new_fp.segments.append(new_valve)  # Tie the control variable objects to the process variable model
        serialized_fp = {
            new_fp.name: new_fp.serialize_fp(),
        }

        # Check for valid flow path name
        if len(new_fp.name) == 0:
            messagebox.showerror(title="Invalid flow path name", message="Flow path must have a name.")
        else:
            # Add to list of flow paths in PLC
            self.plc.flow_paths.append(new_fp)
            print(self.plc.flow_paths)
            try:
                with open("flowpaths.json", "r") as fp_file:
                    # Reading existing data
                    fp_data = json.load(fp_file)
            except FileNotFoundError:
                with open("flowpaths.json", "w") as fp_file:
                    json.dump(serialized_fp, fp_file, sort_keys=True, indent=4)
            else:
                # Update existing data with new data
                fp_data.update(serialized_fp)
                with open("flowpaths.json", "w") as fp_file:
                    json.dump(fp_data, fp_file, indent=4)
            finally:
                self.fp_name_entry.delete(0, END)
                #self.valve_listbox.select_clear()
                self.window.destroy()