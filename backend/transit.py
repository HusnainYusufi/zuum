# %%
import os
from datetime import datetime, time
from typing import Annotated, TypedDict, Literal, Optional, List, Dict
import re

from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from dotenv import load_dotenv
from loguru import logger

# Import database models
from db_models import Stop, ChatHistory, SessionLocal

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

# 1. Define a simplified transit state 
class TransitState(TypedDict):
    bool0: bool
    bool1: bool
    bool2: bool
    bool3: bool
    stop_id: Optional[int]  # for getting stop information

    messages: Annotated[list, add_messages]
    isRunning: Optional[bool] = None
    current_query: Optional[str] = None

class StopInfo(BaseModel):
    ETA: str = None
    Cross_Street: str = None
    Nearest_Highway: str = None
    is_delayed: bool = None
    Delay_Reason: str = None
    location: str = None
    issue: bool

# Function to get stop information from database
def get_stop_info(stop_id: int) -> Optional[Stop]:
    db = SessionLocal()
    try:
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        return stop
    finally:
        db.close()

# Function to save chat history
def save_chat_history(stop_id: int, user_message: str, bot_message: str):
    db = SessionLocal()
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chat_history = ChatHistory(
            stop_id=stop_id,
            user_message=user_message,
            bot_message=bot_message,
            timestamp=timestamp
        )
        db.add(chat_history)
        db.commit()
    finally:
        db.close()

# Function to get chat history for a stop
def get_chat_history(stop_id: int) -> List[Dict]:
    db = SessionLocal()
    try:
        history = db.query(ChatHistory).filter(ChatHistory.stop_id == stop_id).all()
        return [
            {
                "user_message": h.user_message,
                "bot_message": h.bot_message,
                "timestamp": h.timestamp
            }
            for h in history
        ]
    finally:
        db.close()

# %%
# Helper function
def set_bits(n: int):
    return {
        "bool3": bool(n & 0b1000),
        "bool2": bool(n & 0b0100),
        "bool1": bool(n & 0b0010),
        "bool0": bool(n & 0b0001),
    }

# Nodes
def ask_scheduled_message(state: TransitState):
    print(state)
    print("Current Node: ask_scheduled_message")

    LLM_query = "Are you on track with the delivery?"
    return {**state, **set_bits(0b0001), "current_query": LLM_query}

    # LLM_query = llm.invoke(get_messages_info("Are you on track with the delivery?"))
    # return {**state, **set_bits(0b0001), "current_query": LLM_query.content}

def get_scheduled_message(state: TransitState):
    print(state)
    print("Current Node: get_scheduled_message")
    human_response = interrupt({"query": state["current_query"]})
    
    # Save chat history if stop_id is set
    if state.get("stop_id"):
        save_chat_history(state["stop_id"], human_response, state["current_query"])
    
    # Get stop info if available
    stop_info = None
    if state.get("stop_id"):
        stop_info = get_stop_info(state["stop_id"])
        
    # Create a StopInfo object with issue status
    msg = StopInfo(issue=False)
    if stop_info and stop_info.is_delayed:
        msg.issue = True
    
    if not msg.issue:
        return {**state, **set_bits(0b0010)}  # Success -> ask_location
    else:
        return {**state, **set_bits(0b0000)}  # Failure -> ask_scheduled_message

def ask_location(state: TransitState):
    logger.debug(state)
    print("Current Node: ask_location")
    LLM_query = "What is your current location?"
    return {**state, **set_bits(0b0011), "current_query": LLM_query}

def get_location(state: TransitState):
    print(state)
    print("Current Node: get_location")
    human_response = interrupt({"query": state["current_query"]})
    
    # Save chat history if stop_id is set
    if state.get("stop_id"):
        save_chat_history(state["stop_id"], human_response, state["current_query"])
    
    # Get stop info if available
    stop_info = None
    if state.get("stop_id"):
        stop_info = get_stop_info(state["stop_id"])

    LLM_query = llm.invoke(
        get_messages_info(
            [f"""Return True if the user provided location matches the expected location, otherwise return False.
            Expected Location: {stop_info.location}
            User Response: {human_response}"""]
        )
    )

    logger.debug(LLM_query.content)
            
    if "True" in LLM_query.content:
        # Update the reported location in the database
        if state.get("stop_id"):
            db = SessionLocal()
            try:
                stop = db.query(Stop).filter(Stop.id == state["stop_id"]).first()
                if stop:
                    stop.reported_location = human_response
                    db.commit()
            finally:
                db.close()

        logger.success("Location matched")
        return {**state, **set_bits(0b0100)}  # Success -> ask_cross_street
    else:

        logger.error("Location not matched")
        return {**state, **set_bits(0b0010)}  # Failure -> ask_location

def ask_cross_street(state: TransitState):
    print(state)
    print("Current Node: ask_cross_street")
    LLM_query = "What is your nearest cross street?"
    return {**state, **set_bits(0b0101), "current_query": LLM_query}

def get_cross_street(state: TransitState):
    print(state)
    print("Current Node: get_cross_street")
    human_response = interrupt({"query": state["current_query"]})
    
    # Save chat history if stop_id is set
    if state.get("stop_id"):
        save_chat_history(state["stop_id"], human_response, state["current_query"])
    
    # Store the cross street information without comparison
    if state.get("stop_id"):
        db = SessionLocal()
        try:
            stop = db.query(Stop).filter(Stop.id == state["stop_id"]).first()
            if stop:
                stop.cross_street = human_response
                db.commit()
        finally:
            db.close()
    
    # Always proceed to next step
    return {**state, **set_bits(0b0110)}  # Success -> ask_nearest_highway

def ask_nearest_highway(state: TransitState):
    print(state)
    print("Current Node: ask_nearest_highway")
    LLM_query = "What is your nearest highway?"
    return {**state, **set_bits(0b0111), "current_query": LLM_query}

def get_nearest_highway(state: TransitState):
    print(state)
    print("Current Node: get_nearest_highway")
    human_response = interrupt({"query": state["current_query"]})
    
    # Save chat history if stop_id is set
    if state.get("stop_id"):
        save_chat_history(state["stop_id"], human_response, state["current_query"])
    
    # Store the highway information without comparison
    if state.get("stop_id"):
        db = SessionLocal()
        try:
            stop = db.query(Stop).filter(Stop.id == state["stop_id"]).first()
            if stop:
                stop.nearest_highway = human_response
                db.commit()
        finally:
            db.close()
    
    # Always proceed to next step
    return {**state, **set_bits(0b1000)}  # Success -> ask_eta

# Function to parse time string to datetime object
def parse_time_string(time_str):
    try:
        # Try parsing time formats like "5:00 PM", "3:30 PM", etc.
        return datetime.strptime(time_str.strip(), "%I:%M %p").time()
    except ValueError:
        try:
            # Try parsing 24-hour format
            return datetime.strptime(time_str.strip(), "%H:%M").time()
        except ValueError:
            # Try extracting time using regex
            pattern = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM)?'
            match = re.search(pattern, time_str)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2) or 0)
                ampm = match.group(3)
                
                if ampm and ampm.lower() == 'pm' and hour < 12:
                    hour += 12
                elif ampm and ampm.lower() == 'am' and hour == 12:
                    hour = 0
                
                return time(hour, minute)
    
    # Default fallback
    return None

def ask_eta(state: TransitState):
    print(state)
    print("Current Node: ask_eta")
    LLM_query = "What is the estimated time of arrival?"
    return {**state, **set_bits(0b1001), "current_query": LLM_query}


def get_eta(state: TransitState):
    logger.debug(state)
    logger.warning("Current Node: get_eta")
    human_response = interrupt({"query": state["current_query"]})
    
    # Save chat history if stop_id is set
    if state.get("stop_id"):
        save_chat_history(state["stop_id"], human_response, state["current_query"])
    
    # Get stop info if available
    stop_info = None
    if state.get("stop_id"):
        stop_info = get_stop_info(state["stop_id"])
    
    is_delayed = False

    # LLM_query = llm.invoke("""Return True if the user provided ETA is equal to or less than the expected ETA, otherwise return False.
    # Expected ETA: {stop_info.eta}
    # User Response: {human_response}
    # Current Time: {datetime.now().strftime("%I:%M %p")}""")

    LLM_query = llm.invoke(
        get_messages_info(
            [f"""Return True if the user provided ETA is equal to or less than the expected ETA, otherwise return False.
            Expected ETA: {stop_info.eta}
            User Response: {human_response}
            Current Time: {datetime.now().strftime("%I:%M %p")}"""]
        )
    )

    logger.debug(LLM_query.content)

    if "True" in LLM_query.content:
        # Update ETA in the database if not delayed
        if state.get("stop_id") and not is_delayed:
            db = SessionLocal()
            try:
                stop = db.query(Stop).filter(Stop.id == state["stop_id"]).first()
                if stop:
                    user_eta_time = parse_time_string(human_response)
                    if user_eta_time:
                        user_eta_str = user_eta_time.strftime("%I:%M %p")
                        stop.eta = user_eta_str
                    db.commit()
            finally:
                db.close()

        logger.success("No delay")
        return {**state, **set_bits(0b1111)}  # Success -> goodbye
    else:

        logger.error("delayed")
        return {**state, **set_bits(0b1010)}  # Failure -> ask delay

def ask_delay(state: TransitState):
    print(state)
    print("Current Node: ask_delay")

    # LLM_query = llm.invoke(("What is the delay reason?"))
    LLM_query = "What is the delay reason?"
    return {**state, **set_bits(0b1011), "current_query": LLM_query}

def get_delay(state: TransitState):
    print(state)
    print("Current Node: get_delay")
    human_response = interrupt({"query": state["current_query"]})
    
    # Save chat history if stop_id is set
    if state.get("stop_id"):
        save_chat_history(state["stop_id"], human_response, state["current_query"])
    
    # Store the delay reason without comparison
    if state.get("stop_id"):
        db = SessionLocal()
        try:
            stop = db.query(Stop).filter(Stop.id == state["stop_id"]).first()
            if stop:
                stop.delay_reason = human_response
                stop.is_delayed = True
                db.commit()
        finally:
            db.close()
    
    # Always proceed to next step
    return {**state, **set_bits(0b1100)}  # Success -> goodBye

# %%
def goodBye(state: TransitState):
    'Say good bye to the user.'
    # msg = llm.invoke('Say good bye to the user.')
    # print(msg.content)
    return {**state, "isRunning": False}

def transit(state: TransitState):
    return state

# %%
# Map 4-bit binary codes to actions
state_actions = {
    0b0000: "ask_scheduled_message",
    0b0001: "get_scheduled_message",
    0b0010: "ask_location",
    0b0011: "get_location",
    0b0100: "ask_cross_street",
    0b0101: "get_cross_street",
    0b0110: "ask_nearest_highway",
    0b0111: "get_nearest_highway",
    0b1000: "ask_eta",
    0b1001: "get_eta",
    0b1010: "ask_delay",
    0b1011: "get_delay",
    0b1100: "goodBye",
}

def encode_state(state: TransitState) -> int:
    # Encode into a 4-bit integer
    bits = (
        (state["bool3"] << 3) |   # <-- New higher-order bit
        (state["bool2"] << 2) |
        (state["bool1"] << 1) |
        (state["bool0"])
    )
    return bits

def transit_router(state: TransitState) -> str:
    code = encode_state(state)
    return state_actions.get(code, "goodBye")


# %%
# 3. Build the graph
def build_transit_graph():
    graph_builder = StateGraph(TransitState)
    
    # Add all the nodes
    graph_builder.add_node("transit", transit)
    graph_builder.add_node("ask_scheduled_message", ask_scheduled_message)
    graph_builder.add_node("get_scheduled_message", get_scheduled_message)
    graph_builder.add_node("ask_location", ask_location)
    graph_builder.add_node("get_location", get_location)
    graph_builder.add_node("ask_cross_street", ask_cross_street)
    graph_builder.add_node("get_cross_street", get_cross_street)
    graph_builder.add_node("ask_nearest_highway", ask_nearest_highway)
    graph_builder.add_node("get_nearest_highway", get_nearest_highway)
    graph_builder.add_node("ask_eta", ask_eta)
    graph_builder.add_node("get_eta", get_eta)
    graph_builder.add_node("ask_delay", ask_delay)
    graph_builder.add_node("get_delay", get_delay)
    graph_builder.add_node("goodBye", goodBye)

    graph_builder.add_edge(START, "transit")

    graph_builder.add_conditional_edges(
        "transit",
        transit_router,
        {
            "ask_scheduled_message": "ask_scheduled_message",
            "get_scheduled_message": "get_scheduled_message",
            "ask_location": "ask_location",
            "get_location": "get_location",
            "ask_eta": "ask_eta",
            "get_eta": "get_eta",
            "ask_delay": "ask_delay",
            "get_delay": "get_delay",
            "ask_cross_street": "ask_cross_street",
            "get_cross_street": "get_cross_street",
            "ask_nearest_highway": "ask_nearest_highway",
            "get_nearest_highway": "get_nearest_highway",
            "goodBye": "goodBye"
        }
    )    

    graph_builder.add_edge("get_delay", "goodBye")
    graph_builder.add_edge("goodBye", END)

    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)

    return graph

# %%
def initialize_transit_chat(stop_id: int):
    """Initialize a new transit chat session with default state"""
    initial_state = {
        "bool3": False,
        "bool2": False,
        "bool1": False,
        "bool0": False,
        "stop_id": stop_id,
        
        "messages": [HumanMessage(content="Hello, how are you?")],
        "current_query": None
    }
    return initial_state

def get_current_state(state: TransitState):
    """Get the current state of the conversation"""
    thread = {"configurable": {"thread_id": state["stop_id"]}}
    return transit_graph.get_state(thread).values

def process_transit_chat_sequence(state: TransitState, user_message: Optional[str] = None):
    """
    Process the transit chat sequence following the pattern:
    1. interrupt - get question for user
    2. update state - handle user's response
    3. simple query - process current state
    4. new interrupt - prepare next question
    5. repeat
    """

    thread = {"configurable": {"thread_id": state["stop_id"]}}

    if user_message is None:
        result = transit_graph.invoke(state, config=thread)
        response = None
        for event in transit_graph.stream(result, config=thread):
            response = event

    else:
        result = transit_graph.invoke(state, config = thread)

        # 2. Update state
        state = transit_graph.get_state(thread).values
        
        # 3. Process current state
        response = None
        for event in transit_graph.stream(state, config=thread):
            if event:
                response = event
                
        # response message
        for event in transit_graph.stream(
            Command(resume=user_message), 
            config = thread
        ):
            print(event)
            print()

        state = transit_graph.get_state(thread).values

        # result = transit_graph.invoke(Command(resume=user_message), config=thread)
        # response = None
        # for event in transit_graph.stream(result, config=thread):
        #     response = event

    return format_response(response, state)

# def process_transit_chat_sequence(state: TransitState, user_message: Optional[str] = None):
#     """
#     Process the transit chat sequence following the pattern:
#     1. interrupt - get question for user
#     2. update state - handle user's response
#     3. simple query - process current state
#     4. new interrupt - prepare next question
#     5. repeat
#     """
#     thread = {"configurable": {"thread_id": state["stop_id"]}}
    
#     # # Ensure all required fields are present in state
#     # if not isinstance(state, dict):
#     #     state = initialize_transit_chat()
#     # else:
#     #     # Add any missing fields with default values
#     #     default_state = initialize_transit_chat()
#     #     for key in default_state:
#     #         if key not in state and key != "stop_id":  # Preserve stop_id if it exists
#     #             state[key] = default_state[key]
    
#     if user_message is None:
#         # Initial flow - get first interrupt
#         result = transit_graph.invoke(state, config=thread)
#         response = None
#         for event in transit_graph.stream(result, config=thread):
#             response = event
#         return format_response(response, state)
#     else:
#         # 1. Handle interrupt (user's response)
#         result = transit_graph.invoke(Command(resume=user_message), config=thread)
        
#         # 2. Update state
#         state = transit_graph.get_state(thread).values
        
#         # 3. Process current state
#         response = None
#         for event in transit_graph.stream(state, config=thread):
#             if event:
#                 response = event
                
#         # 4. Get new interrupt/next state
#         if not state.get("isRunning", True):  # Check if conversation is finished
#             return format_response(response, state)
            
#         result = transit_graph.invoke(state, config=thread)
#         for event in transit_graph.stream(result, config=thread):
#             if event:
#                 response = event
        
#         return format_response(response, state)

# Initialize the graph
transit_graph = build_transit_graph()

# Function to get all stops
def get_all_stops():
    db = SessionLocal()
    try:
        stops = db.query(Stop).all()
        return [
            {
                "id": stop.id,
                "name": stop.name,
                "location": stop.location,
                "eta": stop.eta,
                "is_delayed": stop.is_delayed,
                'is_origin': stop.is_origin,
                'is_destination': stop.is_destination
            }
            for stop in stops
        ]
    finally:
        db.close()

# Function to get all stops with complete information
def get_all_stops_with_details():
    db = SessionLocal()
    try:
        stops = db.query(Stop).all()
        return [
            {
                "id": stop.id,
                "name": stop.name,
                "location": stop.location,
                "eta": stop.eta,
                "cross_street": stop.cross_street,
                "nearest_highway": stop.nearest_highway,
                "is_delayed": stop.is_delayed,
                "delay_reason": stop.delay_reason,
                "expected_location": stop.expected_location,
                "reported_location": stop.reported_location,
                'is_origin': stop.is_origin,
                'is_destination': stop.is_destination
            }
            for stop in stops
        ]
    finally:
        db.close()

def format_response(response, state: TransitState):
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
            # Handle ask_delay responses
            elif 'ask_delay' in response:
                delay_info = response['ask_delay']
                if isinstance(delay_info, dict) and 'current_query' in delay_info:
                    message = delay_info['current_query']
                    logger.debug(f"Extracted query from ask_delay: {message}")
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
    
    # Ensure all required state fields are present
    state_dict = {
        "bool3": state.get("bool3", False),
        "bool2": state.get("bool2", False),
        "bool1": state.get("bool1", False),
        "bool0": state.get("bool0", False),
        "stop_id": state.get("stop_id", None)
    }
    
    # Determine current step
    code = encode_state(state)
    current_step = state_actions.get(code, "goodBye")
    
    return {
        "message": message,
        "state": {
            **state_dict,
            "current_step": current_step
        }
    }










