#!/usr/bin/env python3
"""
Script to create a test check-in with empty call data for testing the call progress system.
This simulates the initial state when a check-in is created but the Retell call hasn't completed yet.
"""

import sys
import uuid
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from pathlib import Path
import os

# Add the current directory to the path so we can import our models
sys.path.append(str(Path(__file__).parent))

from db_models import CheckIn, RetellCall, get_db

def create_test_checkin():
    """Create a test check-in with empty call data"""
    
    # Get database session
    db = next(get_db())
    
    try:
        # Generate a unique call ID for testing
        test_call_id = f"test_call_{uuid.uuid4().hex[:8]}"
        
        print(f"Creating test check-in with call_id: {test_call_id}")
        
        # Create a new empty check-in
        new_checkin = CheckIn(
            stop_id=None,  # Optional as per the updated model
            load_id=f"LOAD_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            query=None,
            AI_Response_Summary=None,
            AI_Timestamp=datetime.now().isoformat(),
            Issue_Flagged=False,
            Exception_Type=None,
            Call_confidence_score=None,
            Requires_Human_Review=False,
            Tags=None,
            miles=None
        )
        
        # Add to database and flush to get the ID
        db.add(new_checkin)
        db.flush()
        
        print(f"✅ Created check-in with ID: {new_checkin.id}")
        
        # Create associated RetellCall with "in_progress" status
        new_retell_call = RetellCall(
            check_in_id=new_checkin.id,
            call_id=test_call_id,
            call_transcript=None,  # Empty - simulates call in progress
            recording_url=None,    # Empty - simulates call in progress
            check_in_metadata=None, # Empty - simulates call in progress
            call_status="in_progress"  # This will trigger the progress overlay
        )
        
        db.add(new_retell_call)
        db.commit()
        
        print(f"✅ Created RetellCall with call_id: {test_call_id}")
        print(f"✅ Call status set to: in_progress")
        print(f"\n🔗 Test URL: http://localhost:8000/checkin/{new_checkin.id}")
        print(f"📱 This check-in will show the 'Call in Progress' overlay")
        print(f"\n💡 To simulate call completion, you can run:")
        print(f"   python simulate_call_completion.py {new_checkin.id}")
        
        return new_checkin.id, test_call_id
        
    except Exception as e:
        print(f"❌ Error creating test check-in: {e}")
        db.rollback()
        return None, None
    finally:
        db.close()

def create_multiple_test_checkins(count=3):
    """Create multiple test check-ins for testing"""
    print(f"Creating {count} test check-ins...\n")
    
    created_checkins = []
    for i in range(count):
        print(f"Creating test check-in {i+1}/{count}:")
        checkin_id, call_id = create_test_checkin()
        if checkin_id:
            created_checkins.append((checkin_id, call_id))
        print("-" * 50)
    
    if created_checkins:
        print(f"\n🎉 Successfully created {len(created_checkins)} test check-ins:")
        for checkin_id, call_id in created_checkins:
            print(f"   • Check-in #{checkin_id} - Call ID: {call_id}")
        
        print(f"\n🌐 Test URLs:")
        for checkin_id, _ in created_checkins:
            print(f"   • http://localhost:8000/checkin/{checkin_id}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create test check-ins with empty call data")
    parser.add_argument("--count", "-c", type=int, default=1, 
                       help="Number of test check-ins to create (default: 1)")
    parser.add_argument("--multiple", "-m", action="store_true",
                       help="Create 3 test check-ins at once")
    
    args = parser.parse_args()
    
    if args.multiple:
        create_multiple_test_checkins(3)
    elif args.count > 1:
        create_multiple_test_checkins(args.count)
    else:
        create_test_checkin() 