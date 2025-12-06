import streamlit as st
import os
import json
from dotenv import load_dotenv

# Load env vars before importing other modules that might use them
load_dotenv()

from graph import app_graph
from langchain_core.messages import HumanMessage
import ingest_case_law

# Check if Qdrant DB exists, if not, ingest data
if not os.path.exists("./qdrant_db") or not os.listdir("./qdrant_db"):
    print("⚠️ Qdrant DB not found. Running ingestion (this may take a moment)...")
    ingest_case_law.ingest_data()

st.set_page_config(page_title="Legal Argument Builder", layout="wide")

st.title("⚖️ Legal Argument Builder Agent")
st.markdown("""
This AI agent helps lawyers build structured arguments by:
1. **Extracting issues** from your case description.
2. **Retrieving relevant case law** from a local database.
3. **Evaluating** the precedents (support/oppose).
4. **Summarizing principles** (ratio decidendi).
5. **Drafting a skeletal argument**.
""")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    st.info("Ensure you have run `ingest_case_law.py` at least once to populate the database.")

case_description = st.text_area(
    "Enter Case Description",
    height=200,
    placeholder="Example: Employee terminated without notice. Contract had 30-day notice clause. Can employee claim wrongful termination?"
)

if st.button("Build Argument", type="primary"):
    if not case_description:
        st.error("Please enter a case description.")
    elif not os.environ.get("OPENAI_API_KEY"):
        st.error("Please provide an OpenAI API Key in your .env file.")
    else:
        # containers for live updates
        status_container = st.status("Analyzing Case...", expanded=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Analysis Steps")
            issue_placeholder = st.empty()
            retrieval_placeholder = st.empty()
            eval_placeholder = st.empty()
            principle_placeholder = st.empty()
            
            # Initial states
            with issue_placeholder.container():
                 with st.expander("1. Identified Issues", expanded=False): st.write("Waiting...")
            with retrieval_placeholder.container():
                 with st.expander("2. Retrieved Precedents", expanded=False): st.write("Waiting...")
            with eval_placeholder.container():
                 with st.expander("3. Case Evaluation", expanded=False): st.write("Waiting...")
            with principle_placeholder.container():
                 with st.expander("4. Legal Principles", expanded=False): st.write("Waiting...")
            
        with col2:
            st.subheader("Draft Argument")
            argument_container = st.empty()
        
        # Run the graph
        inputs = {
            "case_description": case_description,
            "messages": [HumanMessage(content="Start analysis")] # Seed message for ReAct agent if needed
        }
        
        try:
            # Stream events to show progress
            for output in app_graph.stream(inputs):
                for node_name, state_update in output.items():
                    status_container.write(f"Completed step: **{node_name}**")
                    
                    if node_name == "issue_extractor":
                        issues = state_update.get("issues", [])
                        with issue_placeholder.container():
                            with st.expander(f"1. Identified Issues ({len(issues)})", expanded=True):
                                st.write(issues)
                        
                    elif node_name == "retrieval_agent":
                        pass
                        
                    elif node_name == "tool_execution":
                        pass
                        
                    # Check global state keys if present in update
                    if "retrieved_cases" in state_update:
                        cases = state_update["retrieved_cases"]
                        if cases:
                            with retrieval_placeholder.container():
                                with st.expander(f"2. Retrieved Precedents ({len(cases)})", expanded=True):
                                    for i, c in enumerate(cases):
                                        st.markdown(f"**Case {i+1}**: {c.get('source', 'Unknown')}")
                                        st.caption(f"{c['content'][:200]}...")

                    if "evaluations" in state_update:
                        evals = state_update["evaluations"]
                        with eval_placeholder.container():
                            with st.expander("3. Case Evaluation", expanded=True):
                                st.write(evals)

                    if "principles" in state_update:
                        principles = state_update["principles"]
                        with principle_placeholder.container():
                            with st.expander("4. Legal Principles", expanded=True):
                                st.write(principles)
                        
                    if "argument_outline" in state_update:
                        argument_container.markdown(state_update["argument_outline"])
                        status_container.update(label="Analysis Complete ✅", state="complete", expanded=False)
                        
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.warning("Make sure the Qdrant database is initialized and not locked.")
