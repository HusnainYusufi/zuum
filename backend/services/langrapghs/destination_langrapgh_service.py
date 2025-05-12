# %%
from datetime import datetime
from typing import Annotated, TypedDict, Optional
import sys
from pathlib import Path
from typing import Annotated
from llm_config import llm
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from typing import Annotated, Optional
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers.json import JsonOutputParser
from dotenv import load_dotenv

from services.langrapghs.prompts.destination_prompts import ARRIVED_PROMPT, POD_SIGNATURE_PROMPT
from services.langrapghs.prompts.basic_prompts import CLASSIFIER_PROMPT, FALLBACK_PROMPT, WAIT_PROMPT, GOODBYE_PROMPT
# Add the backend directory to Python path
notebook_dir = Path().absolute()
backend_dir = notebook_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

import os

# Import database models
from db_models import Stop, get_db, Journey, JourneyState

load_dotenv()


class State(TypedDict):
   messages: Annotated[list, add_messages] = None
   stop_id: Optional[str] = None
   stop_data: Optional[dict] = None
   running: Optional[bool] = None
   arrived: Optional[bool] = None
   pod_signature: Optional[bool] = None
   have_loaded: Optional[bool] = None

graphbuilder = StateGraph(State)
json_parser = JsonOutputParser()
fmt = json_parser.get_format_instructions()
db = next(get_db())




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
    msg = llm.invoke([SystemMessage(content=ARRIVED_PROMPT.format(location=state['stop_data']['name']))])
    query = msg.content
    return {
        **state,
        'messages': [
            AIMessage(content=query, name='greet')
        ]
    }
    
def get_humanResponse(state: State, name: str) -> State:
    humanResponse = interrupt(state['messages'][-1].content)
    humanResponse = humanResponse['data']
    return {
        **state,
        'messages': [*state['messages'],
            HumanMessage(content=humanResponse, name=name)
        ]
    }
    
def format_classifier_text(text: str) -> str:
    return text.lower().strip().replace(',', '').replace('.', '').replace('?', '').replace('!', '').replace('_', ' ').split(' ')


def get_arrival_confirmation(state: State) -> State:
    if state['messages'][-1].name == 'arrival_confirmation':
        msg = llm.invoke([SystemMessage(content=FALLBACK_PROMPT.format(question=f"have they arrived at there destination i.e, {state['stop_data']['name']}")),*state['messages']])
        state['messages'].append(AIMessage(content=msg.content, name='arrival_confirmation'))
    state = get_humanResponse(state, 'arrival_confirmation')
    
    check_response = llm.invoke([
        SystemMessage(content=CLASSIFIER_PROMPT.format(question=f"have they arrived at there destination i.e, {state['stop_data']['name']} which can also be only yes or no")),
        *state['messages']
    ])
    
    response_type = format_classifier_text(check_response.content)
    
    
    
    if 'affirmative' in response_type:
        msg = llm.invoke([SystemMessage(content=POD_SIGNATURE_PROMPT),*state['messages']])
        query = msg.content
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='arrival_confirmation')
            ],
            'arrived': True
        }
    elif 'negative' in response_type:
        msg = llm.invoke([SystemMessage(content=WAIT_PROMPT.format(reason=f"not arrived at there destination i.e, {state['stop_data']['name']}")),*state['messages']])
        query = msg.content
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='wait')
            ]
        }

    
def get_pod_confirmation(state: State) -> State:
    if state['messages'][-1].name == 'pod_confirmation':
        msg = llm.invoke([SystemMessage(content=FALLBACK_PROMPT.format(question="signed the proof of delivery signature")),*state['messages']])
        state['messages'].append(AIMessage(content=msg.content, name='pod_confirmation'))
    state = get_humanResponse(state, 'pod_confirmation')
    
    check_response = llm.invoke([
        SystemMessage(content=CLASSIFIER_PROMPT.format(question="signed the proof of delivery signature which can also be only yes or no")),
        *state['messages']
    ])
    
    response_type = format_classifier_text(check_response.content)
    
    if 'affirmative' in response_type:
        msg = llm.invoke([SystemMessage(content=GOODBYE_PROMPT),*state['messages']])
        query = msg.content
        db.query(Journey).filter(Journey.id == 1).update({'current_state': JourneyState.DESTINATION.value})
        db.commit()
        return {   
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='pod_confirmation')
            ],
            'pod_signature': True,
            'running': False
        }
    elif 'negative' in response_type:
        msg = llm.invoke([SystemMessage(content=WAIT_PROMPT.format(reason="not signed the proof of delivery signature")),*state['messages']])
        query = msg.content
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='wait')
            ]
        }
        

def origin(state: State) -> State:
    return state

def router(state: State) -> State:
    if state['messages'][-1].name == 'Goodbye':
        return 'end'
    elif state.get('arrived') is None:
        return 'get_arrival_confirmation'
    elif state.get('pod_signature') is None:
        return 'get_pod_confirmation'
    else:
        return 'end'
    

class DestinationLangraph:
    def __init__(self):
        graphbuilder.add_node('greet', greet)
        graphbuilder.add_node('get_data_from_database', get_data_from_database)
        graphbuilder.add_node('get_arrival_confirmation', get_arrival_confirmation)
        graphbuilder.add_node('get_pod_confirmation', get_pod_confirmation)
        graphbuilder.add_node('origin', origin)

        graphbuilder.add_edge(START, 'get_data_from_database')
        graphbuilder.add_edge('get_data_from_database', 'greet')
        graphbuilder.add_edge('greet', 'origin')


        graphbuilder.add_conditional_edges(
            'origin',
            router,
            {
                'get_arrival_confirmation': 'get_arrival_confirmation',
                'get_pod_confirmation': 'get_pod_confirmation', 
                'end': END
            }
        )

        graphbuilder.add_edge('get_arrival_confirmation', 'origin')
        graphbuilder.add_edge('get_pod_confirmation', 'origin')


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

destination_langgraph_service = DestinationLangraph()



