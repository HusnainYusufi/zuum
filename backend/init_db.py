import os
from db_models import Stop, create_tables, SessionLocal

def init_db():
    # if os.path.exists("transit.db"):
    #     os.remove("transit.db")

    """Initialize the database with 3 hardcoded stops"""
    create_tables()
    
    # Create a session
    db = SessionLocal()
    
    # Check if stops already exist
    existing_stops = db.query(Stop).count()
    if existing_stops > 0:
        print(f"Database already contains {existing_stops} stops. Skipping initialization.")
        db.close()
        return
    
    # Create 3 hardcoded stops
    stops = [
        Stop(
            name="Downtown Tyler Hub",
            location="Tyler, Texas",
            eta="5:00 PM",
            cross_street="Broadway Avenue and 5th Street",
            nearest_highway="Highway 69",
            is_delayed=False,
            delay_reason="",
            expected_location="Tyler, Texas",
            reported_location="Tyler, Texas"
        ),
        Stop(
            name="South Dallas Terminal",
            location="Dallas, Texas",
            eta="3:30 PM",
            # cross_street="Main Street and Commerce",
            # nearest_highway="Interstate 45",
            # is_delayed=True,
            # delay_reason="Heavy traffic due to accident",
            expected_location="Dallas, Texas",
            # reported_location="Richardson, Texas"
        ),
        Stop(
            name="Houston Medical Center",
            location="Houston, Texas",
            eta="7:15 PM",
            # cross_street="Fannin Street and Holcombe Boulevard",
            # nearest_highway="Interstate 610",
            # is_delayed=True,
            # delay_reason="Weather conditions",
            expected_location="Houston, Texas",
            # reported_location="Katy, Texas"
        )
    ]
    
    # Add to database
    for stop in stops:
        db.add(stop)
    
    # Commit and close
    db.commit()
    db.close()
    
    print("Database initialized with 3 stops.")

if __name__ == "__main__":
    init_db() 