import json
from typing import List, Dict, Any, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from state import AgentState
from tools import keyword_extractor_tool, rag_search_tool, _vector_store

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# --- Prompts ---

ISSUE_EXTRACTOR_SYSTEM_PROMPT = """You are an expert legal issue extractor. 
Your task is to analyze the user's case description and extract the core legal issues or questions that need to be answered.
Return the issues as a JSON list of strings.
Example Output: ["Was the termination wrongful?", "Does the contract clause apply?"]"""

EVALUATOR_SYSTEM_PROMPT = """You are a legal evaluator. 
Your task is to evaluate the relevance of the following retrieved cases to the current problem.
For each case, determine if it SUPPORTS, OPPOSES, or is NEUTRAL to the user's position (implied or stated).
Return the result as a JSON list of objects with keys: "case_id" (use the source or title), "relevance" (support/oppose/neutral), "reasoning".
"""

PRINCIPLE_SUMMARIZER_PROMPT = """You are a legal principle extractor.
Your task is to read the retrieved cases and extract the 'ratio decidendi' or core governing legal principles.
Focus on rules that answer the legal issues identified.
Return the output as a JSON list of objects with keys: "case_id", "principle".
"""

ARGUMENT_BUILDER_PROMPT = """You are a senior legal strategist.
Your task is to construct a structured legal argument outline based on the identified issues, retrieved cases, evaluations, and principles.
Structure the argument logically:
1. Issues
2. Supporting Precedents (and how to use them)
3. Opposing Precedents (and how to distinguish them)
4. Overall Strategy
Return the output in Markdown format.
"""

# --- Node Functions ---

def issue_extractor_agent(state: AgentState):
    case_desc = state["case_description"]
    messages = [
        SystemMessage(content=ISSUE_EXTRACTOR_SYSTEM_PROMPT),
        HumanMessage(content=case_desc)
    ]
    response = llm.invoke(messages)
    
    # Parse JSON output roughly
    content = response.content.strip()
    if content.startswith("```json"):
        content = content.replace("```json", "").replace("```", "")
    elif content.startswith("```"):
        content = content.replace("```", "")
        
    try:
        issues = json.loads(content)
        if not isinstance(issues, list):
            issues = [content] # Fallback
    except:
        issues = [content]
        
    return {"issues": issues}

def retrieval_agent(state: AgentState):
    """
    ReAct-style retrieval agent.
    It decides whether to extract keywords or search directly.
    It loops until it decides it has enough info.
    """
    messages = state.get("messages", [])
    if not messages:
        # Initial message if empty (shouldn't happen if we setup correctly, but safe fallback)
        messages = [HumanMessage(content=f"Find cases relevant to: {state['case_description']} Issues: {state['issues']}")]
    
    # We use a bind_tools approach for the ReAct loop
    tools = [keyword_extractor_tool, rag_search_tool]
    agent_model = llm.bind_tools(tools)
    
    # We'll rely on LangGraph's built-in loop via conditional edges, 
    # so this node just performs ONE step: Model -> (Tool Call or Final Answer)
    
    # However, to implement "ReAct" properly in a single node without graph cycles for every token, 
    # we can use the prebuilt 'create_react_agent' or just do a manual loop here 
    # if we want to capture the specific "thought" process logic described in the doc.
    
    # The doc describes: Thought -> Action -> Observation -> ...
    # Let's bind tools and let the model decide.
    
    response = agent_model.invoke(messages)
    
    # The output of this node will be appended to 'messages' in the graph state
    return {"messages": [response]}


def retrieval_node_tool_execution(state: AgentState):
    """
    Executes tools requested by the retrieval agent.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    outputs = []
    tool_calls = last_message.tool_calls
    
    retrieved_items = state.get("retrieved_cases", []) or []
    
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        if tool_name == "keyword_extractor_tool":
            res = keyword_extractor_tool.invoke(tool_args)
            outputs.append(ToolMessage(content=str(res), tool_call_id=tool_call["id"], name=tool_name))
            
        elif tool_name == "rag_search_tool":
            # For RAG search, we want to capture the structured results too, not just the string representation
            # But the tool returns a string.
            # We will manually peek into the vector store or parse the tool's return string if possible.
            # Simpler: The tool logic is imported. We can call the logic directly to get objects if needed, 
            # but that breaks the abstraction.
            # Let's rely on the text returned by the tool for now, 
            # OR we can assume the tool returns a rich JSON string that we parse.
            # Let's run the tool normally.
            res_str = rag_search_tool.invoke(tool_args)
            outputs.append(ToolMessage(content=res_str, tool_call_id=tool_call["id"], name=tool_name))
            
            # Heuristic: If we searched, let's assume valid results were found and add them to our "retrieved_cases" state
            # by parsing the string output or just trusting the text for now.
            # For a hackathon quality, parsing the string result is okay, 
            # OR we can update the RAG tool to help us. 
            # Re-implementing the search here to get objects:
            query = tool_args.get("query")
            if query:
                # Direct access to store to get proper metadata for downstream agents
                # This is "cheating" the tool abstraction but essential for the pipeline data flow
                docs = _vector_store.similarity_search(query, k=5)
                for d in docs:
                    # Avoid duplicates
                    if not any(existing['content'] == d.page_content for existing in retrieved_items):
                        retrieved_items.append({
                            "content": d.page_content,
                            "metadata": d.metadata,
                            "source": d.metadata.get("source", "Unknown")
                        })

    return {"messages": outputs, "retrieved_cases": retrieved_items}


def relevance_evaluator_agent(state: AgentState):
    cases = state.get("retrieved_cases", [])
    if not cases:
        return {"evaluations": []}
    
    # Format cases for LLM
    cases_text = "\n\n".join([f"ID: {c.get('source', 'Case ' + str(i))}\nContent: {c['content']}..." for i, c in enumerate(cases)])
    
    messages = [
        SystemMessage(content=EVALUATOR_SYSTEM_PROMPT),
        HumanMessage(content=f"User Case: {state['case_description']}\n\nRetrieved Cases:\n{cases_text}")
    ]
    
    response = llm.invoke(messages)
    content = response.content.strip().replace("```json", "").replace("```", "")
    
    try:
        evaluations = json.loads(content)
    except:
        evaluations = [{"error": "Failed to parse evaluations", "raw": content}]
        
    return {"evaluations": evaluations}


def principle_summarizer_agent(state: AgentState):
    cases = state.get("retrieved_cases", [])
    if not cases:
        return {"principles": []}
        
    cases_text = "\n\n".join([f"ID: {c.get('source', 'Case ' + str(i))}\nContent: {c['content']}..." for i, c in enumerate(cases)])
    
    messages = [
        SystemMessage(content=PRINCIPLE_SUMMARIZER_PROMPT),
        HumanMessage(content=f"Issues: {state['issues']}\n\nRetrieved Cases:\n{cases_text}")
    ]
    
    response = llm.invoke(messages)
    content = response.content.strip().replace("```json", "").replace("```", "")
    
    try:
        principles = json.loads(content)
    except:
        principles = [{"error": "Failed to parse principles", "raw": content}]
        
    return {"principles": principles}


def argument_builder_agent(state: AgentState):
    data_summary = (
        f"Issues: {json.dumps(state['issues'])}\n\n"
        f"Evaluations: {json.dumps(state['evaluations'])}\n\n"
        f"Principles: {json.dumps(state['principles'])}"
    )
    
    messages = [
        SystemMessage(content=ARGUMENT_BUILDER_PROMPT),
        HumanMessage(content=f"Case Description: {state['case_description']}\n\nAnalysis Data:\n{data_summary}")
    ]
    
    response = llm.invoke(messages)
    return {"argument_outline": response.content}

