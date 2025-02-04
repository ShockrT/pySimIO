import tkinter as tk
from tkinter import ttk
import threading

class GUI:
    def __init__(self, opc_interface, plc_simulator):
        self.simulation_thread = None
        self.opc_interface = opc_interface
        self.plc_simulator = plc_simulator
        self.root = tk.Tk()
        self.root.title("PLC Tag Monitor")

        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(self.frame, columns=("Active", "Value"), show='headings')
        self.tree.heading("Active", text="Active")
        self.tree.heading("Value", text="Value")
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.populate_tags()

        self.search_button = ttk.Button(self.root, text="Search Tags", command=self.refresh_tags)
        self.search_button.pack()

        self.start_button = ttk.Button(self.root, text="Start Simulation", command=self.start_simulation)
        self.start_button.pack()

        self.stop_button = ttk.Button(self.root, text="Stop Simulation", command=self.stop_simulation)
        self.stop_button.pack()

    def populate_tags(self):
        try:
            with open("AnalogInputs.csv", "r") as f:
                tags = f.read().splitlines()
            for tag in tags:
                self.tree.insert("", tk.END, values=(tag, "False", "0.0"))
        except FileNotFoundError:
            print("No matching tags file found.")

    def refresh_tags(self):
        self.opc_interface.search_tags_by_data_type()
        self.tree.delete(*self.tree.get_children())
        self.populate_tags()

    def start_simulation(self):
        active_tags = [self.tree.item(item)['values'][0] for item in self.tree.get_children() if
                       self.tree.item(item)['values'][1] == "True"]
        self.simulation_thread = threading.Thread(target=self.plc_simulator.simulate, args=(active_tags,))
        self.simulation_thread.start()

    def stop_simulation(self):
        self.plc_simulator.stop_simulation()

    def run(self):
        self.root.mainloop()
