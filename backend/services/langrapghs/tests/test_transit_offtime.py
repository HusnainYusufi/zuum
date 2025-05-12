import os
import sys
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from services.langrapghs.transit_langrapgh_service import transit_langgraph_service
from langgraph.types import Command
from llm_config import llm
from langchain_core.messages import SystemMessage, HumanMessage

def compare_messages(expected: str, actual: str) -> bool:
    prompt = f"""You are a message comparison expert. Your task is to determine if two messages are conveying the same core meaning or intent, even if they use different words.

Focus on the main purpose of the message, not minor details. For example:
- If both messages are asking for location, they're the same
- If both messages are asking for ETA, they're the same
- If both messages are farewell/goodbye messages, they're the same
- If both messages are asking about delays, they're the same

Expected message: "{expected}"
Actual message: "{actual}"

Are these messages conveying the same core meaning/intent? Answer with only 'yes' or 'no'."""

    response = llm.invoke([SystemMessage(content=prompt)])
    return response.content.strip().lower() == 'yes'

def test_transit_langgraph():
    # Use the singleton instance instead of creating a new one
    service = transit_langgraph_service
    
    # Create initial state
    initial_state = {
        "messages": [],
        "stop_id": 1,  # Using a test stop ID
        "running": True
    }
    
    # Generate a unique thread ID
    thread_id = "test_thread_1"
    
    # Test the conversation flow
    print("\n=== Starting Transit LangGraph Test ===")
    
    # Define expected responses for each turn
    expected_responses = {
        'greeting': "Hello! Support agent here. Can you tell me where you are right now and your estimated time of arrival?",
        'location_eta': "Thanks for the update! Just curious, what caused the delay on your route?",
        'delay': "Got it, thanks for letting me know! Could you also tell me where the nearest highway exit is?",
        'highway': "Thanks for the info! Safe travels on I-45, and see you soon at your destination!"
    }
    
    correct_responses = 0
    total_responses = len(expected_responses)
    
    # First message - should get a greeting and location/ETA request
    response = service.run(initial_state, thread_id)
    print("\nBot:", response)
    print("Expected:", expected_responses['greeting'])
    is_same = compare_messages(expected_responses['greeting'], response)
    print(f"Same meaning: {'Yes' if is_same else 'No'}")
    if is_same:
        correct_responses += 1
    
    # Simulate driver response with location
    driver_response = "I'm currently in Houston, TX and will arrive in 30 minutes"
    response = service.run(Command(resume={'data': driver_response}), thread_id)
    print("\nDriver:", driver_response)
    print("Bot:", response)
    print("Expected:", expected_responses['location_eta'])
    is_same = compare_messages(expected_responses['location_eta'], response)
    print(f"Same meaning: {'Yes' if is_same else 'No'}")
    if is_same:
        correct_responses += 1
    
    # Simulate driver response with delay
    driver_response = "Actually, I'm running about 15 minutes behind due to traffic"
    response = service.run(Command(resume={'data': driver_response}), thread_id)
    print("\nDriver:", driver_response)
    print("Bot:", response)
    print("Expected:", expected_responses['delay'])
    is_same = compare_messages(expected_responses['delay'], response)
    print(f"Same meaning: {'Yes' if is_same else 'No'}")
    if is_same:
        correct_responses += 1
    
    # Simulate driver response with highway info
    driver_response = "I'm on I-45 near exit 72"
    response = service.run(Command(resume={'data': driver_response}), thread_id)
    print("\nDriver:", driver_response)
    print("Bot:", response)
    print("Expected:", expected_responses['highway'])
    is_same = compare_messages(expected_responses['highway'], response)
    print(f"Same meaning: {'Yes' if is_same else 'No'}")
    if is_same:
        correct_responses += 1
    
    # Print final results
    print("\n=== Test Results ===")
    print(f"Total Responses: {total_responses}")
    print(f"Correct Responses: {correct_responses}")
    print(f"Accuracy: {(correct_responses/total_responses)*100:.1f}%")
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_transit_langgraph()