import sqlite3
from datetime import datetime
from tkinter import (BOTH, DISABLED, END, NORMAL, WORD, Button, Frame, Label,
                     Text, Tk, Toplevel, messagebox, simpledialog, ttk)

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from dungeon_tracker_logic import DungeonTrackerLogic


class DungeonTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dungeon Tracker")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.logic = DungeonTrackerLogic()
        self.logic.database_setup()

        self.current_room = 1
        self.run_date = datetime.now().strftime("%Y-%m-%d")
        self.run_data = []  # Store room choices temporarily until the run is completed

        # GUI Components
        self.setup_gui()
        self.create_graphs()
        for room in range(1, 5):
            self.update_graph(room)

    def setup_gui(self):
        """Create the GUI layout."""
        self.main_frame = Frame(self.root)
        self.main_frame.pack(pady=10)

        Label(self.main_frame, text=f"Run Date: {self.run_date}").grid(
            row=0, column=0, columnspan=2, pady=5, sticky="nsew"
        )

        self.room_buttons = {}
        for room in range(1, 6):  # 5 rooms -> 4 doors
            Label(self.main_frame, text=f"Room {room}").grid(
                row=room, column=0, pady=5, sticky="nsew"
            )
            frame = Frame(self.main_frame)
            frame.grid(row=room, column=1, padx=5, pady=5, sticky="nsew")

            if room != 5:
                left_button = Button(
                    frame,
                    text="Left",
                    state=NORMAL if room == 1 else DISABLED,
                    command=lambda r=room: self.record_choice(r, "left"),
                )
                left_button.grid(row=0, column=0, padx=5, sticky="nsew")

                right_button = Button(
                    frame,
                    text="Right",
                    state=NORMAL if room == 1 else DISABLED,
                    command=lambda r=room: self.record_choice(r, "right"),
                )
                right_button.grid(row=0, column=1, padx=5, sticky="nsew")
            else:
                left_button = Button(
                    frame,
                    text="Submit Final Room Loot",
                    state=NORMAL if room == 1 else DISABLED,
                    command=lambda r=room: self.record_choice(r, "right"),
                )
                left_button.grid(row=0, column=0, padx=5, sticky="nsew")

            self.room_buttons[room] = {
                "left": left_button,
                "right": right_button,
                "loot": self.create_loot_dropdown(room),
            }

        Button(self.main_frame, text="Add Loot Item", command=self.add_loot_item).grid(
            row=1, column=4, columnspan=2, pady=10, sticky="nsew"
        )
        Button(self.main_frame, text="Complete Run", command=self.complete_run).grid(
            row=6, column=0, columnspan=2, pady=10, sticky="nsew"
        )
        Button(
            self.main_frame, text="Generate Report", command=self.generate_report
        ).grid(row=7, column=0, columnspan=2, pady=10, sticky="nsew")

    def create_loot_dropdown(self, room):
        loot_items = self.logic.get_loot_items()

        # Create a drop-down for loot selection in the current room
        loot_dropdown = ttk.Combobox(self.main_frame, values=loot_items, state="normal")
        loot_dropdown.grid(row=room, column=2, padx=10, pady=5, sticky="nsew")
        return loot_dropdown

    def update_loot_dropdowns(self):
        """Update the loot drop-down lists in all rooms."""
        # Clear the previous loot dropdowns
        for room in range(1, 6):
            if "loot" in self.room_buttons[room]:
                self.room_buttons[room]["loot"].destroy()  # Remove old drop-down
                self.room_buttons[room]["loot"] = self.create_loot_dropdown(room)

    def add_loot_item(self):
        """Prompt user to add a new loot item to the database."""
        new_loot_item = simpledialog.askstring(
            "Add Loot Item", "Enter the loot item name:"
        )

        if new_loot_item:
            # Insert the new loot item into the loot_items table
            try:
                self.logic.add_loot_item(new_loot_item)
                messagebox.showinfo(
                    "Success", f"'{new_loot_item}' has been added to the loot items."
                )
                self.update_loot_dropdowns()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "This loot item already exists.")

    def on_closing(self):
        """Handle window close event."""
        # Ask the user if they are sure about closing (optional)
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.logic.close()  # Close the database connection
            self.main_frame.destroy()  # Close the Tkinter window

    def create_graphs(self):
        """Set up graphs for each room."""
        self.graph_frame = Frame(self.root)
        self.graph_frame.pack(pady=10)

        self.graphs = {}
        for room in range(1, 5):
            fig = Figure(figsize=(3, 2), dpi=100)
            ax = fig.add_subplot(111)
            ax.bar(["Left", "Right"], [0, 0], color=["blue", "green"])
            ax.set_title(f"Room {room} Door Selections")
            ax.set_ylim(0, 10)

            canvas = FigureCanvasTkAgg(fig, self.graph_frame)
            canvas.get_tk_widget().grid(
                row=((room - 1) // 2), column=((room - 1) % 2), padx=10, pady=10
            )

            self.graphs[room] = {"figure": fig, "axes": ax, "canvas": canvas}

    def update_graph(self, room_id):
        """Update the graph for the selected room based on door selections."""
        graph_data = self.logic.get_graph_data(room_id)

        max_count = max(graph_data.values())

        # Update the graph with the new data
        ax = self.graphs[room_id]["axes"]
        ax.clear()
        ax.bar(
            ["Left", "Right"],
            [graph_data["Left"], graph_data["Right"]],
            color=["blue", "green"],
        )
        ax.set_title(f"Room {room_id} Door Selections")
        ax.set_ylim(0, max_count + 5)
        self.graphs[room_id]["canvas"].draw()

    def record_choice(self, room, door):
        """Record the choice for the current room and loot."""
        loot = self.room_buttons[room]["loot"].get().strip()
        self.run_data.append((self.run_date, room, door, loot))

        # Disable buttons for the current room
        self.room_buttons[room]["left"].config(state=DISABLED)
        self.room_buttons[room]["right"].config(state=DISABLED)

        # Enable buttons for the next room, if any
        next_room = room + 1
        if next_room in self.room_buttons:
            self.room_buttons[next_room]["left"].config(state=NORMAL)
            self.room_buttons[next_room]["right"].config(state=NORMAL)

    def complete_run(self):
        """Mark the run as completed and save to the database."""
        if not self.run_data:
            messagebox.showerror("Error", "No data to save!")
            return

        try:
            self.logic.complete_run(self.run_data)
            messagebox.showinfo("Success", "Run data saved successfully!")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        # Update all graphs for each room based on the recorded data
        for room in range(1, 5):
            self.update_graph(room)

        # Reset application state
        self.run_data = []
        self.current_room = 1
        for room in self.room_buttons:
            self.room_buttons[room]["left"].config(
                state=NORMAL if room == 1 else DISABLED
            )
            self.room_buttons[room]["right"].config(
                state=NORMAL if room == 1 else DISABLED
            )
            self.room_buttons[room]["loot"].delete(0, END)

    def generate_report(self):
        """Generate a report for all rooms, showing loot and door probabilities."""
        report_data = self.logic.generate_report()

        # Create a new top-level window for the report
        report_window = Toplevel(self.main_frame)  # Reference to the root window
        report_window.title("Dungeon Run Report")
        report_window.geometry("800x600")  # Set initial size
        report_window.resizable(True, True)  # Make the window resizable

        # Set up a grid in the new window
        report_frame = Frame(report_window)
        report_frame.pack(fill=BOTH, expand=True)

        # Column headers
        headers = [
            "Room",
            "Loot Obtained",
            "Left Door Correct %",
            "Right Door Correct %",
            "Left Door Count",
            "Right Door Count",
            "Visits",
        ]
        for col, header in enumerate(headers):
            label = Label(
                report_frame, text=header, font=("Helvetica", 10, "bold"), anchor="w"
            )
            label.grid(row=0, column=col, padx=10, pady=5, sticky="w")

        # Populate the grid with data
        for room, data in report_data.items():
            for col, value in enumerate(data):
                if col == 1:  # Loot column
                    text_widget = Text(report_frame, height=4, wrap=WORD)
                    text_widget.insert(END, value)
                    text_widget.config(state=DISABLED)
                    text_widget.grid(row=room, column=col, padx=10, pady=5, sticky="w")
                else:
                    label = Label(
                        report_frame, text=value, font=("Helvetica", 10), anchor="w"
                    )
                    label.grid(row=room, column=col, padx=10, pady=5, sticky="w")

    def close(self):
        """Close the database connection."""
        self.logic.close()
        self.root.destroy()


if __name__ == "__main__":
    root = Tk()
    app = DungeonTrackerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)  # Ensure database closes on exit
    root.mainloop()
