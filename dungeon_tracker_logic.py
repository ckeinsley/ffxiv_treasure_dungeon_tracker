import sqlite3


class DungeonTrackerLogic:
    def __init__(self):
        self.conn = sqlite3.connect("dungeon_runs.db")
        self.cursor = self.conn.cursor()

    def database_setup(self):
        """Set up the SQLite database."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT
            )
        """
        )

        rooms = [
            ("Room 1", "The first room of the dungeon."),
            ("Room 2", "The second room of the dungeon."),
            ("Room 3", "The third room of the dungeon."),
            ("Room 4", "The fourth room of the dungeon."),
            ("Room 5", "The final room of the dungeon."),
        ]

        for room_name, room_description in rooms:
            # Check if the room already exists by its name
            self.cursor.execute(
                "SELECT COUNT(*) FROM rooms WHERE name = ?", (room_name,)
            )
            if self.cursor.fetchone()[0] == 0:
                # If the room does not exist, insert it
                self.cursor.execute(
                    "INSERT INTO rooms (name, description) VALUES (?, ?)",
                    (room_name, room_description),
                )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS loot_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                room_id INTEGER NOT NULL,
                door TEXT NOT NULL,
                loot_id INTEGER,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (loot_id) REFERENCES loot_items(id)
            )
        """
        )

        self.conn.commit()

    def get_loot_items(self):
        """Fetch loot items from the database."""
        self.cursor.execute("SELECT name FROM loot_items")
        return [row[0] for row in self.cursor.fetchall()]

    def add_loot_item(self, new_loot_item):
        """Add a new loot item to the database."""
        self.cursor.execute(
            "INSERT INTO loot_items (name) VALUES (?)", (new_loot_item,)
        )
        self.conn.commit()

    def get_graph_data(self, room_id):
        """Fetch graph data for the specified room."""
        graph_data = {"Left": 0, "Right": 0}
        self.cursor.execute(
            """
            SELECT door, COUNT(*) 
            FROM runs 
            WHERE room_id = ? 
            GROUP BY door
        """,
            (room_id,),
        )

        for door_name, count in self.cursor.fetchall():
            graph_data[door_name.capitalize()] = count

        return graph_data

    def complete_run(self, run_data):
        """Complete the run and save data to the database."""
        run_data_to_insert = []
        for date, room, door, loot in run_data:
            self.cursor.execute(
                "SELECT id FROM rooms WHERE name = ?", (f"Room {room}",)
            )
            room_id = self.cursor.fetchone()
            if not room_id:
                raise ValueError(f"Room {room} not found!")
            room_id = room_id[0]

            loot_id = None
            if loot:
                self.cursor.execute("SELECT id FROM loot_items WHERE name = ?", (loot,))
                loot_id = self.cursor.fetchone()
                if loot_id:
                    loot_id = loot_id[0]
                else:
                    raise ValueError(f"Loot item '{loot}' not found!")

            run_data_to_insert.append((date, room_id, door, loot_id))

        self.cursor.executemany(
            "INSERT INTO runs (run_date, room_id, door, loot_id) VALUES (?, ?, ?, ?)",
            run_data_to_insert,
        )
        self.conn.commit()

    def generate_report(self):
        """Generate report data for all rooms."""
        report_data = {}
        for room in range(1, 6):
            self.cursor.execute(
                """
                SELECT li.name
                FROM runs r
                JOIN loot_items li ON r.loot_id = li.id
                WHERE r.room_id = ?
            """,
                (room,),
            )
            loot = [row[0] for row in self.cursor.fetchall()]

            self.cursor.execute(
                """
                SELECT door, COUNT(*) 
                FROM runs 
                WHERE room_id = ? 
                GROUP BY door
            """,
                (room,),
            )
            door_counts = {door: count for door, count in self.cursor.fetchall()}
            total_visits = sum(door_counts.values())

            left_correct = door_counts.get("left", 0)
            right_correct = door_counts.get("right", 0)

            left_correct_percentage = (
                (left_correct / total_visits * 100) if total_visits > 0 else 0
            )
            right_correct_percentage = (
                (right_correct / total_visits * 100) if total_visits > 0 else 0
            )
            left_correct_percentage_string = f"{left_correct_percentage:.2f}%"
            right_correct_percentage_string = f"{right_correct_percentage:.2f}%"

            loot_display = "\n".join(set(loot)) if loot else "No loot recorded"

            if room == 5:
                left_correct_percentage_string = "-"
                right_correct_percentage_string = "-"

            report_data[room] = [
                f"Room {room}",
                loot_display,
                left_correct_percentage_string,
                right_correct_percentage_string,
                str(left_correct),
                str(right_correct),
                str(total_visits),
            ]

        return report_data

    def close(self):
        """Close the database connection."""
        self.conn.close()
