from database import MetadataDB

def create_metadata_db():
    db = MetadataDB("metadata.db")
    
    db.add_image(
        image_id="prod_001",
        date="2026-09-03",
        sensor_type="optical",
        bounding_box='{"lat": 19.0, "lon": 72.8}',
        resolution=10.0
    )
    
    print("metadata.db created successfully!")
    db.close()

if __name__ == "__main__":
    create_metadata_db()