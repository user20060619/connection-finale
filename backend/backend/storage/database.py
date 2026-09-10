import sqlite3
import json
from datetime import datetime

class MetadataDB:
    def __init__(self, db_path="metadata.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                image_id TEXT PRIMARY KEY,
                acquisition_date TEXT,
                sensor_type TEXT,
                bounding_box TEXT,
                resolution REAL,
                created_at TEXT
            )
        """)
        self.conn.commit()

    def add_image(self, image_id, date, sensor_type, bounding_box, resolution):
        self.cursor.execute("""
            INSERT INTO images (image_id, acquisition_date, sensor_type, bounding_box, resolution, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (image_id, date, sensor_type, bounding_box, resolution, datetime.now().isoformat()))
        self.conn.commit()
        print(f" Added image: {image_id}")

    def get_image(self, image_id):
        self.cursor.execute("SELECT * FROM images WHERE image_id = ?", (image_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                "image_id": row[0],
                "acquisition_date": row[1],
                "sensor_type": row[2],
                "bounding_box": json.loads(row[3]),
                "resolution": row[4],
                "created_at": row[5]
            }
        return None

    def get_all_images(self):
        self.cursor.execute("SELECT * FROM images")
        rows = self.cursor.fetchall()
        return [{
            "image_id": row[0],
            "acquisition_date": row[1],
            "sensor_type": row[2],
            "bounding_box": json.loads(row[3]),
            "resolution": row[4],
            "created_at": row[5]
        } for row in rows]

    def close(self):
        self.conn.close()