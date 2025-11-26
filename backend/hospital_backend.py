import os
import re
from typing import Optional, List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_core.callbacks import BaseCallbackHandler


from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains import RetrievalQA

from crewai import Agent as CrewAIAgent, Task, Crew
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

DEFAULT_DB_URI = "postgresql+psycopg2://postgres:medical123@localhost:5432/medicaldb2"

APOLLO_POLICY_FILES: List[str] = [
    "human-rights-policy.pdf",
    "board-diversity-policy.pdf",
    "archival_policy_2023.pdf",
    "anti-bribery-and-anti-corruption-policy.pdf",
    "ahel-risk-management-policy.pdf",
    "ahel---prevention--prohibition-and-redressal-of-sexual-harassment-and-discrimination-at-workplace---2025.pdf",
]


# --------------------------------------------------------------------
# BASIC DB + LLM UTILITIES
# --------------------------------------------------------------------
class Settings(BaseModel):
    db_uri: str = Field(
        default=DEFAULT_DB_URI,
        description="SQLAlchemy/Postgres URI",
    )


def get_settings() -> Settings:
    uri = os.getenv("DB_URI") or DEFAULT_DB_URI
    return Settings(db_uri=uri)


def get_db() -> SQLDatabase:
    settings = get_settings()
    db = SQLDatabase.from_uri(settings.db_uri)
    return db


def get_llm() -> ChatOpenAI:
    """
    Create ChatOpenAI LLM for both Text2SQL and Intent Agent.
    """
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(
        model=model_name,
        temperature=0,
        streaming=False,
    )


class SQLQueryResult(BaseModel):
    question: str
    sql_query: str
    final_answer: str


def build_text2sql_agent():
    db = get_db()
    llm = get_llm()

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    sql_prefix = """
You are a STRICT PostgreSQL text-to-SQL agent for a hospital database.

REAL DATABASE TABLES (schema: public) and KEY COLUMNS (VERY IMPORTANT):

GENERAL RULES (VERY IMPORTANT):
- ALWAYS inspect the real schema using tools (sql_db_list_tables, sql_db_schema)
  before writing SQL.
- NEVER invent columns. Use ONLY columns that actually exist in the schema output.
- NEVER assume generic "id" columns on these tables:
  * patients uses patient_id
  * doctors uses doctor_id
  * diseases uses disease_id
  * appointments uses appointment_id
  * patient_conditions uses patient_conditions_id
- NEVER assume a disease_id column exists on patients. It does NOT.
- VERY IMPORTANT: When you provide Action Input, DO NOT surround it with extra quotes.
  For example:
    - Use: Action Input: patients
      NOT: Action Input: "patients"
    - Use: Action Input: SELECT COUNT(*) FROM patients;
      NOT: Action Input: "SELECT COUNT(*) FROM patients;"

----------------------------------------------------------------------
APPOINTMENT QUERIES (use appointments.encounter_date):

- For questions like:
    "how many appointments ... ?"
    "total number of appointments?"
  you MUST use the appointments table:

    SELECT COUNT(*) FROM appointments;

- For date ranges like "Show all appointments in January 2025 along with the patient names":

    SELECT
      p.name,
      a.encounter_date,
      a.status,
      a.reason
    FROM appointments a
    JOIN patients p ON p.patient_id = a.patient_id
    WHERE a.encounter_date >= '2025-01-01'
      AND a.encounter_date <  '2025-02-01'
    ORDER BY a.encounter_date;

- For upcoming appointments:

    SELECT
      p.name,
      a.encounter_date,
      a.status
    FROM appointments a
    JOIN patients p ON p.patient_id = a.patient_id
    WHERE a.encounter_date > NOW()
    ORDER BY a.encounter_date;

- DO NOT use a column named appointment_date (it does NOT exist).
  The correct column is appointments.encounter_date.

----------------------------------------------------------------------
DISEASE / CONDITION QUERIES (USE JOIN PATTERN BELOW):

For questions like:
  - "how many patients have diabetes?"
  - "how many patients have asthma?"
  - "list all patients who have hypertension"

YOU MUST USE THIS RELATIONSHIP:

  patients.patient_id
    -> patient_conditions.patient_id
    -> patient_conditions.disease_id
    -> diseases.disease_id

Correct count pattern (VERY IMPORTANT):

  SELECT COUNT(DISTINCT p.patient_id)
  FROM patients p
  JOIN patient_conditions pc ON p.patient_id = pc.patient_id
  JOIN diseases d ON pc.disease_id = d.disease_id
  WHERE LOWER(d.name) = 'diabetes';

Rules:
- Use COUNT(DISTINCT p.patient_id) to count patients.
- Use LOWER(d.name) = LOWER('<disease-name-from-question>') for matching.
- DO NOT filter by gender unless the user explicitly asks (e.g. "female patients with diabetes").
- DO NOT use disease_id directly on patients.
- DO NOT use a generic d.id or p.id column.

If user asks "List all patient_conditions with disease name and diagnosed_date":

  SELECT
    p.name,
    d.name AS disease_name,
    pc.onset_date AS diagnosed_date,
    pc.description,
    pc.status
  FROM patient_conditions pc
  JOIN patients p ON p.patient_id = pc.patient_id
  JOIN diseases d ON d.disease_id = pc.disease_id
  ORDER BY pc.onset_date DESC;

----------------------------------------------------------------------
MULTI-TABLE / GROUPING EXAMPLES (for complex queries):

1) "List all patients and their upcoming appointment dates.":

  SELECT
    p.name,
    a.encounter_date
  FROM patients p
  JOIN appointments a ON p.patient_id = a.patient_id
  WHERE a.encounter_date > NOW()
  ORDER BY a.encounter_date;

2) "For each patient, show their name and total number of appointments.":

  SELECT
    p.name,
    COUNT(a.appointment_id) AS total_appointments
  FROM patients p
  LEFT JOIN appointments a ON p.patient_id = a.patient_id
  GROUP BY p.patient_id, p.name
  ORDER BY total_appointments DESC;

3) "List patients who do not have any appointments.":

  SELECT
    p.name
  FROM patients p
  LEFT JOIN appointments a ON p.patient_id = a.patient_id
  WHERE a.appointment_id IS NULL;

4) "For each doctor, show their name and total number of appointments.":

  SELECT
    d.name,
    COUNT(a.appointment_id) AS total_appointments
  FROM doctors d
  LEFT JOIN appointments a ON d.doctor_id = a.practitioner_id
  GROUP BY d.doctor_id, d.name
  ORDER BY total_appointments DESC;

5) "List all patients who have at least one recorded condition. Show patient name and notes from patient_conditions.":

  SELECT DISTINCT
    p.name,
    pc.description AS condition_notes
  FROM patients p
  JOIN patient_conditions pc ON p.patient_id = pc.patient_id;

6) "Show all patient_conditions with disease name and diagnosed_date.":

  SELECT
    p.name,
    d.name AS disease_name,
    pc.onset_date AS diagnosed_date,
    pc.description,
    pc.status
  FROM patient_conditions pc
  JOIN patients p ON p.patient_id = pc.patient_id
  JOIN diseases d ON d.disease_id = pc.disease_id
  ORDER BY pc.onset_date DESC;

----------------------------------------------------------------------
COUNT RULES:

- When the user asks "how many ...", use a pure COUNT(*) or COUNT(DISTINCT ...) query, e.g.:

    SELECT COUNT(*) FROM patients;

- Do NOT add LIMIT or ORDER BY to pure COUNT queries, unless absolutely necessary.

----------------------------------------------------------------------
TOOL FORMAT (STRICT):

Thought: I should inspect the tables.
Action: sql_db_list_tables
Action Input: 

Thought: I should inspect the schema of the patients table.
Action: sql_db_schema
Action Input: patients

Thought: I now know the schema, I can query.
Action: sql_db_query
Action Input: SELECT COUNT(*) FROM patients;

Final Answer: <natural language answer here>

Rules:
- "Action:" and "Action Input:" MUST be on separate lines.
- You MUST always include an "Action Input:" line (but WITHOUT wrapping it in quotes).
- NEVER append tool outputs or extra sentences on the same line as Action Input.
- After thinking, ALWAYS run the SQL through the sql_db_query tool.
- If a SQL query fails because a column does not exist, DO NOT retry the same query.
  Instead, re-check the schema and fix the column name or answer describing the issue.
"""

    agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        prefix=sql_prefix,
    )
    return agent


def ask_text2sql_question(agent, question: str) -> SQLQueryResult:
    """
    Run the Text2SQL agent on a natural-language question and attempt to
    pull out the SQL query + final answer.
    """
    result = agent.invoke({"input": question})
    final_answer = result["output"]
    sql_query = "No SQL was executed for this question."

    if "intermediate_steps" in result:
        steps = result["intermediate_steps"]
        for step in reversed(steps):
            if isinstance(step, tuple) and len(step) == 2:
                tool_input = step[1]
                if isinstance(tool_input, str) and ("SELECT" in tool_input.upper()):
                    sql_query = tool_input
                    break

    return SQLQueryResult(
        question=question,
        sql_query=sql_query,
        final_answer=final_answer,
    )


# RAG SETUP FOR APOLLO POLICY DOCUMENTS
def load_policy_documents() -> List:
    """
    Load multiple policy PDFs and return a list of LangChain Documents.
    """
    all_docs = []
    for pdf_path in APOLLO_POLICY_FILES:
        if not os.path.exists(pdf_path):
            print(f"⚠️  Warning: Policy file not found: {pdf_path}")
            continue
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        all_docs.extend(docs)
    return all_docs


def build_policy_vectorstore():
    """
    Build a FAISS vectorstore from Apollo policy documents.
    """
    docs = load_policy_documents()
    if not docs:
        raise RuntimeError("No Apollo policy documents could be loaded.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
    )
    split_docs = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(split_docs, embeddings)
    return vectorstore


def build_policy_rag_chain() -> RetrievalQA:
    """
    Build a RetrievalQA chain over the Apollo policy documents.
    """
    vectorstore = build_policy_vectorstore()
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 4},
    )

    llm = get_llm()

    system_prompt = """
You are an assistant that answers questions strictly based on Apollo policy documents,
including (but not limited to):

- Apollo Human Rights Policy
- Board Diversity Policy
- Archival Policy
- Anti-bribery and Anti-corruption Policy
- AHEL Risk Management Policy
- Prevention, Prohibition and Redressal of Sexual Harassment and Discrimination at Workplace Policy.

RULES:
- If the answer is not clearly supported by the retrieved policy text, say you are not sure.
- Do NOT invent new policy details.
- If multiple policies conflict, mention that clearly.
"""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "Here are the relevant Apollo policy excerpts:\n\n{context}\n\n"
                "User question: {question}"
            ),
        ]
    )


    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=False,
    )
    return qa_chain


def ask_policy_question(qa_chain: RetrievalQA, question: str) -> str:
    """
    Ask a question about Apollo policy documents via the RAG chain.
    """
    result = qa_chain.invoke({"query": question})
    if isinstance(result, dict) and "result" in result:
        return result["result"]
    if isinstance(result, str):
        return result
    return "I could not confidently answer from the Apollo policy documents."


# INTENT AGENT (CrewAI) TO ROUTE: TEXT2SQL vs RAG vs OTHER
class SimpleLoggerCallback(BaseCallbackHandler):
    def on_llm_start(self, *args, **kwargs):
        print("\n--- Intent LLM START ---\n")

    def on_llm_end(self, *args, **kwargs):
        print("\n--- Intent LLM END ---\n")

    def on_llm_error(self, error, *args, **kwargs):
        print(f"\n--- Intent LLM ERROR: {error} ---\n")


def build_intent_crew(llm: ChatOpenAI) -> Crew:
    """
    Build a CrewAI "Intent Agent" that decides whether the query should go to:
    - TEXT2SQL_AGENT (hospital DB)
    - RAG_AGENT (Apollo policies)
    - OTHER_AGENT (out-of-context)
    """

    def text2sql_tool(user_query: str) -> str:
        """
        TOOL: TEXT2SQL_AGENT
        Use this tool ONLY when the user query is about hospital database
        records such as patients, doctors, staff, diseases, appointments,
        treatments, medicines, billing, diagnostic reports, etc.
        """
        return "TEXT2SQL_AGENT"

    def rag_tool(user_query: str) -> str:
        """
        TOOL: RAG_AGENT
        Use this tool ONLY when the user query is about Apollo policies,
        governance documents, board diversity, human rights, anti-bribery,
        archival rules, POSH (sexual harassment) or risk management.
        """
        return "RAG_AGENT"

    def other_tool(user_query: str) -> str:
        """
        TOOL: OTHER_AGENT
        Use this tool when the query is:
        - General medical knowledge (e.g., 'What is diabetes?')
        - Personal health advice (e.g., 'Should I take this medicine?')
        - Completely unrelated topics (e.g., 'Tell me a joke', 'Who is the PM of India?')
        """
        return "OTHER_AGENT"

    def text2sql_wrapper(user_query: str) -> str:
        return text2sql_tool(user_query)

    def rag_wrapper(user_query: str) -> str:
        return rag_tool(user_query)

    def other_wrapper(user_query: str) -> str:
        return other_tool(user_query)

    intent_system = """
You are the Intent Agent inside a hospital chatbot system.

High-level role:
- The user always talks to you first.
- Your only job is to:
  1. Read the user’s message.
  2. Decide which ROUTE label to output:
     - TEXT2SQL_AGENT   → hospital DATABASE questions.
     - RAG_AGENT        → Apollo policies / company policy questions.
     - OTHER_AGENT      → everything else (out of scope).

ROUTE TO TEXT2SQL_AGENT when:
- The user clearly asks about structured data stored in the hospital DATABASE,
  such as:
  - Number of patients, doctors, staff.
  - Appointments, diseases, diagnoses, treatments, medicines.
  - Billing, revenue, pending bills.
  - Any question that requires running SQL on tables like:
    patients, doctors, appointments, diseases, billing, staff,
    patient_conditions, patient_treatments, prescriptions, etc.
Examples:
- "How many patients are there in total?"
- "How many appointments are scheduled for today?"
- "List all patients with diabetes."
- "Show all appointments for Dr. Sharma tomorrow."
- "How many bills are pending payment?"
- "Average bill amount for admitted patients."
- "Total revenue from billing last month."

ROUTE TO RAG_AGENT when:
- The user is asking about Apollo policies, governance, procedures,
  rights, guidelines or company rules.
- The answer is expected from internal policy documents, such as:
  - Apollo Human Rights Policy
  - Board Diversity Policy
  - Archival policy
  - Anti-bribery and Anti-corruption Policy
  - Risk Management Policy
  - Prevention of Sexual Harassment (POSH) Policy
  - Any other Apollo corporate / compliance policy.
Examples:
- "What does Apollo's human rights policy say about research participants?"
- "Explain Apollo's board diversity policy."
- "What is the archival policy for 2023?"
- "What is Apollo’s anti-bribery and anti-corruption policy?"
- "What is the procedure for reporting sexual harassment at Apollo?"

ROUTE TO OTHER_AGENT when:
- The query is NOT about hospital database records AND
  NOT about Apollo policies / corporate policies.
- This includes:
  - General medical knowledge:
    - "What is a heart attack?"
    - "What are the symptoms of diabetes?"
  - Personal health advice:
    - "Should I take this medicine?"
    - "How do I cure a fever quickly?"
  - Completely unrelated topics:
    - "Tell me a joke."
    - "Who is the Prime Minister of India?"
    - "Explain quantum physics."

VERY IMPORTANT RULES:
- You MUST NOT hallucinate or answer questions yourself.
- You MUST NOT try to give database counts or policy summaries.
- Your ONLY job is routing: choose one of:
  - TEXT2SQL_AGENT
  - RAG_AGENT
  - OTHER_AGENT

User query:
{user_query}

OUTPUT FORMAT (STRICT):
- Respond with EXACTLY ONE of the following labels:
  - TEXT2SQL_AGENT
  - RAG_AGENT
  - OTHER_AGENT

No extra words, no explanations, no punctuation, no formatting.
Just a single label on its own line.
"""

    intent_agent = CrewAIAgent(
        role="Intent Agent",
        goal="Decide whether the query goes to TEXT2SQL_AGENT, RAG_AGENT, or OTHER_AGENT.",
        backstory=intent_system,
        verbose=True,
        llm=llm,
    )

    intent_task = Task(
        description=(
            "Given this user query, decide if it is for hospital DB (TEXT2SQL_AGENT), "
            "Apollo policies (RAG_AGENT), or out-of-context (OTHER_AGENT). "
            "Then call ONLY the chosen tool."
        ),
        agent=intent_agent,
        expected_output=(
            "Return exactly one label inside your response: "
            "TEXT2SQL_AGENT, RAG_AGENT, or OTHER_AGENT."
        ),
    )

    crew = Crew(
        agents=[intent_agent],
        tasks=[intent_task],
        verbose=True,
    )
    return crew


def route_with_intent(crew: Crew, user_query: str) -> str:
    """
    Run the Intent Agent via CrewAI to classify the user query.
    Returns one of:
      - "TEXT2SQL_AGENT"
      - "RAG_AGENT"
      - "OTHER_AGENT"
    """
    result = crew.kickoff(inputs={"user_query": user_query})
    label = str(result).strip().upper()

    if "TEXT2SQL_AGENT" in label:
        return "TEXT2SQL_AGENT"
    if "RAG_AGENT" in label:
        return "RAG_AGENT"
    return "OTHER_AGENT"


# SINGLE-QUERY ENTRY POINT + FASTAPI BACKEND (for UI integration)

_intent_crew_fastapi = None
_text2sql_agent_fastapi = None
_policy_rag_chain_fastapi = None


def _ensure_fastapi_agents_ready():
    """Lazy-init crews and chains used by the FastAPI /chat endpoint."""
    global _intent_crew_fastapi, _text2sql_agent_fastapi, _policy_rag_chain_fastapi

    if _text2sql_agent_fastapi is None:
        _text2sql_agent_fastapi = build_text2sql_agent()

    if _policy_rag_chain_fastapi is None:
        try:
            _policy_rag_chain_fastapi = build_policy_rag_chain()
        except Exception as e:
            print(
                "⚠️  Warning: Could not initialize Apollo policies RAG chain in FastAPI mode.\n"
                f"   Reason: {e}\n"
                "   RAG_AGENT route will not work until this is fixed.\n"
            )
            _policy_rag_chain_fastapi = None

    if _intent_crew_fastapi is None:
        llm = get_llm()
        _intent_crew_fastapi = build_intent_crew(llm)

def _clean_list_style_answer(text: str) -> str:
    """
    Clean the Text2SQL 'Final Answer' so that:
    - 'Final Answer:' prefix is removed
    - Header sentences like 'The patients and their conditions are as follows'
      or 'Here are 10 patients from the database' are removed
    - Numbering like '1. ', '2) ' etc. is stripped from each line
    - No HTML is added
    """
    if not text:
        return text

    text = re.sub(r"^Final Answer:\s*", "", text.strip(), flags=re.IGNORECASE)

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    cleaned_lines = []
    for ln in lines:
        lower_ln = ln.lower()

        if "the patients and their conditions are as follows" in lower_ln:
            continue
        if "here are" in lower_ln and "patients" in lower_ln:
            continue

        ln = re.sub(r"^\d+[\).\-\s]+", "", ln).strip()

        if not ln:
            continue

        cleaned_lines.append(ln)

    if not cleaned_lines:
        return text.strip()

    return "\n".join(cleaned_lines)

def answer_hospital_query(user_q: str) -> str:
    """Single entry point used by the FastAPI backend for each user query."""
    _ensure_fastapi_agents_ready()

    user_q = user_q.strip()
    if not user_q:
        return "Please enter a non-empty question."

    greetings = [
        "hi",
        "hello",
        "hey",
        "hey there",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "hii",
        "hiiii",
        "yo",
        "sup",
        "namaste",
    ]
    clean_msg = user_q.lower().strip()

    if any(clean_msg.startswith(g) for g in greetings) or clean_msg in greetings:
        return "Hello! 👋 How can I assist you today with hospital information or Apollo policies?"

    route = route_with_intent(_intent_crew_fastapi, user_q)

    if route == "TEXT2SQL_AGENT":
      try:
        result = ask_text2sql_question(_text2sql_agent_fastapi, user_q)

        cleaned_answer = _clean_list_style_answer(result.final_answer)
        return cleaned_answer

      except Exception as e:
        print(f"[FastAPI/Text2SQL] Error: {e}")
        return (
            "Sorry, there was an error while querying the hospital database. "
            "Please try again."
        )


    if route == "RAG_AGENT":
        if _policy_rag_chain_fastapi is None:
            return (
                "RAG is not initialized (policy documents are not loaded or there "
                "was an error in setup). Please contact the administrator."
            )
        try:
            answer = ask_policy_question(_policy_rag_chain_fastapi, user_q)
            return answer
        except Exception as e:
            print(f"[FastAPI/RAG] Error: {e}")
            return (
                "Sorry, there was an error while looking up the policy documents. "
                "Please try again."
            )

    return (
        "Your query is out of context for this hospital + policy chatbot. "
        "Please ask a question related to hospital database information "
        
    )


# ----------------------- FastAPI app definition -----------------------

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


app = FastAPI(title="Hospital + Apollo Policy Chatbot Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "hospital-policy-chatbot-backend"}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """Endpoint used by the React UI (MedicalBotUI.tsx)."""
    user_message = req.message
    try:
        reply_text = answer_hospital_query(user_message)
    except Exception as e:
        print(f"[FastAPI] Unhandled error while answering query: {e}")
        reply_text = (
            "Sorry, something went wrong while processing your request. "
            "Please try again in a moment."
        )
    return ChatResponse(reply=reply_text)


# MAIN LOOP: UI/CLI → Intent Agent → Text2SQL OR RAG OR Other

def main():
    text2sql_agent = build_text2sql_agent()

    try:
        policy_rag_chain = build_policy_rag_chain()
    except Exception as e:
        print(
            "⚠️  Warning: Could not initialize Apollo policies RAG chain.\n"
            f"   Reason: {e}\n"
            "   RAG_AGENT route will not work until this is fixed.\n"
        )
        policy_rag_chain = None

    intent_llm = get_llm()
    intent_crew = build_intent_crew(intent_llm)

    print("=== Hospital Chatbot (Intent Agent + Text2SQL + RAG) ===")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_q = input("User> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_q:
            continue
        if user_q.lower() in {"exit", "quit"}:
            print("Bye.")
            break

        # GREETING DETECTION (Intent Agent shortcut)
        greetings = [
            "hi",
            "hello",
            "hey",
            "hey there",
            "good morning",
            "good afternoon",
            "good evening",
            "how are you",
            "hii",
            "hiiii",
            "yo",
            "sup",
            "namaste",
        ]

        clean_msg = user_q.lower().strip()

        if any(clean_msg.startswith(g) for g in greetings) or clean_msg in greetings:
            print("Bot> Hello! 👋 How can I assist you today with hospital information?")
            continue

        route = route_with_intent(intent_crew, user_q)

        # TEXT2SQL: hospital DB route
        if route == "TEXT2SQL_AGENT":
            print("\n[Intent Agent] This is a hospital DATABASE question.")
            print("[Routing] → TEXT2SQL_AGENT\n")

            try:
                result = ask_text2sql_question(text2sql_agent, user_q)
                print("Answer:", result.final_answer)
                print("(SQL executed:", result.sql_query, ")")
            except Exception as e:
                print("Error while running Text2SQL agent:", e)

        elif route == "RAG_AGENT":
            print("\n[Intent Agent] This is an APOLLO POLICY question.")
            print("[Routing] → RAG_AGENT\n")

            if policy_rag_chain is None:
                print(
                    "RAG chain is NOT initialized. Cannot answer policy questions right now."
                )
            else:
                try:
                    answer = ask_policy_question(policy_rag_chain, user_q)
                    print("Answer:", answer)
                except Exception as e:
                    print("Error while running RAG chain:", e)

        else:
            print(
                "\n[Intent Agent] This query is NOT answerable from the hospital "
                "database or Apollo policy documents.\n"
            )
            print(
                "Your query is out of context for this hospital + policy chatbot.\n"
                "Please ask a question related to:\n"
                "- Hospital database information (patients, doctors, appointments, billing), OR\n"
                "- Apollo policy documents (human rights, board diversity, anti-bribery, POSH, risk, archival).\n"
            )


if __name__ == "__main__":
    main()
