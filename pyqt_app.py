import sys
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton, QComboBox, QGridLayout, QMessageBox, QInputDialog)
from PyQt5.QtChart import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter

num_rooms = 5

class DungeonTrackerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Dungeon Tracker")
        self.conn = sqlite3.connect('dungeon_runs.db')
        self.cursor = self.conn.cursor()
        self.database_setup()

        self.current_room = 1
        self.run_date = datetime.now().strftime("%Y-%m-%d")
        self.run_data = []  # Store room choices temporarily until the run is completed

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        # self.main_layout = QVBoxLayout(self.main_widget)

        self.setup_gui()
        self.create_graphs()
        for room in range(1, num_rooms + 1):
            self.update_graph(room)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Quit', 'Do you want to quit?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.conn.close()
            event.accept()
        else:
            event.ignore()

    def database_setup(self):
        """Set up the SQLite database."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT
            )
        """)

        rooms = [
            ("Room 1", "The first room of the dungeon."),
            ("Room 2", "The second room of the dungeon."),
            ("Room 3", "The third room of the dungeon."),
            ("Room 4", "The fourth room of the dungeon."),
            ("Room 5", "The final room of the dungeon."),
        ]

        for room_name, room_description in rooms:
            self.cursor.execute("SELECT COUNT(*) FROM rooms WHERE name = ?", (room_name,))
            if self.cursor.fetchone()[0] == 0:
                self.cursor.execute("INSERT INTO rooms (name, description) VALUES (?, ?)", (room_name, room_description))

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS loot_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                room_id INTEGER NOT NULL,
                door TEXT NOT NULL,
                loot_id INTEGER,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (loot_id) REFERENCES loot_items(id)
            )
        """)

        self.conn.commit()

    def setup_gui(self):
        """Create the GUI layout."""
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)

        self.run_date_label = QLabel(f"Run Date: {self.run_date}")
        self.main_layout.addWidget(self.run_date_label)

        self.room_buttons = {}
        for room in range(1, 6):
            room_label = QLabel(f"Room {room}")
            self.main_layout.addWidget(room_label)

            button_layout = QGridLayout()
            if room != 5:
                left_button = QPushButton("Left")
                left_button.setEnabled(room == 1)
                left_button.clicked.connect(lambda _, r=room: self.record_choice(r, "left"))
                button_layout.addWidget(left_button, 0, 0)

                right_button = QPushButton("Right")
                right_button.setEnabled(room == 1)
                right_button.clicked.connect(lambda _, r=room: self.record_choice(r, "right"))
                button_layout.addWidget(right_button, 0, 1)
            else:
                submit_button = QPushButton("Submit Final Room Loot")
                submit_button.setEnabled(room == 1)
                submit_button.clicked.connect(lambda _, r=room: self.record_choice(r, "right"))
                button_layout.addWidget(submit_button, 0, 0)

            self.main_layout.addLayout(button_layout)

            loot_dropdown = self.create_loot_dropdown(room)
            self.main_layout.addWidget(loot_dropdown)

            self.room_buttons[room] = {
                "left": left_button if room != 5 else None,
                "right": right_button if room != 5 else submit_button,
                "loot": loot_dropdown
            }

        add_loot_button = QPushButton("Add Loot Item")
        add_loot_button.clicked.connect(self.add_loot_item)
        self.main_layout.addWidget(add_loot_button)

        complete_run_button = QPushButton("Complete Run")
        complete_run_button.clicked.connect(self.complete_run)
        self.main_layout.addWidget(complete_run_button)

        generate_report_button = QPushButton("Generate Report")
        generate_report_button.clicked.connect(self.generate_report)
        self.main_layout.addWidget(generate_report_button)

    def create_loot_dropdown(self, room):
        self.cursor.execute("SELECT name FROM loot_items")
        loot_items = [row[0] for row in self.cursor.fetchall()]

        loot_dropdown = QComboBox()
        loot_dropdown.addItems(loot_items)
        return loot_dropdown

    def update_loot_dropdowns(self):
        """Update the loot drop-down lists in all rooms."""
        for room in range(1, 6):
            if "loot" in self.room_buttons[room]:
                self.room_buttons[room]["loot"].clear()
                self.room_buttons[room]["loot"].addItems([row[0] for row in self.cursor.execute("SELECT name FROM loot_items")])

    def add_loot_item(self):
        """Prompt user to add a new loot item to the database."""
        new_loot_item, ok = QInputDialog.getText(self, "Add Loot Item", "Enter the loot item name:")

        if ok and new_loot_item:
            try:
                self.cursor.execute("INSERT INTO loot_items (name) VALUES (?)", (new_loot_item,))
                self.conn.commit()
                QMessageBox.information(self, "Success", f"'{new_loot_item}' has been added to the loot items.")
                self.update_loot_dropdowns()
            except sqlite3.IntegrityError:
                QMessageBox.critical(self, "Error", "This loot item already exists.")

    def create_graphs(self):
        """Set up graphs for each room."""
        self.graphs = {}
        for room in range(1, num_rooms + 1):
            set0 = QBarSet("Left")
            set1 = QBarSet("Right")
            set0 << 0
            set1 << 0

            series = QBarSeries()
            series.append(set0)
            series.append(set1)

            chart = QChart()
            chart.addSeries(series)
            chart.setTitle(f"Room {room} Door Selections")
            chart.setAnimationOptions(QChart.SeriesAnimations)

            categories = ["Left", "Right"]
            axisX = QBarCategoryAxis()
            axisX.append(categories)
            chart.addAxis(axisX, Qt.AlignBottom)
            series.attachAxis(axisX)

            axisY = QValueAxis()
            axisY.setRange(0, 10)
            chart.addAxis(axisY, Qt.AlignLeft)
            series.attachAxis(axisY)

            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.Antialiasing)
            self.main_layout.addWidget(chart_view)

            self.graphs[room] = {
                "chart": chart,
                "series": series,
                "chart_view": chart_view
            }

    def update_graph(self, room_id):
        graph_data = {"Left": 0, "Right": 0}

        self.cursor.execute("""
            SELECT door, COUNT(*) 
            FROM runs 
            WHERE room_id = ? 
            GROUP BY door
        """, (room_id,))
        rows = self.cursor.fetchall()
        for row in rows:
            graph_data[row[0]] = row[1]

        series = self.graphs[room_id]["series"]
        series.clear()

        set0 = QBarSet("Left")
        set1 = QBarSet("Right")
        set0 << graph_data["Left"]
        set1 << graph_data["Right"]

        series.append(set0)
        series.append(set1)

    def record_choice(self, room, door):
        loot = self.room_buttons[room]["loot"].currentText().strip()
        self.run_data.append((self.run_date, room, door, loot))

        if room != 5:
            self.room_buttons[room]["left"].setEnabled(False)
            self.room_buttons[room]["right"].setEnabled(False)
            next_room = room + 1
            self.room_buttons[next_room]["left"].setEnabled(True)
            self.room_buttons[next_room]["right"].setEnabled(True)

    def complete_run(self):
        if not self.run_data:
            QMessageBox.critical(self, "Error", "No data to save!")
            return

        run_data_to_insert = []
        for date, room, door, loot in self.run_data:
            self.cursor.execute("SELECT id FROM rooms WHERE name = ?", (f"Room {room}",))
            room_id = self.cursor.fetchone()
            if not room_id:
                QMessageBox.critical(self, "Error", f"Room {room} not found!")
                return
            room_id = room_id[0]

            loot_id = None
            if loot:
                self.cursor.execute("SELECT id FROM loot_items WHERE name = ?", (loot,))
                loot_id = self.cursor.fetchone()
                if loot_id:
                    loot_id = loot_id[0]
                else:
                    QMessageBox.critical(self, "Error", f"Loot item '{loot}' not found!")
                    return

            run_data_to_insert.append((date, room_id, door, loot_id))

        self.cursor.executemany("INSERT INTO runs (run_date, room_id, door, loot_id) VALUES (?, ?, ?, ?)", run_data_to_insert)
        self.conn.commit()

        QMessageBox.information(self, "Success", "Run data saved successfully!")

        for room in range(1, num_rooms + 1):
            self.update_graph(room)

        self.run_data = []
        self.current_room = 1
        for room in self.room_buttons:
            if room != 5:
                self.room_buttons[room]["left"].setEnabled(room == 1)
                self.room_buttons[room]["right"].setEnabled(room == 1)
            self.room_buttons[room]["loot"].setCurrentIndex(0)

    def generate_report(self):
        report_window = QMainWindow(self)
        report_window.setWindowTitle("Dungeon Run Report")
        report_widget = QWidget()
        report_layout = QVBoxLayout(report_widget)
        report_window.setCentralWidget(report_widget)

        headers = ["Room", "Loot Obtained", "Left Door Correct %", "Right Door Correct %", "Visits"]
        header_layout = QGridLayout()
        for col, header in enumerate(headers):
            label = QLabel(header)
            header_layout.addWidget(label, 0, col)
        report_layout.addLayout(header_layout)

        for room in range(1, 6):
            self.cursor.execute("""
                SELECT li.name
                FROM runs r
                JOIN loot_items li ON r.loot_id = li.id
                WHERE r.room_id = ?
            """, (room,))
            loot = [row[0] for row in self.cursor.fetchall()]

            self.cursor.execute("""
                SELECT door, COUNT(*) 
                FROM runs 
                WHERE room_id = ? 
                GROUP BY door
            """, (room,))
            door_counts = {door: count for door, count in self.cursor.fetchall()}
            total_visits = sum(door_counts.values())

            left_correct = door_counts.get("left", 0)
            right_correct = door_counts.get("right", 0)

            left_correct_percentage = (left_correct / total_visits * 100) if total_visits > 0 else 0
            right_correct_percentage = (right_correct / total_visits * 100) if total_visits > 0 else 0
            left_correct_percentage_string = f"{left_correct_percentage:.2f}%"
            right_correct_percentage_string = f"{right_correct_percentage:.2f}%"

            loot_display = ", ".join(set(loot)) if loot else "No loot recorded"

            if room == 5:
                left_correct_percentage_string = "-"
                right_correct_percentage_string = "-"

            row_data = [f"Room {room}", loot_display, left_correct_percentage_string, right_correct_percentage_string, str(total_visits)]
            row_layout = QGridLayout()
            for col, data in enumerate(row_data):
                label = QLabel(data)
                row_layout.addWidget(label, 0, col)
            report_layout.addLayout(row_layout)

        report_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DungeonTrackerApp()
    window.show()
    sys.exit(app.exec_())
