#!/usr/bin/env python3
"""
Script to create test check-in data for testing the checkin dashboard.
Run this script to populate the database with sample check-in data.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from db_models import SessionLocal, CheckIn, RetellCall, Stop
from loguru import logger

def create_test_stops():
    """Create test stops if they don't exist"""
    db = SessionLocal()
    try:
        # Check if we already have stops
        existing_stops = db.query(Stop).count()
        if existing_stops > 0:
            logger.info(f"Found {existing_stops} existing stops")
            return
        
        # Create test stops
        test_stops = [
            {"name": "Origin Warehouse", "location": "Los Angeles, CA", "is_origin": True},
            {"name": "Transit Hub", "location": "Phoenix, AZ"},
            {"name": "Destination Center", "location": "Dallas, TX", "is_destination": True},
            {"name": "Pickup Point", "location": "San Diego, CA", "is_origin": True},
            {"name": "Delivery Hub", "location": "Houston, TX", "is_destination": True},
        ]
        
        for stop_data in test_stops:
            stop = Stop(**stop_data)
            db.add(stop)
        
        db.commit()
        logger.info(f"Created {len(test_stops)} test stops")
        
    except Exception as e:
        logger.error(f"Error creating test stops: {e}")
        db.rollback()
    finally:
        db.close()

def create_test_checkins():
    """Create test check-in data with various scenarios"""
    db = SessionLocal()
    try:
        # Check if we already have check-ins
        existing_checkins = db.query(CheckIn).count()
        if existing_checkins > 50:
            logger.info(f"Already have {existing_checkins} check-ins, skipping creation")
            return
        
        # Get available stops
        stops = db.query(Stop).all()
        if not stops:
            logger.error("No stops found. Please create stops first.")
            return
        
        # Sample AI summaries and tags
        ai_summaries = [
            "Driver confirmed arrival at pickup location. Load ready for pickup at dock 5.",
            "Completed pickup successfully. ETA to destination updated to 3:30 PM tomorrow.",
            "Currently in transit, passing through Phoenix, AZ. No delays expected.",
            "Arrived at destination. Waiting for dock assignment.",
            "Delivery completed successfully. POD uploaded to system.",
            "Minor delay due to traffic. ETA updated by 45 minutes.",
            "Equipment issue reported. Maintenance team notified.",
            "Driver requests lumper service at destination.",
            "Load secured and ready for transport. All paperwork verified.",
            "Fuel stop completed. Continuing to destination as scheduled.",
            "Weather delay in Denver area. Will update ETA once conditions improve.",
            "Driver confirmed DOT inspection passed. Continuing journey.",
            "Arrived early at pickup. Waiting for appointment time.",
            "Scale weight confirmed within limits. Proceeding to destination.",
            "Driver reports load shifted. Securing load before continuing.",
        ]
        
        tags_options = [
            "priority,urgent",
            "standard",
            "delayed",
            "equipment-issue",
            "weather-delay",
            "early-arrival",
            "lumper-required",
            "dot-inspection",
            "fuel-stop",
            "load-secured",
            "paperwork-verified",
            "traffic-delay",
            "maintenance-needed",
            "on-schedule",
            "completed",
        ]
        
        exception_types = [
            None, None, None, None,  # Most check-ins have no exceptions
            "Traffic Delay",
            "Equipment Issue", 
            "Weather Delay",
            "Documentation Issue",
            "Fuel Emergency",
            "DOT Inspection",
        ]
        
        # Create check-ins for the last 60 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        created_count = 0
        for day_offset in range(60):
            current_date = start_date + timedelta(days=day_offset)
            
            # Create 1-5 check-ins per day (more recent days have more check-ins)
            daily_checkins = random.randint(1, min(5, max(1, day_offset // 10)))
            
            for _ in range(daily_checkins):
                # Random time during the day
                random_hour = random.randint(6, 22)
                random_minute = random.randint(0, 59)
                checkin_time = current_date.replace(hour=random_hour, minute=random_minute)
                
                # Random stop
                stop = random.choice(stops)
                
                # Random data
                summary = random.choice(ai_summaries)
                tags = random.choice(tags_options)
                exception_type = random.choice(exception_types)
                
                # Issue and review flags (more likely for exceptions)
                issue_flagged = exception_type is not None or random.random() < 0.15
                requires_review = issue_flagged or random.random() < 0.25
                
                # Confidence score
                confidence_score = f"{random.randint(75, 99)}.{random.randint(10, 99)}"
                
                # Create check-in
                checkin = CheckIn(
                    stop_id=stop.id,
                    load_id=f"LOAD-{random.randint(1000, 9999)}",
                    query=f"Driver check-in call for {stop.name}",
                    AI_Response_Summary=summary,
                    AI_Timestamp=checkin_time.isoformat(),
                    Issue_Flagged=issue_flagged,
                    Exception_Type=exception_type,
                    Call_confidence_score=confidence_score,
                    call_trasfered=True,
                    Tags=tags,
                    miles=str(random.randint(50, 1200)),
                    is_active=False
                )
                
                db.add(checkin)
                db.flush()  # Get the ID
                
                # Create associated RetellCall
                retell_call = RetellCall(
                    check_in_id=checkin.id,
                    call_id=f"call_{random.randint(100000, 999999)}",
                    call_transcript=f"Test transcript for check-in {checkin.id}",
                    recording_url=f"https://example.com/recording_{checkin.id}.mp3",
                    call_status="completed"
                )
                
                db.add(retell_call)
                created_count += 1
        
        db.commit()
        logger.info(f"Created {created_count} test check-ins")
        
        # Show some statistics
        total_checkins = db.query(CheckIn).count()
        total_issues = db.query(CheckIn).filter(CheckIn.Issue_Flagged == True).count()
        total_reviews = db.query(CheckIn).filter(CheckIn.Requires_Human_Review == True).count()
        
        logger.info(f"Database now contains:")
        logger.info(f"  - {total_checkins} total check-ins")
        logger.info(f"  - {total_issues} issues flagged")
        logger.info(f"  - {total_reviews} requiring human review")
        
    except Exception as e:
        logger.error(f"Error creating test check-ins: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Main function to create test data"""
    logger.info("Creating test data for checkin dashboard...")
    
    try:
        # Create test stops first
        create_test_stops()
        
        # Create test check-ins
        create_test_checkins()
        
        logger.info("Test data creation completed successfully!")
        logger.info("You can now visit /checkin-dashboard to see the dashboard with test data.")
        
    except Exception as e:
        logger.error(f"Error creating test data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 