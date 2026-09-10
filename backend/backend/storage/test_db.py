from database import MetadataDB
import json

def test_database():
    db = MetadataDB("test_metadata.db")
    
    db.add_image(
        image_id="test_001",
        date="2026-09-02",
        sensor_type="optical",
        bounding_box=json.dumps({"lat": 19.0, "lon": 72.8}),
        resolution=10.0
    )
    
    result = db.get_image("test_001")
    print(" Test entry retrieved:", result)
    
    db.close()

if __name__ == "__main__":
    test_database()