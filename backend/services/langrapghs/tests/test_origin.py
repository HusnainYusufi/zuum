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
from llm_config import llm
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import evaluate, Client


# examples = [
#     # First message (bot greeting)
#     {
#         "inputs": {"stop_id": 1},  # Empty user input for first message
#         "outputs": {"output": "Hey, just checking—are we confirmed for the pickup at Las Vegas, NV"}  # Expected bot response
#     },
#     # Second turn (carrier confirmation)
#     {
#         "inputs": {"input": "Yes, I have"},  # Carrier response
#         "outputs": {"output": "Great! Did you pickup the load?"}  # Expected bot response
#     },
#     # Third turn (load picked)
#     {
#         "inputs": {"input": "Yes, the load is ready for pickup"},
#         "outputs": {"output": "Perfect! Have you started your journey yet?"}
#     },
#     # Fourth turn (journey started)
#     {
#         "inputs": {"input": "Yes, I'm on my way to the pickup location"},
#         "outputs": {"output": "Thanks for confirming everything. Have a safe journey!"}
#     }
# ]

# client = Client()
# dataset = client.create_dataset("origin-conversation-flow")
# client.create_examples(
#     dataset_id=dataset.id,
#     examples=examples
# )




#    # Define expected responses for each turn
# datasets = {
#         'carrier_confirmation': "ds-carrier-confirmation",
#         'load_picked': "ds-load-picked",
#         'journey_started': "ds-journey-started",
#         'goodbye': "ds-goodbye"
#     }

def test_origin_langgraph():
    # Use the singleton instance
    service = origin_langgraph_service

    # Test the conversation flow
    print("\n=== Starting Origin LangGraph Test ===")
    
    results = service.evaluate('origin-conversation-flow')
    # Print results
    correct_count = sum(1 for r in results if r["correct"])
    print(f"Accuracy: {correct_count}/{len(results)} ({correct_count/len(results)*100:.1f}%)")


    
    # correct_responses = 0
    # total_responses = len(expected_responses)
    
    # # First message - should get carrier confirmation request
    # response = service.run(initial_state, thread_id)
    # print("\nBot:", response)
    # print("Expected:", expected_responses['carrier_confirmation'])
    # is_same = compare_messages(expected_responses['carrier_confirmation'], response)
    # print(f"Same meaning: {'Yes' if is_same else 'No'}")
    # if is_same:
    #     correct_responses += 1
    
    # # Simulate carrier confirmation
    # carrier_response = "Yes, I have"
    # response = service.run(Command(resume={'data': carrier_response}), thread_id)
    # print("\nCarrier:", carrier_response)
    # print("Bot:", response)
    # print("Expected:", expected_responses['load_picked'])
    # is_same = compare_messages(expected_responses['load_picked'], response)
    # print(f"Same meaning: {'Yes' if is_same else 'No'}")
    # if is_same:
    #     correct_responses += 1
    
    # # Simulate load ready response
    # carrier_response = "Yes, the load is ready for pickup"
    # response = service.run(Command(resume={'data': carrier_response}), thread_id)
    # print("\nCarrier:", carrier_response)
    # print("Bot:", response)
    # print("Expected:", expected_responses['journey_started'])
    # is_same = compare_messages(expected_responses['journey_started'], response)
    # print(f"Same meaning: {'Yes' if is_same else 'No'}")
    # if is_same:
    #     correct_responses += 1
    
    # # Simulate journey started response
    # carrier_response = "Yes, I'm on my way to the pickup location"
    # response = service.run(Command(resume={'data': carrier_response}), thread_id)
    # print("\nCarrier:", carrier_response)
    # print("Bot:", response)
    # print("Expected:", expected_responses['goodbye'])
    # is_same = compare_messages(expected_responses['goodbye'], response)
    # print(f"Same meaning: {'Yes' if is_same else 'No'}")
    # if is_same:
    #     correct_responses += 1
    
    # # Print final results
    # print("\n=== Test Results ===")
    # print(f"Total Responses: {total_responses}")
    # print(f"Correct Responses: {correct_responses}")
    # print(f"Accuracy: {(correct_responses/total_responses)*100:.1f}%")
    # print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_origin_langgraph() 