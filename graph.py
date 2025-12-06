from langgraph.graph import StateGraph, START, END
from state import AgentState
from agents import (
    issue_extractor_agent,
    retrieval_agent,
    retrieval_node_tool_execution,
    relevance_evaluator_agent,
    principle_summarizer_agent,
    argument_builder_agent
)

def route_retrieval(state: AgentState):
    """
    Decide whether to loop back for tools or continue to evaluation.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    if last_message.tool_calls:
        return "tools"
    return "finalize"

# Initialize Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("issue_extractor", issue_extractor_agent)
workflow.add_node("retrieval_agent", retrieval_agent)
workflow.add_node("tool_execution", retrieval_node_tool_execution)
workflow.add_node("relevance_evaluator", relevance_evaluator_agent)
workflow.add_node("principle_summarizer", principle_summarizer_agent)
workflow.add_node("argument_builder", argument_builder_agent)

# Add Edges
workflow.add_edge(START, "issue_extractor")
workflow.add_edge("issue_extractor", "retrieval_agent")

# ReAct Loop Edges
workflow.add_conditional_edges(
    "retrieval_agent",
    route_retrieval,
    {
        "tools": "tool_execution",
        "finalize": "relevance_evaluator"
    }
)
workflow.add_edge("tool_execution", "retrieval_agent")

# Linear flow after Retrieval
workflow.add_edge("relevance_evaluator", "principle_summarizer")
workflow.add_edge("principle_summarizer", "argument_builder")
workflow.add_edge("argument_builder", END)

# Compile
app_graph = workflow.compile()
