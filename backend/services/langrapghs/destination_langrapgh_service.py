# %%
from datetime import datetime
from typing import Annotated, TypedDict, Optional
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
from dotenv import load_dotenv


# Add the backend directory to Python path
notebook_dir = Path().absolute()
backend_dir = notebook_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))



# Import database models
from db_models import Stop, get_db

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


llm = ChatOpenAI(model="gpt-4o-mini", api_key='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')


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
    query = f"Hello! Support agent here. Have you arrived at {state['stop_data']['name']}?"
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
    
def format_human_text(text: str) -> str:
    return text.lower().strip().replace(',', '').replace('.', '').replace('?', '').replace('!', '').replace('_', ' ').split(' ')


def get_arrival_confirmation(state: State) -> State:
    if state['messages'][-1].name != 'greet':
        msg = llm.invoke([SystemMessage(content=f"You are a support agent dispatcher for a trucking company. Respond to the trucker messages without getting out of path of conversation and ask them have they arrived at {state['stop_data']['name']}"),*state['messages']])
        state['messages'].append(AIMessage(content=msg.content, name='arrival_confirmation'))
    state = get_humanResponse(state, 'arrival_confirmation')
    if 'yes' in format_human_text(state['messages'][-1].content):
        query = f"Have you signed the Proof of Delivery signature?"
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='arrival_confirmation')
            ],
            'arrived': True
        }
    elif 'no' in format_human_text(state['messages'][-1].content):
        query = f"All right, please let me know when you arrive at {state['stop_data']['name']}."
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='Goodbye')
            ],
            'arrived': False,
            'running': False
        }
    else:
        return state
    
def get_pod_confirmation(state: State) -> State:
    if state['messages'][-1].name != 'arrival_confirmation':
        msg = llm.invoke([SystemMessage(content=f"You are a support agent dispatcher for a trucking company. Respond to the trucker messages without getting out of path of conversation and ask them if they have signed the proof of delivery signature"),*state['messages']])
        state['messages'].append(AIMessage(content=msg.content, name='pod_confirmation'))
    state = get_humanResponse(state, 'pod_confirmation')
    if 'yes' in format_human_text(state['messages'][-1].content):
        query = f"Good to know. will be in touch again soon."
        return {   
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='Goodbye')
            ],
            'pod_signature': True,
            'running': False
        }
    elif 'no' in format_human_text(state['messages'][-1].content):
        query = f"Okay, let me know when you have signed the proof of delivery signature"
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='Goodbye')
            ],
            'pod_signature': False,
            'running': False
        }
        
    else:
        return state

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



