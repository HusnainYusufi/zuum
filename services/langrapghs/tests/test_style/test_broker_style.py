# """
# Tests for comparing broker output style with real conversation examples using cosine similarity.
# """

# import os
# import sys
# import json
# from pathlib import Path
# from sentence_transformers import SentenceTransformer
# import numpy as np
# from typing import List, Tuple

# current_dir = Path(__file__).parent
# backend_dir = current_dir.parent.parent.parent
# if str(backend_dir) not in sys.path:
#     sys.path.append(str(backend_dir))

# model = SentenceTransformer('all-MiniLM-L6-v2')

# SIMILARITY_THRESHOLD = 0.3

# def get_embedding(text: str) -> np.ndarray:
#     """Get the embedding vector for a given text."""
#     return model.encode(text)

# def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
#     """Calculate cosine similarity between two vectors."""
#     return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# def load_conversations():
#     """Load all conversation threads."""
#     conversations = {}
#     conversation_files = [
#         "test_origin_conversation.json",
#         "test_transit_conversation.json",
#         "test_destination_conversation.json"
#     ]

#     for file in conversation_files:
#         file_path = current_dir.parent / "real_conversations" / file
#         with open(file_path, 'r') as f:
#             data = json.load(f)
#             # Get all broker messages from all threads in this file
#             for conv in data['conversations']:
#                 thread_id = conv['thread_id']
#                 broker_messages = [msg['content'] for msg in conv['messages'] if msg['role'] == 'broker']
#                 conversations[thread_id] = broker_messages

#     return conversations

# def check_similarity_with_corresponding_messages(text: str, conversations: dict, message_index: int) -> Tuple[bool, List[Tuple[float, str]]]:
#     """
#     Check if the text matches the corresponding message from each thread.
#     Returns True if any similarity exceeds threshold, along with all matches.
#     """
#     text_embedding = get_embedding(text)
#     matches = []
#     has_match = False

#     # Check against corresponding message from each thread
#     for thread_id, messages in conversations.items():
#         if message_index < len(messages):
#             example = messages[message_index]
#             example_embedding = get_embedding(example)
#             similarity = cosine_similarity(text_embedding, example_embedding)
#             if similarity >= SIMILARITY_THRESHOLD:
#                 has_match = True
#             matches.append((similarity, example, thread_id))

#     return has_match, matches

# def test_broker_style():
#     """Test broker output style against real conversation examples."""
#     # Load all conversation threads
#     conversations = load_conversations()

#     # Test cases - each corresponds to a specific message index in the conversations
#     test_cases = [
#         # First message in conversations (carrier confirmation request)
#         """Please sign the Carrier Confirmation for load # 295653 to begin your haul""",

#         # Second message in conversations (loading check)
#         """Loaded brother?""",

#         # Third message in conversations (dispatch check)
#         """Are you dispatched?"""
#     ]

#     print("\n=== Starting Broker Style Test ===")
#     total_score = 0

#     for i, test_text in enumerate(test_cases):
#         has_match, matches = check_similarity_with_corresponding_messages(test_text, conversations, i)
#         score = 1 if has_match else 0
#         total_score += score

#         print(f"\nTest case {i+1} (comparing with message {i+1} from each thread):")
#         print(f"Input text: {test_text}")
#         print("\nMatches found:")
#         for similarity, example, thread_id in sorted(matches, key=lambda x: x[0], reverse=True):
#             print(f"\nThread: {thread_id}")
#             print(f"Similarity: {similarity:.2f}")
#             print(f"Example: {example}")
#         print(f"\nFinal score: {score} (matched any corresponding message: {'Yes' if has_match else 'No'})")

#     # Print final results
#     print("\n=== Test Results ===")
#     print(f"Total Score: {total_score}/{len(test_cases)}")
#     print(f"Average Score: {(total_score/len(test_cases))*100:.1f}%")
#     print("\n=== Test Complete ===")

# if __name__ == "__main__":
#     test_broker_style() 
