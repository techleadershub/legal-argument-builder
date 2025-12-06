import operator
from typing import TypedDict, Annotated, List, Dict, Any, Union
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    case_description: str
    issues: List[str]
    # storing retrieved items. Each can be a dict or a Document object representation
    retrieved_cases: List[Dict[str, Any]] 
    evaluations: List[Dict[str, Any]]
    principles: List[Dict[str, Any]]
    argument_outline: str
    errors: List[str]
    # For ReAct agent (Retrieval Agent), we might need scratchpad or messages
    messages: Annotated[List[BaseMessage], operator.add]
