# %%
import os
from typing import Annotated, TypedDict, Literal, Optional, List, Dict
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt
from langgraph.graph.message import add_messages

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from langgraph.checkpoint.memory import MemorySaver

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


# %%
llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

template = """When asked to ask the user a question, respond with only the question itself, without any additional text or context.

When asked to say goodbye to the user, respond with only a goodbye message.


More instructions:
- Do not add sure to your response.
- Do not add any additional text or context to your response.
- Do not add any additional questions to your response.

For all other interactions:
Your job is to get information from a user about what type of prompt template they want to create.
"""


# %%
def get_messages_info(messages):
    return [SystemMessage(content=template)] + messages

# 1. Define a simplified driver state structure
class DriverState(TypedDict):
    carrier_confirmed: bool
    ask_carrier_confirmed: bool
    messages: Annotated[list, add_messages]
    isRunning: Optional[bool] = None
    current_query: Optional[str] = None
    departed: bool
    ask_departed: bool

def ask_courier_confirmation(state: DriverState):
    'Ask if the courier has confirmed the pickup.'
    LLM_query = llm.invoke(get_messages_info(['Ask if the courier has confirmed the pickup.']))
    print(LLM_query.content)
    return {**state, "ask_carrier_confirmed": True, "current_query": LLM_query.content}


def get_courier_confirmation(state: DriverState):
    'Get the courier confirmation from the user.'

    print("get_courier_confirmation")

    human_response = interrupt({"query": state["current_query"]})

    # print(human_response)
    # courier_confirmation = human_response["data"]

    msg = llm.invoke(f'''See the user prompt and check if there is a courier confirmation 
                     Conditons:
                     - If there is a courier confirmation and it is yes, return True
                     - If there is no courier confirmation or the courier confirmation is not yes, return False
                     
                     User prompt: {human_response}''')
    
    logger.debug(msg.content)
    
    if 'True' in msg.content:
        return {
             **state,
            "messages": [*state["messages"], state["current_query"], HumanMessage(content=human_response)],
            "carrier_confirmed": True
        }
    else:
        return {
             **state,
            "messages": [*state["messages"], state["current_query"], HumanMessage(content=human_response)],
            "carrier_confirmed": False
        }

    
def goodBye(state: DriverState):
    'Say good bye to the user.'
    msg = llm.invoke('Say good bye to the user.')
    print(msg.content)
    return {**state, "isRunning": False}

def origin(state: DriverState):
    return state
    
def ask_departed(state: DriverState):
    LLM_query = llm.invoke(get_messages_info(['Ask if the courier has departed.']))
    print(LLM_query.content)
    return {**state, "ask_departed": True, "current_query": LLM_query.content}

def get_departed(state: DriverState):
    human_response = interrupt({"query": state["current_query"]})
    # print(human_response)
    # return {**state, "messages": [*state["messages"], state["current_query"], HumanMessage(content=human_response)], "departed": True}

    msg = llm.invoke(f'''See the user prompt and check if courier has departed
                     Conditons:
                     - If courier has departed and it is yes, return True
                     - If courier has not departed or the courier has departed is not yes, return False
                     
                     User prompt: {human_response}''')
    
    logger.debug(msg.content)
    
    if 'True' in msg.content:
        return {
             **state,
            "messages": [*state["messages"], state["current_query"], HumanMessage(content=human_response)],
            "departed": True
        }
    else:
        return {
             **state,
            "messages": [*state["messages"], state["current_query"], HumanMessage(content=human_response)],
            "departed": False
        }

def origin_router(state: DriverState):
    if not state["ask_carrier_confirmed"]:    
        return "ask_courier_confirmation"
    elif not state["carrier_confirmed"]:
        return "get_courier_confirmation"
    elif not state["ask_departed"]:
        return "ask_departed_node"
    elif not state["departed"]:
        return "get_departed_node"
    else:
        return "goodBye"


# %%
# 3. Build the graph
def build_driver_graph():
    graph_builder = StateGraph(DriverState)
    
    # Add all the nodes
    graph_builder.add_node("origin", origin)
    graph_builder.add_node("ask_courier_confirmation", ask_courier_confirmation)
    graph_builder.add_node("get_courier_confirmation", get_courier_confirmation)
    graph_builder.add_node("ask_departed_node", ask_departed)
    graph_builder.add_node("get_departed_node", get_departed)
    graph_builder.add_node("goodBye", goodBye)

    graph_builder.add_edge(START, "origin")

    graph_builder.add_conditional_edges(
        "origin",
        origin_router,
        {
            "ask_courier_confirmation": "ask_courier_confirmation",
            "get_courier_confirmation": "get_courier_confirmation",
            "ask_departed_node": "ask_departed_node",
            "get_departed_node": "get_departed_node",
            "goodBye": "goodBye"
        }
        
    )    

    # graph_builder.add_edge("ask_courier_confirmation", "get_courier_confirmation")
    graph_builder.add_edge("get_courier_confirmation", "goodBye")
    graph_builder.add_edge("goodBye", END)

    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)

    return graph


# %% [markdown]
# # Running the Graph

# %%
state = {
    "carrier_confirmed": False,
    "ask_carrier_confirmed": False,
    "ask_departed": False,
    "departed": False,
    "messages": [HumanMessage(content="Hello, how are you?")],
    "current_query": None
}

driver_graph = build_driver_graph()

# %%
# result = driver_graph.invoke(state, config = {"configurable": {"thread_id": "1"}})
# # state = process_driver_flow(state)

# result

# # %%
# for event in driver_graph.stream(result, config = {"configurable": {"thread_id": "1"}}):
#     print(event)
#     print()

# # %%
# thread = {"configurable": {"thread_id": "1"}}

# for event in driver_graph.stream(
#     Command(resume="yes"), 
#     config = thread
# ):
#     print(event)
#     print()

# # %%
# state = driver_graph.get_state(thread).values
# state

# # %%
# for event in driver_graph.stream(
#     state,
#     config = thread
# ):
#     print(event)
#     print()

# # %%
# state = driver_graph.get_state(thread).values
# state

# # %%
# for event in driver_graph.stream(
#     state,
#     config = thread
# ):
#     print(event)
#     print()

# # %%
# thread = {"configurable": {"thread_id": "1"}}

# for event in driver_graph.stream(
#     Command(resume="no"), 
#     config = thread
# ):
#     print(event)
#     print()

# # %%
# state = driver_graph.get_state(thread).values
# state

# # %%
# for event in driver_graph.stream(
#     state,
#     config = thread
# ):
#     print(event)
#     print()

# # %%
# from IPython.display import Image, display

# try:
#     display(Image(driver_graph.get_graph().draw_mermaid_png()))
# except Exception:
#     # This requires some extra dependencies and is optional
#     pass

# %% [markdown]
# # Utility functions

# %%
def format_response(response, state: DriverState):
    """Format the response for the UI"""
    message = ""
    
    # Log the exact response for debugging
    logger.debug(f"Raw response type: {type(response)}")
    logger.debug(f"Raw response: {response}")
    
    try:
        # Handle dictionary responses
        if isinstance(response, dict):
            # Handle interrupt messages
            if '__interrupt__' in response:
                interrupt_tuple = response['__interrupt__']
                if isinstance(interrupt_tuple, tuple) and len(interrupt_tuple) > 0:
                    interrupt_obj = interrupt_tuple[0]
                    if hasattr(interrupt_obj, 'value') and isinstance(interrupt_obj.value, dict):
                        message = interrupt_obj.value.get('query', '')
                        logger.debug(f"Extracted query from interrupt: {message}")
            # Handle goodbye messages
            elif 'goodBye' in response:
                message = "Goodbye! Thank you for using our service."
                logger.debug("Generated goodbye message")
        
        # Handle string responses (fallback)
        elif isinstance(response, str):
            message = response
            logger.debug(f"Using string response directly: {message}")

    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        message = str(response)

    # If we still don't have a valid message, use a safe fallback
    if not message:
        logger.warning(f"Failed to extract message, using raw response: {response}")
        message = str(response)

    logger.debug(f"Final formatted message: {message}")
    
    return {
        "message": message,
        "state": {
            "carrier_confirmed": state["carrier_confirmed"],
            "departed": state["departed"],
            "current_step": "confirmation" if not state["carrier_confirmed"] else "departure" if not state["departed"] else "complete"
        }
    }

def process_chat_sequence(state: DriverState, user_message: Optional[str] = None):
    """
    Process the chat sequence following the pattern:
    1. interrupt - get question for user
    2. update state - handle user's response
    3. simple query - process current state
    4. new interrupt - prepare next question
    5. repeat
    """
    thread = {"configurable": {"thread_id": "1"}}
    
    if user_message is None:
        # Initial flow - get first interrupt
        result = driver_graph.invoke(state, config=thread)
        response = None
        for event in driver_graph.stream(result, config=thread):
            response = event
        return format_response(response, state)
    else:
        # 1. Handle interrupt (user's response)
        result = driver_graph.invoke(Command(resume=user_message), config=thread)
        
        # 2. Update state
        state = driver_graph.get_state(thread).values
        
        # 3. Process current state
        response = None
        for event in driver_graph.stream(state, config=thread):
            if event:
                response = event
                
        # 4. Get new interrupt/next state
        if not state["carrier_confirmed"] or not state["departed"]:
            result = driver_graph.invoke(state, config=thread)
            for event in driver_graph.stream(result, config=thread):
                if event:
                    response = event
        
        return format_response(response, state)

def initialize_chat():
    """Initialize a new chat session with default state"""
    initial_state = {
        "carrier_confirmed": False,
        "ask_carrier_confirmed": False,
        "ask_departed": False,
        "departed": False,
        "messages": [HumanMessage(content="Hello, how are you?")],
        "current_query": None
    }
    return initial_state

def get_current_state():
    """Get the current state of the conversation"""
    thread = {"configurable": {"thread_id": "1"}}
    return driver_graph.get_state(thread).values

# Example usage in the notebook:
"""
# Initialize chat
state = initialize_chat()

# Get first interrupt/question
response = process_chat_sequence(state)
print("Bot:", response)

# Send user response and get next interrupt
response = process_chat_sequence(state, "yes")
print("Bot:", response)

# Continue conversation...
response = process_chat_sequence(state, "yes")
print("Bot:", response)
"""






