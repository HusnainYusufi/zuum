import os
from db_models import Stop, create_tables, SessionLocal, Base, engine, Journey, JourneyState, CheckIn, RetellCall
from datetime import datetime, timedelta


def init_db():
    """Initialize the database with hardcoded stops and check-ins"""
    # Create tables if they don't exist
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
        
        # Add dummy check-in data
        sample_check_in = CheckIn(
            id=1,
            stop_id=1,  # Las Vegas Hub
            load_id="lb_213",
            query=None,
            AI_Response_Summary="I checked in with the trucker about load L123456. The trucker confirmed they were released from the dock after 2 PM, had already uploaded the POD to the Zuum app, and had no pending lumper receipts or scale tickets. The trucker also confirmed the noted damage of 2 cases crushed on the rear pallet that was documented on the BOL.",
            AI_Timestamp="2025-06-10T00:39:00",
            Issue_Flagged=True,
            Exception_Type=None,
            Call_confidence_score="95",
            call_trasfered=True,
            Tags="Completed Delivery",
        )
        db.add(sample_check_in)
        db.commit()
        
        # Add dummy retell call data
        transcript_text = """Agent: Hey there, this is Strike from dispatch checking in on load L123456. What time were you released from the dock today?
User: After two o'clock
Agent: Got it, released after 2 PM. Have you already uploaded the signed POD to the Zuum app, or do you need to text a photo now?
User: Yes. I have uploaded it.
Agent: Perfect, thanks for uploading the POD. Any lumper receipts or scale tickets we still need from you?
User: No.
Agent: Thanks for confirming. Can you confirm there were no overages, shortages or damages with the load?
User: I don't know.
Agent: No problem. According to our records, there were 2 cases crushed on the rear pallet, which was noted on the BOL. Does that sound right to you?
User: Yes.
Agent: Thanks for 
Agent: confirming. Since we have all the information we need and 
Agent: the delivery is 
Agent: complete, I'll mark this load as delivered in our system.I'll update your delivery information in our system now.
Agent: I've updated 
Agent: your delivery information in our system. Thanks for confirming all the details about load L123456. Is there"""
        
        sample_retell_call = RetellCall(
            id=1,
            check_in_id=1,
            call_id="call_acbd2b178f7426b944a1d7f5ad7",
            call_transcript=transcript_text,
            recording_url="dxc03zgurdly9.cloudfront.net/08f45f9bcb1f501b356454ef854715736c4082acb111299d21d81d4eed58c2aa/recording.wav",
            check_in_metadata='{"Dock_release_time": "14:00", "POD_uploaded": true, "Receipts_pending": false, "Final_OSD_confirmed_clean": false}'
        )
        db.add(sample_retell_call)
        db.commit()
        
        print("Successfully added dummy check-in and retell call data.")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

# Removed __main__ block - initialization should only happen through main.py or reinit_db.py 