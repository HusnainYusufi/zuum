import os
import sys
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from services.langrapghs.origin_langraph import origin_langgraph_service
from langgraph.types import Command
from llm_config import llm
from langchain_core.messages import SystemMessage, HumanMessage

def compare_messages(expected: str, actual: str) -> bool:
    prompt = f"""You are a message comparison expert. Your task is to determine if two messages are conveying the same core meaning or intent, even if they use different words.

Focus on the main purpose of the message, not minor details. For example:
- If both messages are asking for carrier confirmation, they're the same
- If both messages are asking if the load is ready, they're the same
- If both messages are asking if the journey has started, they're the same
- If both messages are farewell/goodbye messages, they're the same

Expected message: "{expected}"
Actual message: "{actual}"

Are these messages conveying the same core meaning/intent? Answer with only 'yes' or 'no'."""

    response = llm.invoke([SystemMessage(content=prompt)])
    return response.content.strip().lower() == 'yes'

def test_origin_langgraph():
    # Use the singleton instance
    service = origin_langgraph_service
    
    # Create initial state
    initial_state = {
        "messages": [],
        "stop_id": 1,  # Using a test stop ID
        "running": True
    }
    
    # Generate a unique thread ID
    thread_id = "test_thread_1"
    
    # Test the conversation flow
    print("\n=== Starting Origin LangGraph Test ===")
    
    # Define expected responses for each turn
    expected_responses = {
        'carrier_confirmation': "Hey, just checking—are we confirmed for the pickup at Las Vegas, NV",
        'load_picked': "Great! Did you pickup the load?",
        'journey_started': "Perfect! Have you started your journey yet?",
        'goodbye': "Thanks for confirming everything. Have a safe journey!"
    }
    
    correct_responses = 0
    total_responses = len(expected_responses)
    
    # First message - should get carrier confirmation request
    response = service.run(initial_state, thread_id)
    print("\nBot:", response)
    print("Expected:", expected_responses['carrier_confirmation'])
    is_same = compare_messages(expected_responses['carrier_confirmation'], response)
    print(f"Same meaning: {'Yes' if is_same else 'No'}")
    if is_same:
        correct_responses += 1
    
    # Simulate carrier confirmation
    carrier_response = "Yes, I have"
    response = service.run(Command(resume={'data': carrier_response}), thread_id)
    print("\nCarrier:", carrier_response)
    print("Bot:", response)
    print("Expected:", expected_responses['load_picked'])
    is_same = compare_messages(expected_responses['load_picked'], response)
    print(f"Same meaning: {'Yes' if is_same else 'No'}")
    if is_same:
        correct_responses += 1
    
    # Simulate load ready response
    carrier_response = "Yes, the load is ready for pickup"
    response = service.run(Command(resume={'data': carrier_response}), thread_id)
    print("\nCarrier:", carrier_response)
    print("Bot:", response)
    print("Expected:", expected_responses['journey_started'])
    is_same = compare_messages(expected_responses['journey_started'], response)
    print(f"Same meaning: {'Yes' if is_same else 'No'}")
    if is_same:
        correct_responses += 1
    
    # Simulate journey started response
    carrier_response = "Yes, I'm on my way to the pickup location"
    response = service.run(Command(resume={'data': carrier_response}), thread_id)
    print("\nCarrier:", carrier_response)
    print("Bot:", response)
    print("Expected:", expected_responses['goodbye'])
    is_same = compare_messages(expected_responses['goodbye'], response)
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
    test_origin_langgraph() 