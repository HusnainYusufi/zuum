# %%
import os
from datetime import datetime
from typing import Annotated, TypedDict, Optional
import re
import sys
from pathlib import Path


from typing import Annotated


from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langgraph.types import Command, interrupt
from typing import Annotated, Optional
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers.json import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from services.langrapghs.prompts.transit_prompt import GREET_PROMPT, EXTRACT_LOCATION_AND_ETA_PROMPT, GET_LOCATION_OR_ETA_PROMPT, examples, DELAY_REASON_PROMPT, GET_DELAY_REASON_PROMPT, EXTRACT_HIGHWAY_NAME_PROMPT
from services.langrapghs.prompts.basic_prompts import FALLBACK_PROMPT
import os

# Add the backend directory to Python path
notebook_dir = Path().absolute()
backend_dir = notebook_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))


# Import database models
from db_models import Stop, ChatHistory, get_db

load_dotenv()
class State(TypedDict):
   messages: Annotated[list, add_messages] = None
   stop_id: Optional[str] = None
   stop_data: Optional[dict] = None
   running: Optional[bool] = None
   reported_location: Optional[str] = None
   estimated_eta: Optional[str] = None
   delay_reason: Optional[str] = None
   delayed: Optional[bool] = None
   nearest_highway: Optional[str] = None

graphbuilder = StateGraph(State)
json_parser = JsonOutputParser()
fmt = json_parser.get_format_instructions()
db = next(get_db())



llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv('OPENAI_API_KEY'))




def get_data_from_database(state: State) -> State:
    try:
        print(state)
        stop_data = db.query(Stop).filter(Stop.id == state['stop_id']).first()
        if stop_data:
            # Convert SQLAlchemy model to dictionary
            stop_dict = {
                'id': stop_data.id,
                'name': stop_data.name,
                'location': stop_data.location,
                'eta': stop_data.eta,
                'cross_street': stop_data.cross_street,
                'nearest_highway': stop_data.nearest_highway,
                'is_delayed': stop_data.is_delayed,
                'delay_reason': stop_data.delay_reason,
                'expected_location': stop_data.expected_location,
                
            }
            
            # Parse the eta string to datetime
            stop_dict['eta'] = datetime.strptime(stop_dict['eta'].split('.')[0], "%Y-%m-%dT%H:%M:%S")
            
            return {
                **state,
                'stop_data': stop_dict
            }
        else:
            raise ValueError(f"No stop found with id {state['stop_id']}")
    finally:
        db.close()

def greet(state: State) -> State:
    'Call this tool when the driver wants to end the conversation and shut down the agent.'
    msg = llm.invoke([SystemMessage(content=GREET_PROMPT)])
    query = msg.content
    return {
        **state,
        'messages': [
            AIMessage(content=query)
        ]
    }

def get_humanResponse(state: State) -> State:
    humanResponse = interrupt(state['messages'][-1].content)
    humanResponse = humanResponse['data']
    return {
        **state,
        'messages': [*state['messages'],
            HumanMessage(content=humanResponse)
        ]
    }
    
def get_location_and_eta(state: State) -> State:
    state = get_humanResponse(state)
    prompt = PromptTemplate(
        input_variables=[
           "human_response", "format_instructions", "current_time"
        ],
        template=EXTRACT_LOCATION_AND_ETA_PROMPT,
    )
    formatted = prompt.format_prompt(human_response=state['messages'][-1].content, format_instructions=fmt, current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    msg = llm.invoke(formatted.to_messages())
    json_response = json_parser.parse(msg.content)
    print(json_response)
    print(json_response.get('eta'))
    location = json_response['location'] if json_response.get('location') is not None else state.get('reported_location') if state.get('reported_location') is not None else None
    eta = json_response['eta'] if json_response.get('eta') is not None else state.get('estimated_eta') if state.get('estimated_eta') is not None else None
    
   
    query = ''
    
    print(eta,location)
    if location is None or eta is None:
        msg = llm.invoke([SystemMessage(content=GET_LOCATION_OR_ETA_PROMPT.format(location=location, eta=eta, examples=examples )),*state['messages']])
        query = msg.content        
    else:
        # Convert eta to ISO format if it's not already
        if eta is not None:
            try:
                # Try to parse with ISO format first
                parsed_eta = datetime.strptime(eta.split('.')[0], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                try:
                    # Try alternative format
                    parsed_eta = datetime.strptime(eta, "%Y-%m-%d %H:%M:%S")
                    # Convert to ISO format for consistency
                    eta = parsed_eta.strftime("%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    # If all parsing fails, use a default format
                    print(f"Could not parse eta: {eta}")
                    eta = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        db.query(Stop).filter(Stop.id == state['stop_id']).update({'reported_location': location, 'eta': eta})   
        db.commit()     
        if eta is not None:
            try:
                # Try to parse with ISO format first
                eta_dt = datetime.strptime(eta.split('.')[0], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                # Try alternative format
                eta_dt = datetime.strptime(eta, "%Y-%m-%d %H:%M:%S")
                
            print(eta_dt, state.get('stop_data')['eta'])
            if eta_dt > state.get('stop_data')['eta']:
                delay = eta_dt - state.get('stop_data')['eta']
                msg = llm.invoke([SystemMessage(content=DELAY_REASON_PROMPT.format(delay=delay)),*state['messages']])
                query = msg.content
                state['delayed'] = True

    return {
        **state,
        'messages': [*state['messages'],
            AIMessage(content=query, name='transit_chat')
        ]
        ,
        'reported_location': location,
        'estimated_eta': eta,
    }
    
    
def get_delay_reason(state:State):
    state = get_humanResponse(state=state)
    msg = llm.invoke([SystemMessage(
        content=GET_DELAY_REASON_PROMPT
    ), *state['messages']])
    
    if 'yes' in msg.content.lower():
        db.query(Stop).filter(Stop.id == state['stop_id']).update({'delay_reason':state['messages'][-1].content, 'is_delayed':True})
        db.commit()
        return{**state,'messages':[*state['messages'], AIMessage(content='', name='transit_chat')], 'delay_reason':state['messages'][-1].content}
    else:
        return{**state, 'messages':[*state['messages'], msg]}

def check_router(state: State) -> State:
    return state


def router(state: State) -> State:
    print(state)
    if state.get('reported_location') is None or state.get('estimated_eta') is None:
        return 'get_location_and_eta'
    if state.get('delayed') is True and state.get('delay_reason') is None:
        return 'get_delay_reason'
    if state.get('nearest_highway') is None:
        return 'get_nearest_highway'
    return 'goodbye'




def get_nearest_highway(state: State) -> State:
    query = ''
    if state.get('messages')[-1].name == 'transit_chat':
        query = 'What is the nearest highway exit?'
    else:
        msg = llm.invoke([SystemMessage(content=FALLBACK_PROMPT.format(question="about the nearest highway exit")),*state['messages']])
        query = msg.content
    state['messages'].append(AIMessage(content=query, name='highway_exit'))
    state = get_humanResponse(state)
    prompt = PromptTemplate(
        input_variables=[
           "human_response", "format_instructions"
        ],
        template=EXTRACT_HIGHWAY_NAME_PROMPT,
    )
    formatted = prompt.format_prompt(human_response=state['messages'][-1].content, format_instructions=fmt)
    msg = llm.invoke(formatted.to_messages())
    json_response = json_parser.parse(msg.content)
    print(json_response)
    highway_name = json_response['highway_name']
    if highway_name is not None:
        db.query(Stop).filter(Stop.id == state['stop_id']).update({'nearest_highway':highway_name})
        db.commit()
        return {**state, 'nearest_highway':highway_name}
    else:
        return {**state, 'nearest_highway':None}

def goodbye(state: State) -> State:
    query = 'Thats all for now, Have a safe journey!'
    return {**state, 'messages':[*state['messages'], AIMessage(content=query)]}

class TransitLangGraphService:
    def __init__(self):
        graphbuilder.add_node('get_data_from_database', get_data_from_database)
        graphbuilder.add_node('get_location_and_eta', get_location_and_eta)
        graphbuilder.add_node('get_delay_reason', get_delay_reason)
        graphbuilder.add_node('greet', greet)
        graphbuilder.add_node('check_router', check_router)
        graphbuilder.add_node('get_nearest_highway', get_nearest_highway)
        graphbuilder.add_node('goodbye', goodbye)
        graphbuilder.add_edge(START, 'get_data_from_database')
        graphbuilder.add_edge('get_data_from_database', 'greet')
        graphbuilder.add_edge('greet', 'check_router')
        graphbuilder.add_conditional_edges(
            'check_router',
            router,
            {
                'get_location_and_eta': 'get_location_and_eta',
                'get_delay_reason': 'get_delay_reason',
                'get_nearest_highway': 'get_nearest_highway',
                'goodbye': 'goodbye'
            }
        )

        graphbuilder.add_edge('get_location_and_eta', 'check_router')
        graphbuilder.add_edge('get_delay_reason', 'check_router')
        graphbuilder.add_edge('get_nearest_highway', 'check_router')
        graphbuilder.add_edge('goodbye', END)

        memory = MemorySaver()
        self.graph = graphbuilder.compile(checkpointer=memory)
        
    def run(self, state: State, thread_id: str):
        query = ''
        for eventType, event in self.graph.stream(state, {'configurable': {'thread_id': thread_id}}, stream_mode=["values", "updates"]):
            if eventType == "updates":
                if event.get('__interrupt__'):
                    query = event['__interrupt__'][0].value
            elif eventType == "values" and len(event.get('messages')) > 0:
                query = event['messages'][-1].content
        return query

transit_langgraph_service = TransitLangGraphService()
