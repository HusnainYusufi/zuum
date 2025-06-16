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
from langchain_core.prompts import PromptTemplate
from services.langrapghs.forms.config.prompts import system_prompt, analyse_prompt
from services.langrapghs.forms.config.output_format import at_pickup_output_format



class State(TypedDict):
   messages: Annotated[list, add_messages] = None
   purpose: Optional[list[str]] = None
   form_data: Optional[dict] = None
   result: Optional[dict] = None
   output_schema: Optional[dict] = None

graphbuilder = StateGraph(State)
json_parser = JsonOutputParser()
fmt = json_parser.get_format_instructions()



llm = ChatOpenAI(model="gpt-4o",temperature=0.6, api_key='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')



def get_system_prompt(state:State):
    systemPrompt = PromptTemplate(
        input_variables=[
          "purpose",
          "form_data",
        ],
        template=system_prompt,
    )
    formatted_prompt = systemPrompt.format_prompt(
        purpose=state['purpose'],
        form_data=state['form_data'],
    )
    return SystemMessage(content=formatted_prompt.to_string())


def get_human_response(state: State):
    response = interrupt(state['messages'][-1].content)
    return {**state,'messages': [*state['messages'], HumanMessage(content=response['data'])]}

def get_query(state: State):
    if len(state['messages']) > 0:
        state = get_human_response(state)
    query = llm.invoke([get_system_prompt(state), *state['messages']])
    return {**state, 'messages': [*state['messages'],query]}


def analyse_chat(state: State):
    prompt = PromptTemplate(
        input_variables=[
          "output_format",
          "format_instructions"
        ],
        template=analyse_prompt,
    )
    formatted_prompt = prompt.format_prompt(
        output_format=state.get('output_schema', {}),
        format_instructions=fmt
    )
    msg = llm.invoke([SystemMessage(content=formatted_prompt.to_string()), *state['messages']])
    return {**state, 'messages': [*state['messages'], AIMessage(content='You are all set, have a safe journey')], 'result': json_parser.parse(msg.content)}



def router(state: State):
    if 'end' in state['messages'][-1].content.lower():
        return 'analyse_chat'
    else:
        return 'get_query'
    

class forms_langraph:
    def __init__(self):
        graphbuilder.add_node('get_query', get_query)
        graphbuilder.add_node('analyse_chat', analyse_chat)
        graphbuilder.add_edge(START, 'get_query')
        graphbuilder.add_conditional_edges(
            'get_query',
            router,
            {
                'analyse_chat': 'analyse_chat',
                'get_query': 'get_query',
            }
        )
        graphbuilder.add_edge('analyse_chat', END)
        memory = MemorySaver()
        self.graph = graphbuilder.compile(checkpointer=memory)
    
    def run(self, state: State, thread_id: str):
        state = self.graph.invoke(state, {'configurable': {'thread_id': thread_id}})
        if state.get('__interrupt__') is not None:
            return {
                "type": "message",
                "content": state['__interrupt__'][0].value,
                "messages": state.get('messages', [])
            }
        else:
            return {
                "type": "result",
                "content": state['result'],
                "message": state.get('messages', [])[-1].content.replace('end', '').replace('"', '')
            }






forms_langraph_from_service = forms_langraph()
