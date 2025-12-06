# ⚖️ Legal Argument Builder Agent

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_Workflow-green)
![Qdrant](https://img.shields.io/badge/Vector_DB-Qdrant-red)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-orange)

An advanced **multi-agent AI system** designed to assist legal professionals in researching case law, extracting legal principles, and drafting structured arguments.

Built with **LangChain**, **LangGraph**, and **Qdrant**, this application moves beyond simple RAG by orchestrating a graph of specialized agents that think, search, evaluate, and write like a legal research team.

---

## 🚀 Features

* **🔍 Issue Extraction** – Identifies core legal questions from raw case descriptions.
* **🤖 ReAct Retrieval Agent** – Performs iterative, reasoning-guided case law search.
* **📂 Semantic Search** – Uses **Qdrant** + OpenAI embeddings for meaning-based retrieval.
* **⚖️ Relevance Evaluation** – Determines whether retrieved cases support or oppose your position.
* **📝 Automated Drafting** – Produces a structured legal argument outline (skeleton argument).
* **📊 Transparent Workflow** – Streamlit UI visualizes the agent pipeline and decisions.

---

## 🧠 Architecture

The system uses a **LangGraph StateGraph**, where information flows through dedicated nodes:

1. **Issue Extractor** – User text → Legal issues
2. **ReAct Retrieval Agent** – Issues → Iterative case law search
3. **Relevance Evaluator** – Case summaries → Support/Oppose classification
4. **Principle Summarizer** – Extracts ratio decidendi & legal principles
5. **Argument Builder** – Synthesizes the final structured argument

---

## 🛠️ Installation & Setup

### **Prerequisites**

* Python **3.11+**
* OpenAI API key

---

### **1. Clone the repository**

```bash
git clone https://github.com/yourusername/legal-agent.git
cd legal-agent
```

### **2. Install dependencies**

```bash
pip install -r requirements.txt
```

*or using `uv`:*

```bash
uv sync
```

### **3. Configure environment**

Create a `.env` file:

```bash
OPENAI_API_KEY=sk-your-key-here
```

### **4. (Optional) Ingest new case law**

```bash
python ingest_case_law.py
```

This rebuilds the Qdrant vector index using files from the `data/` directory.

---

## 💻 Usage

Run the Streamlit app:

```bash
streamlit run app.py
```

Then:

1. Open **[http://localhost:8501](http://localhost:8501)**
2. Enter a case description
3. Click **Build Argument**
4. Watch the agent workflow unfold in real time

**Example input:**

> “My landlord evicted me without notice despite a 30-day termination clause. Is this wrongful eviction?”

---

## 📂 Project Structure

```
app.py              # Streamlit frontend
graph.py            # LangGraph workflow
agents.py           # Prompts + agent logic
tools.py            # Retrieval & Qdrant tools
ingest_case_law.py  # Data ingestion pipeline
data/               # Raw legal judgments
qdrant_db/          # Local vector database (SQLite)
```

---

## ⚠️ Disclaimer

This software is an AI prototype for **research and educational purposes only**.
It does **not** provide legal advice. Always consult a qualified lawyer for legal matters.

---

