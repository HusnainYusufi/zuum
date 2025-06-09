# %%
from datetime import datetime
from typing import Annotated, TypedDict, Optional
import sys
from pathlib import Path
from loguru import logger
from typing import Annotated
from services.langrapghs.prompts.origin_prompts import CARRIER_CONFIRMATION_PROMPT,LOAD_NUMBER_PROMPT, LOADED_PROMPT, DISPATCHED_PROMPT
from services.langrapghs.prompts.basic_prompts import CLASSIFIER_PROMPT, FALLBACK_PROMPT, WAIT_PROMPT, GOODBYE_PROMPT
from llm_config import llm
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import  interrupt
from typing import Annotated, Optional
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers.json import JsonOutputParser
from dotenv import load_dotenv
import os
from langgraph.types import Command



# 1. Create and/or select your dataset



def compare_messages(outputs: dict, reference_outputs: dict) -> bool:
    prompt = f"""You are a message comparison expert. Your task is to determine if two messages are conveying the same core meaning or intent, even if they use different words.

Focus on the main purpose of the message, not minor details. For example:
- If both messages are asking for carrier confirmation, they're the same
- If both messages are asking if the load is ready, they're the same
- If both messages are asking if the journey has started, they're the same
- If both messages are farewell/goodbye messages, they're the same

Expected message: "{reference_outputs['output']}"
Actual message: "{outputs['output']}"

Are these messages conveying the same core meaning/intent? Give a score between 0 and 100 only."""

    response = llm.invoke([SystemMessage(content=prompt)])
    return response.content.strip().lower()

# expected_responses = {
#         'carrier_confirmation': "Hey, just checking—are we confirmed for the pickup at Las Vegas, NV",
#         'load_picked': "Great! Did you pickup the load?",
#         'journey_started': "Perfect! Have you started your journey yet?",
#         'goodbye': "Thanks for confirming everything. Have a safe journey!"
#     }


# Add the backend directory to Python path
notebook_dir = Path().absolute()
backend_dir = notebook_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))



# Import database models
from db_models import Stop, get_db, Journey, JourneyState

load_dotenv()

class State(TypedDict):
   messages: Annotated[list, add_messages] = None
   stop_id: Optional[str] = None
   stop_data: Optional[dict] = None
   running: Optional[bool] = None
   carrier_confirmation: Optional[bool] = None
   dispatched: Optional[bool] = None
   have_loaded: Optional[bool] = None
   load_number: Optional[str] = None
   is_load_equal: Optional[bool] = None

graphbuilder = StateGraph(State)
json_parser = JsonOutputParser()
fmt = json_parser.get_format_instructions()
db = next(get_db())



def get_data_from_database(state: State) -> State:
    try:
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
    msg = llm.invoke([SystemMessage(content="Ask the carrier for their load number. Be friendly and professional.")])
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

def get_load_number(state: State) -> State:
    if state['messages'][-1].name == 'load_number':
        msg = llm.invoke([SystemMessage(content=FALLBACK_PROMPT.format(question=f"provide a valid load number  for the journey from {state['stop_data']['name']}")), *state['messages']])
        state['messages'].append(AIMessage(content=msg.content, name='load_number'))
    state = get_humanResponse(state, 'load_number')
    
    # Use LLM to check if response is affirmative or negative
    check_response = llm.invoke([
        SystemMessage(content=CLASSIFIER_PROMPT.format(question="Does the message contain a valid load number? Answer either yes or no.")),
        *state['messages']
    ])
    
    print('check_response::',check_response.content)
    response_type = format_classifier_text(check_response.content)
    if 'affirmative' in response_type:
        if state['load_number'].lower().strip().replace('-', '') in state['messages'][-1].content.lower().strip().replace('-', ''):
            # Ask for carrier confirmation
            confirmation_msg = llm.invoke([
                SystemMessage(content=CARRIER_CONFIRMATION_PROMPT.format(origin=state['stop_data']['name'])),
                *state['messages']
            ])
            return {
                **state,
                'messages': [*state['messages'],
                    AIMessage(content=confirmation_msg.content, name='carrier_confirmation')
                ],
                'is_load_equal': True
            }
        else:
            return {
                **state,
                'messages': [*state['messages'],
                    AIMessage(content='The load number is not correct, please contact the dispatch team.', name='load_number')
                ],
                'running': False
            }
    else:
        # Handle any response that doesn't clearly contain a load number
        msg = llm.invoke([SystemMessage(content=WAIT_PROMPT.format(reason="load number was not provided ")), *state['messages']])
        query = msg.content
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='load_number')
            ]
        }




def get_carrier_confirmation(state: State) -> State:
    if state['messages'][-1].name == 'carrier_confirmation' :
        msg = llm.invoke([SystemMessage(content=FALLBACK_PROMPT.format(question=f"if they have signed the carrier confirmation for the journey from {state['stop_data']['name']}")), *state['messages']])
        state['messages'].append(AIMessage(content=msg.content, name='carrier_confirmation'))
    state = get_humanResponse(state, 'carrier_confirmation')
    
    # Use LLM to check if response is affirmative or negative
    check_response = llm.invoke([
        SystemMessage(content=CLASSIFIER_PROMPT.format(question="signing carrier confirmation which can also be only yes or no")),
        *state['messages']
    ])
    
    response_type = format_classifier_text(check_response.content)
    if 'affirmative' in response_type:
        msg = llm.invoke([SystemMessage(content=LOADED_PROMPT),*state['messages']])
        query = msg.content
        print('loadedoutput query::',query)
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='ask_have_loaded')
            ],
            'carrier_confirmation': True,
        }
    elif 'negative' in response_type:
        msg = llm.invoke([SystemMessage(content=WAIT_PROMPT.format(reason="not signed the carrier confirmation")), *state['messages']])
        query = msg.content
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='wait')
            ]
        }
    return state

def get_have_loaded(state: State) -> State:
    if state['messages'][-1].name == 'have_loaded':
        msg = llm.invoke([SystemMessage(content=FALLBACK_PROMPT.format(question="loaded the cargo")),*state['messages']])
        state['messages'].append(AIMessage(content=msg.content, name='have_loaded'))
    state = get_humanResponse(state, 'have_loaded')
    
    # Use LLM to check if response is affirmative, negative, or unclear
    check_response = llm.invoke([
        SystemMessage(content=CLASSIFIER_PROMPT.format(question="loading cargo")),
        *state['messages']
    ])
    
    response_type = format_classifier_text(check_response.content)
    if 'affirmative' in response_type:
        msg = llm.invoke([SystemMessage(content= DISPATCHED_PROMPT.format(location=state['stop_data']['name']))])
        query = msg.content
        print('have_loaded output query::',query)
        return {   
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='ask_have_dispatched')
            ],
            'have_loaded': True,
            'dispatched': None,
        }
    elif 'negative' in response_type:
        msg = llm.invoke([SystemMessage(content=WAIT_PROMPT.format(reason="not loaded the cargo")), *state['messages']])
        query = msg.content
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='wait')
            ]
        }

def get_dispatched(state: State) -> State:
    if state['messages'][-1].name == 'dispatched':
        msg = llm.invoke([
            SystemMessage(content=FALLBACK_PROMPT.format(question=f"started the journey which can also be also yes or no")),
            *state['messages'],
        ])
        state['messages'].append(AIMessage(content=msg.content, name='dispatched'))
    state = get_humanResponse(state, 'dispatched')

    # Use LLM to check if response is affirmative, negative, or unclear
    check_response = llm.invoke([
        SystemMessage(content=CLASSIFIER_PROMPT.format(question="started the journey which can also be also yes or no")),
        *state['messages']
    ])

    response_type = format_classifier_text(check_response.content)
    logger.debug(f"LLM classified response as: {response_type}")
    if "affirmative" in response_type:
        query = llm.invoke([SystemMessage(content=GOODBYE_PROMPT), *state['messages']])
        query = query.content
        db.query(Journey).filter(Journey.id == 1).update({'current_state': JourneyState.TRANSIT.value})
        db.commit()
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='Goodbye')
            ],
            'dispatched': True,
            'running': False
        }
    elif "negative" in response_type:
        query = llm.invoke([SystemMessage(content=WAIT_PROMPT.format(reason="not started the journey")), *state['messages']])
        query = query.content
        return {
            **state,
            'messages': [*state['messages'],
                AIMessage(content=query, name='wait')
            ]
        }


def origin(state: State) -> State:
    return state

def router(state: State) -> State:
    if state['running'] == False:
        return 'end'
    elif state.get('is_load_equal') is None:
        return 'get_load_number'
    elif state.get('carrier_confirmation') is None:
        return 'get_carrier_confirmation'
    elif state.get('have_loaded') is None:
        return 'get_have_loaded'
    elif state.get('dispatched') is None:
        return 'get_dispatched'
    else:
        return 'end'


class OriginLangraph:
    def __init__(self):
        graphbuilder.add_node('greet', greet)
        graphbuilder.add_node('get_load_number', get_load_number)
        graphbuilder.add_node('get_carrier_confirmation', get_carrier_confirmation)
        graphbuilder.add_node('get_dispatched', get_dispatched)
        graphbuilder.add_node('get_have_loaded', get_have_loaded)
        graphbuilder.add_node('origin', origin)
        graphbuilder.add_node('get_data_from_database', get_data_from_database)
        graphbuilder.add_edge(START, 'get_data_from_database')
        graphbuilder.add_edge('get_data_from_database', 'greet')
        graphbuilder.add_edge('greet', 'origin')


        graphbuilder.add_conditional_edges(
            'origin',
            router,
            {
                'get_load_number': 'get_load_number',
                'get_carrier_confirmation': 'get_carrier_confirmation',
                'get_have_loaded': 'get_have_loaded',
                'get_dispatched': 'get_dispatched', 
                'end': END
            }
        )
        graphbuilder.add_edge('get_load_number', 'origin')
        graphbuilder.add_edge('get_carrier_confirmation', 'origin')
        graphbuilder.add_edge('get_have_loaded', 'origin')
        graphbuilder.add_edge('get_dispatched', 'origin')


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
    
    
origin_langgraph_service = OriginLangraph()

        
                

