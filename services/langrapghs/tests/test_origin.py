# import os
# import sys
# import json
# from datetime import datetime
# from pathlib import Path
# from sentence_transformers import SentenceTransformer
# import numpy as np
# from rouge_score import rouge_scorer

# # Add the backend directory to Python path
# current_dir = Path(__file__).parent
# backend_dir = current_dir.parent.parent.parent
# if str(backend_dir) not in sys.path:
#     sys.path.append(str(backend_dir))

# from services.langrapghs.origin_langraph import origin_langgraph_service
# from langgraph.types import Command
# from llm_config import llm
# from langchain_core.messages import SystemMessage, HumanMessage

# # Initialize models
# model = SentenceTransformer('all-MiniLM-L6-v2')
# rouge = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# def get_embedding(text: str) -> np.ndarray:
#     """Get the embedding vector for a given text."""
#     return model.encode(text)

# def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
#     """Calculate cosine similarity between two vectors."""
#     return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# def get_rouge_scores(expected: str, actual: str) -> dict:
#     """Calculate Rouge scores between two texts."""
#     scores = rouge.score(expected, actual)
#     return {
#         'rouge1': scores['rouge1'].fmeasure,
#         'rouge2': scores['rouge2'].fmeasure,
#         'rougeL': scores['rougeL'].fmeasure
#     }

# def compare_messages(expected: str, actual: str) -> tuple:
#     """Compare messages using meaning, cosine similarity, and Rouge scores."""
#     # Get meaning comparison
#     prompt = f"""You are a message comparison expert. Your task is to determine if two messages are conveying the same core meaning or intent, even if they use different words.

# Focus on the main purpose of the message, not minor details. For example:
# - If both messages are asking for carrier confirmation or asking if they are ready for pickup, they're the same regardless if one of them is asking for confirmation and the other is asking if they are ready for pickup, or if one is asking for extra information 
# - If both messages are asking if the load is ready, they're the same
# - If both messages are asking if the journey has started or if they are on the road or dispatched, they're the same
# - If both messages are farewell/goodbye messages, they're the same

# Expected message: "{expected}"
# Actual message: "{actual}"

# Are these messages conveying the same core meaning/intent? Answer with only 'yes' or 'no'."""

#     response = llm.invoke([SystemMessage(content=prompt)])
#     meaning_match = response.content.strip().lower() == 'yes'
    
#     # Get cosine similarity
#     expected_embedding = get_embedding(expected)
#     actual_embedding = get_embedding(actual)
#     cos_sim = float(cosine_similarity(expected_embedding, actual_embedding))
    
#     # Get Rouge scores
#     rouge_scores = get_rouge_scores(expected, actual)
    
#     # Calculate combined score (weighted average)
#     combined_score = float(
#         0.4 * cos_sim +  # Cosine similarity weight
#         0.3 * rouge_scores['rougeL'] +  # Rouge-L weight
#         0.3 * (1.0 if meaning_match else 0.0)  # Meaning match weight
#     )
    
#     return meaning_match, cos_sim, rouge_scores, combined_score

# def load_conversations():
#     conversations_file = current_dir.parent / 'tests' / 'real_conversations' / "test_origin_conversation.json"
#     with open(conversations_file, 'r') as f:
#         return json.load(f)['conversations']

# def test_origin_langgraph():
#     # Use the singleton instance
#     service = origin_langgraph_service
    
#     # Load test conversations
#     conversations = load_conversations()
    
#     # Test each conversation thread
#     print("\n=== Starting Origin LangGraph Test ===")
    
#     total_scores = {
#         'meaning': 0,
#         'cosine': 0,
#         'rouge': 0,
#         'combined': 0
#     }
#     total_responses = 0
#     conversation_results = []
    
#     for conversation in conversations:
#         thread_id = conversation['thread_id']
#         messages = conversation['messages']
#         thread_results = {
#             'thread_id': thread_id,
#             'responses': []
#         }
        
#         print(f"\nTesting conversation thread: {thread_id}")
        
#         # Create initial state
#         initial_state = {
#             "messages": [],
#             "stop_id": 1,
#             "running": True,
#             "load_number": "lb_201"
#         }
        
#         # First message - should get carrier confirmation request
#         response = service.run(initial_state, thread_id)
#         expected = messages[0]['content']  # First broker message
#         print("\nBot:", response)
#         print("Expected:", expected)
        
#         meaning_match, cos_sim, rouge_scores, combined_score = compare_messages(expected, response)
#         print(f"Meaning Match: {'Yes' if meaning_match else 'No'}")
#         print(f"Cosine Similarity: {cos_sim:.2f}")
#         print(f"Rouge Scores:")
#         print(f"  Rouge-1: {rouge_scores['rouge1']:.2f}")
#         print(f"  Rouge-2: {rouge_scores['rouge2']:.2f}")
#         print(f"  Rouge-L: {rouge_scores['rougeL']:.2f}")
#         print(f"Combined Score: {combined_score:.2f}")
        
#         thread_results['responses'].append({
#             'expected': expected,
#             'actual': response,
#             'meaning_match': meaning_match,
#             'cosine_similarity': cos_sim,
#             'rouge_scores': rouge_scores,
#             'combined_score': combined_score
#         })
        
#         if meaning_match:
#             total_scores['meaning'] += 1
#         if cos_sim >= 0.7:  # Threshold for cosine similarity
#             total_scores['cosine'] += 1
#         if rouge_scores['rougeL'] >= 0.7:  # Threshold for Rouge score
#             total_scores['rouge'] += 1
#         if combined_score >= 0.7:  # Threshold for combined score
#             total_scores['combined'] += 1
#         total_responses += 1
        
#         # Simulate each trucker response and verify broker's next message
#         for i in range(1, len(messages), 2):
#             if i + 1 < len(messages):  # Ensure we have a broker message to compare against
#                 trucker_response = messages[i]['content']
#                 expected_broker = messages[i + 1]['content']
                
#                 response = service.run(Command(resume={'data': trucker_response}), thread_id)
#                 print("\nTrucker:", trucker_response)
#                 print("Bot:", response)
#                 print("Expected:", expected_broker)
                
#                 meaning_match, cos_sim, rouge_scores, combined_score = compare_messages(expected_broker, response)
#                 print(f"Meaning Match: {'Yes' if meaning_match else 'No'}")
#                 print(f"Cosine Similarity: {cos_sim:.2f}")
#                 print(f"Rouge Scores:")
#                 print(f"  Rouge-1: {rouge_scores['rouge1']:.2f}")
#                 print(f"  Rouge-2: {rouge_scores['rouge2']:.2f}")
#                 print(f"  Rouge-L: {rouge_scores['rougeL']:.2f}")
#                 print(f"Combined Score: {combined_score:.2f}")
                
#                 thread_results['responses'].append({
#                     'trucker_input': trucker_response,
#                     'expected': expected_broker,
#                     'actual': response,
#                     'meaning_match': meaning_match,
#                     'cosine_similarity': cos_sim,
#                     'rouge_scores': rouge_scores,
#                     'combined_score': combined_score
#                 })
                
#                 if meaning_match:
#                     total_scores['meaning'] += 1
#                 if cos_sim >= 0.7:
#                     total_scores['cosine'] += 1
#                 if rouge_scores['rougeL'] >= 0.7:
#                     total_scores['rouge'] += 1
#                 if combined_score >= 0.7:
#                     total_scores['combined'] += 1
#                 total_responses += 1
        
#         conversation_results.append(thread_results)
    
#     # Print final results
#     print("\n=== Test Results ===")
#     print(f"Total Responses: {total_responses}")
#     print(f"Meaning Match Score: {total_scores['meaning']}/{total_responses}")
#     print(f"Cosine Similarity Score: {total_scores['cosine']}/{total_responses}")
#     print(f"Rouge Score: {total_scores['rouge']}/{total_responses}")
#     print(f"Combined Score: {total_scores['combined']}/{total_responses}")
#     print("\n=== Test Complete ===")
    
#     # Return results as JSON object
#     return {
#         'test_name': 'origin',
#         'total_responses': total_responses,
#         'scores': {
#             'meaning': {
#                 'passed': total_scores['meaning'],
#                 'total': total_responses,
#                 'percentage': (total_scores['meaning'] / total_responses * 100) if total_responses > 0 else 0
#             },
#             'cosine': {
#                 'passed': total_scores['cosine'],
#                 'total': total_responses,
#                 'percentage': (total_scores['cosine'] / total_responses * 100) if total_responses > 0 else 0
#             },
#             'rouge': {
#                 'passed': total_scores['rouge'],
#                 'total': total_responses,
#                 'percentage': (total_scores['rouge'] / total_responses * 100) if total_responses > 0 else 0
#             },
#             'combined': {
#                 'passed': total_scores['combined'],
#                 'total': total_responses,
#                 'percentage': (total_scores['combined'] / total_responses * 100) if total_responses > 0 else 0
#             }
#         },
#         'conversation_results': conversation_results
#     }

# if __name__ == "__main__":
#     test_origin_langgraph() 