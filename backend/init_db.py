import os
from db_models import Stop, create_tables, SessionLocal, Base, engine, Journey, JourneyState
from datetime import datetime, timedelta


def init_db():
    """Initialize the database with 3 hardcoded stops"""
    # Drop all tables and recreate them
    Base.metadata.drop_all(bind=engine)
    create_tables()
    
    # Create a session
    db = SessionLocal()
    
    # Helper function to convert time to ISO format
    def convert_time_to_iso(time_str):
        # Parse the time string
        time_obj = datetime.strptime(time_str, "%I:%M %p")
        # Combine with today's date
        today = datetime.now().date()
        datetime_obj = datetime.combine(today, time_obj.time())
        # Return ISO format
        return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")
    
    # Create 3 hardcoded stops
    stops = [
        Stop(
            name="Las Vegas Hub",
            location="Las Vegas, Nevada",
            eta=convert_time_to_iso("3:00 PM"),
            cross_street="Broadway Avenue and 5th Street",
            nearest_highway="Highway 69",
            is_delayed=False,
            delay_reason="",
            expected_location="Las Vegas, Nevada",
            reported_location="Las Vegas, Nevada",
            is_origin=True
        ),
        Stop(
            name="Downtown Tyler Hub",
            location="Tyler, Texas",
            eta=convert_time_to_iso("5:00 PM"),
            cross_street="Broadway Avenue and 5th Street",
            nearest_highway="Highway 69",
            is_delayed=False,
            delay_reason="",
            expected_location="Tyler, Texas",
            reported_location="Tyler, Texas",
        ),
        Stop(
            name="South Dallas Terminal",
            location="Dallas, Texas",
            eta=convert_time_to_iso("8:30 PM"),
            cross_street="Main Street and Commerce",
            nearest_highway="Interstate 45",
            is_delayed=False,
            delay_reason="",
            expected_location="Dallas, Texas",
            reported_location="Dallas, Texas",
            
        ),
        Stop(
            name="Houston Medical Center",
            location="Houston, Texas",
            eta=convert_time_to_iso("10:15 PM"),
            cross_street="Fannin Street and Holcombe Boulevard",
            nearest_highway="Interstate 610",
            is_delayed=False,
            delay_reason="",
            expected_location="Houston, Texas",
            reported_location="Houston, Texas"
        ),
        Stop(
            name="Washington Hub",
            location="Washington, DC",
            eta=convert_time_to_iso("11:00 PM"),
            cross_street="Fannin Street and Holcombe Boulevard",
            nearest_highway="Interstate 610",
            is_delayed=False,
            delay_reason="",
            expected_location="Washington, DC",
            reported_location="Washington, DC",
            is_destination=True
        )
    ]
    
    try:
        # Add all stops to the database first to get their IDs
        for stop in stops:
            db.add(stop)
        db.flush()  # This assigns IDs without committing
        
        # Now create the journey with the stop IDs
        journey = Journey(
            current_state=JourneyState.ORIGIN.value
        )
        # Set the stop_ids using the property which will handle JSON serialization
        journey.stop_ids = [stop.id for stop in stops]
        
        db.add(journey)
        db.commit()
        print(f"Successfully initialized database with {len(stops)} stops.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db() 