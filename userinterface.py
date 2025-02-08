import tkinter as tk
from tkinter import *
from tkinter.ttk import Combobox
from models import *
from pySimIO.data import ProcessVariable, PLCData
from functools import partial


COLUMN_HEADINGS = ["Analog Input", "Active", "Device Type", "Controlled By", "Value", "Model"]
COLUMN_WIDTHS = [30, 10, 20, 50, 20, 20]
MODEL_TYPES = ["None", "Flow", "Pressure", "Temperature", "Level"]
class GUI:
    def __init__(self, opc_interface, plc_simulator, plc_data: PLCData):
        self.simulation_thread = None
        self.opc_interface = opc_interface
        self.plc_simulator = plc_simulator
        self.plc_data = plc_data
        self.pv_list = plc_data.pv_list

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
        self.canvas = Canvas(master=self.main_frame, background="red")
        scrollbar = Scrollbar(master=self.main_frame, orient="vertical", command=self.canvas.yview)

        # Create scrollable frame
        self.table_frame = Frame(master=self.canvas, background="yellow")
        self.table_frame.pack(side=TOP, fill=BOTH, expand=True)

        # Attach scrollable frame to canvas
        self.window_id = self.canvas.create_window((0,0), window=self.table_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        # Pack canvas and scrollbar
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Ensure width of table frame equals width of canvas
        self.canvas.bind("<Configure>", self.update_scroll_region)

        # Create table headers
        for col_num, col_name in enumerate(COLUMN_HEADINGS):
            Label(master=self.header_frame,
                              text=col_name,
                              font=("Arial", 10, "bold"),
                              borderwidth=2,
                              relief="solid",
                              width=COLUMN_WIDTHS[col_num]).pack(side=LEFT, fill=BOTH, expand=True)

        # Add the data to the table
        for pv in self.pv_list:
            row_frame = Frame(master=self.table_frame, background="green")
            new_label = Label(master=row_frame, text=pv.name)
            new_label.configure(width=COLUMN_WIDTHS[0])
            new_checkbox = Checkbutton(master=row_frame, command=pv.toggle_active)
            new_checkbox.configure(width=COLUMN_WIDTHS[1])
            new_device_type_label = Label(master=row_frame, text=pv.model)
            new_device_type_label.configure(width=COLUMN_WIDTHS[2])
            new_cv_label = Label(master=row_frame, text=pv.cvTag)
            new_cv_label.configure(width=COLUMN_WIDTHS[3])
            new_value_label = Label(master=row_frame, text=f"{pv.value}")
            new_value_label.configure(width=COLUMN_WIDTHS[4])
            new_modelcfg_button = Button(master=row_frame,
                                         text="Configure Model",
                                         command=partial(self.open_model_config, pv))
            new_modelcfg_button.configure(width=COLUMN_WIDTHS[5])
            # Pack new row underneath previous one
            row_frame.pack(side=TOP, fill=BOTH, expand=True)
            # Pack row widgets left to right
            new_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_checkbox.pack(side=LEFT, fill=BOTH, expand=True)
            new_device_type_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_cv_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_value_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_modelcfg_button.pack(side=LEFT, fill=BOTH, expand=True)

    def update_scroll_region(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.itemconfig(self.window_id, width=self.canvas.winfo_width()) # Set table width = canvas width

    def create_tag_table(self, master):
        for pv in self.pv_list:
            #row_frame = Frame(master=master, background="green")
            new_label = Label(master=self.table_frame, text=pv.name)
            new_label.configure(width=COLUMN_WIDTHS[0])
            new_checkbox = Checkbutton(master=self.table_frame, command=pv.toggle_active)
            new_checkbox.configure(width=COLUMN_WIDTHS[1])
            new_device_type_label = Label(master=self.table_frame, text=pv.model)
            new_device_type_label.configure(width=COLUMN_WIDTHS[2])
            new_cv_label = Label(master=self.table_frame, text=pv.cvTag)
            new_cv_label.configure(width=COLUMN_WIDTHS[3])
            new_value_label = Label(master=self.table_frame, text=f"{pv.value}")
            new_value_label.configure(width=COLUMN_WIDTHS[4])
            new_modelcfg_button = Button(master=self.table_frame,
                                         text="Configure Model",
                                         command=partial(self.open_model_config, pv))
            new_modelcfg_button.configure(width=COLUMN_WIDTHS[5])
            #self.table_frame.pack(side=TOP, fill=BOTH, expand=True)
            new_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_checkbox.pack(side=LEFT, fill=BOTH, expand=True)
            new_device_type_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_cv_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_value_label.pack(side=LEFT, fill=BOTH, expand=True)
            new_modelcfg_button.pack(side=LEFT, fill=BOTH, expand=True)


    def open_model_config(self, pv: ProcessVariable):
        model_config_wizard = ModelConfigWizard(pv, plc_data=self.plc_data)

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
    def __init__(self, pv: ProcessVariable, plc_data: PLCData):
        window = tk.Tk()
        window.config(padx=20, pady=20, width=500, height=500)
        window.title(f"Model Configuration Wizard for {pv.name}")
        self.canvas = Canvas(master=window)

        model_type_label = Label(master=window, text="Model Type: ")
        model_type_label.grid(column=0, row=0)
        model_select_combobox = Combobox(master=window, textvariable=pv.model_type, values=MODEL_TYPES)
        model_select_combobox.grid(column=1, row=0)
        cv_label = Label(master=window, text="Controlled By: ")
        cv_label.grid(column=0, row=1)
        cv_combobox = Combobox(master=window, textvariable=pv.cvTag, values=plc_data.cv_list)
        cv_combobox.grid(column=1, row=1)

class FlowPathConfigWizard:
    def __init__(self):
        window = tk.Tk()
        window.config(padx=20, pady=20, width=500, height=500)
        window.title(f"Flow Path Configuration Wizard")
        self.canvas = Canvas(master=window)