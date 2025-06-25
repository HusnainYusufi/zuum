from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import os
from pathlib import Path
import json

# Get the absolute path to the database file
current_dir = Path(__file__).parent
db_path = os.path.join(current_dir, 'transit.db')

# Create SQLite database engine with absolute path
engine = create_engine(f'sqlite:///{db_path}')
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define Stop model
class Stop(Base):
    __tablename__ = "stops"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String)  # City and state
    eta = Column(String)
    cross_street = Column(String)
    nearest_highway = Column(String)
    is_delayed = Column(Boolean, default=False)
    delay_reason = Column(String)
    expected_location = Column(String)
    reported_location = Column(String)
    is_origin = Column(Boolean, default=False)
    is_destination = Column(Boolean, default=False)
    

# Define an Enum for Journey states
import enum
class JourneyState(enum.Enum):
    ORIGIN = 0
    TRANSIT = 1
    DESTINATION = 2

class Journey(Base):
    __tablename__ = "journeys"
    
    id = Column(Integer, primary_key=True, index=True)
    # Store stop_ids as a JSON string instead of ARRAY since SQLite doesn't support ARRAY
    stop_ids_json = Column(Text)
    current_state = Column(Integer)
    
    @property
    def stop_ids(self):
        """Get the stop IDs as a list"""
        if self.stop_ids_json:
            return json.loads(self.stop_ids_json)
        return []
    
    @stop_ids.setter
    def stop_ids(self, value):
        """Set the stop IDs as a JSON string"""
        if value is not None:
            self.stop_ids_json = json.dumps(value)
        else:
            self.stop_ids_json = None

# Model for storing notifications
class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    timestamp = Column(String, nullable=False)
    stop_id = Column(Integer, nullable=True)
    severity = Column(String, default="info")
    read = Column(Boolean, default=False)
    
class CheckIn(Base):
    __tablename__ = "check_ins"
    
    id = Column(Integer, primary_key=True, index=True)
    stop_id = Column(Integer, ForeignKey('stops.id'), index=True)
    load_id = Column(Text)
    query = Column(Text)
    AI_Response_Summary = Column(Text)
    AI_Timestamp = Column(String)
    Issue_Flagged = Column(Boolean, default=False)
    Exception_Type = Column(String)
    Call_confidence_score = Column(String)
    call_trasfered = Column(Boolean, default=False)
    Tags = Column(String)
    miles = Column(String)  # Add miles field
    # Define relationship to Stop
    stop = relationship("Stop", backref="check_ins")
    is_active = Column(Boolean, default=True)

class RetellCall(Base):
    __tablename__ = "retell_calls"
    
    id = Column(Integer, primary_key=True, index=True)
    check_in_id = Column(Integer, ForeignKey('check_ins.id'), index=True)
    call_id = Column(String)
    call_transcript = Column(Text)
    recording_url = Column(String)
    check_in = relationship("CheckIn", backref="retell_calls")
    check_in_metadata = Column(String)
    call_status = Column(String, default="in_progress")  # in_progress, completed, failed

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    feedback_type = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    user_email = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    
    # Relationship to feedback images
    images = relationship("FeedbackImage", back_populates="feedback", cascade="all, delete-orphan")

class FeedbackImage(Base):
    __tablename__ = "feedback_images"
    
    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey('feedback.id'), index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(String, default=lambda: datetime.now().isoformat())
    
    # Relationship back to feedback
    feedback = relationship("Feedback", back_populates="images")

# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Function to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 
# All database initialization is handled in init_db.py