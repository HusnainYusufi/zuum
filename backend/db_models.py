from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create SQLite database engine
engine = create_engine('sqlite:///transit.db')
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
    
# Define model for chat history
class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    stop_id = Column(Integer, index=True)
    user_message = Column(Text)
    bot_message = Column(Text)
    timestamp = Column(String)
    
    

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