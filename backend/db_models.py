from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
    
# Define model for chat history
class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    stop_id = Column(Integer, index=True)
    user_message = Column(Text)
    bot_message = Column(Text)
    timestamp = Column(String)

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
        
def initialize_database():
    # Create all tables
    create_tables()
    
    # Add some initial test data
    db = SessionLocal()
    try:
        # Check if we already have data
        existing_stops = db.query(Stop).first()
        if not existing_stops:
            # Add sample stop
            sample_stop = Stop(
                id=1,
                name="Test Stop",
                location="Test City, State",
                eta=(datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S"),
                cross_street="Main St & 1st Ave",
                nearest_highway="I-95",
                is_delayed=False
            )
            db.add(sample_stop)
            db.commit()
    finally:
        db.close()

# Initialize the database when this module is imported
initialize_database()