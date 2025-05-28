import os
import sys
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from services.langrapghs.destination_langrapgh_service import destination_langgraph_service
from langgraph.types import Command
from llm_config import llm
from langchain_core.messages import SystemMessage, HumanMessage

def compare_messages(expected: str, actual: str) -> bool:
    prompt = f"""You are a message comparison expert. Your task is to determine if two messages are conveying the same core meaning or intent, even if they use different words.

Focus on the main purpose of the message, not minor details. For example:
- If both messages are asking for arrival confirmation, they're the same
- If both messages are asking for POD signature, they're the same
- If both messages are farewell/goodbye messages, they're the same

Expected message: "{expected}"
Actual message: "{actual}"

Are these messages conveying the same core meaning/intent? Answer with only 'yes' or 'no'."""

    response = llm.invoke([SystemMessage(content=prompt)])
    return response.content.strip().lower() == 'yes'

def test_destination_langgraph():
    # Use the singleton instance
    service = destination_langgraph_service
    
    # Create initial state
    initial_state = {
        "messages": [],
        "stop_id": 1,  # Using a test stop ID
        "running": True
    }
    
    # Generate a unique thread ID
    thread_id = "test_thread_1"
    
    # Test the conversation flow
    print("\n=== Starting Destination LangGraph Test ===")
    
    # Define expected responses for each turn
    expected_responses = {
        'load_number': "Hello! What is the load number?",
        'arrival_confirmation': "Have you arrived at the destination?",
        'pod_signature': "Great! Have you received the POD signature?",
        'goodbye': "Perfect! Thank you for completing the delivery. Have a safe journey!"
    }
    
    correct_responses = 0
    total_responses = len(expected_responses)
    
    response = service.run(initial_state, thread_id)
    print("\nBot:", response)
    print("Expected:", expected_responses['load_number'])
    is_same = compare_messages(expected_responses['load_number'], response)
    print(f"Same meaning: {'Yes' if is_same else 'No'}")
    if is_same:
        correct_responses += 1
    
    # First message - should get arrival confirmation request
    response = service.run(initial_state, thread_id)
    print("\nBot:", response)
    print("Expected:", expected_responses['arrival_confirmation'])
    is_same = compare_messages(expected_responses['arrival_confirmation'], response)
    print(f"Same meaning: {'Yes' if is_same else 'No'}")
    if is_same:
        correct_responses += 1
    
    # Simulate arrival confirmation
    driver_response = "Yes, I have arrived at the destination"
    response = service.run(Command(resume={'data': driver_response}), thread_id)
    print("\nDriver:", driver_response)
    print("Bot:", response)
    print("Expected:", expected_responses['pod_signature'])
    is_same = compare_messages(expected_responses['pod_signature'], response)
    print(f"Same meaning: {'Yes' if is_same else 'No'}")
    if is_same:
        correct_responses += 1
    
    # Simulate POD signature confirmation
    driver_response = "Yes, I have received the POD signature"
    response = service.run(Command(resume={'data': driver_response}), thread_id)
    print("\nDriver:", driver_response)
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
    
    # Return the metrics for API consumption
    return {
        "total_responses": total_responses,
        "correct_responses": correct_responses,
        "accuracy": f"{(correct_responses/total_responses)*100:.1f}%"
    }

if __name__ == "__main__":
    test_destination_langgraph() 