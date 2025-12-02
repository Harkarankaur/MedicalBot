import os
import re
from typing import Optional, List,Tuple
import uuid
import hashlib
import base64
import psycopg2
from psycopg2.extras import RealDictCursor
from passlib.context import CryptContext
from datetime import datetime
import urllib.parse as urlparse

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text as sql_text, Column, Integer, String, Text, DateTime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, declarative_base

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
from fastapi import FastAPI , HTTPException
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

DEFAULT_DB_URI = "postgresql+psycopg2://postgres:medical123@localhost:5432/my_new_db"

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

_sql_engine = None  # global cache for SQLAlchemy Engine


def get_sql_engine():
    """Get or create a singleton SQLAlchemy engine using the same DB URI."""
    global _sql_engine
    if _sql_engine is None:
        settings = get_settings()
        _sql_engine = create_engine(settings.db_uri)
    return _sql_engine


# 🔽🔽🔽 PASTE THIS BLOCK HERE 🔽🔽🔽

def get_pg_connection():
    """
    Low-level psycopg2 connection used for auth/search history endpoints.
    Uses the same DB_URI / DEFAULT_DB_URI as SQLAlchemy.
    """
    db_url = os.getenv("DB_URI") or DEFAULT_DB_URI
    url = urlparse.urlparse(db_url)
    return psycopg2.connect(
        database=url.path[1:],          # strip leading '/'
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        cursor_factory=RealDictCursor,
    )


# Password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash any length password safely for bcrypt.
    Steps:
    1. Encode to bytes.
    2. If >72 bytes, SHA256 it.
    3. Base64 encode to keep it ASCII.
    4. Decode back to string and hash with passlib.
    """
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = hashlib.sha256(password_bytes).digest()
        password_bytes = base64.b64encode(password_bytes)
    safe_password = password_bytes.decode("utf-8")
    return pwd_context.hash(safe_password)


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored hash.
    Uses the same SHA256 + base64 pre-processing as hash_password.
    """
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = hashlib.sha256(password_bytes).digest()
        password_bytes = base64.b64encode(password_bytes)
    safe_password = password_bytes.decode("utf-8")
    return pwd_context.verify(safe_password, hashed)




# --------------------------------------------------------------------
# CHAT HISTORY ORM (chat_messages + chat_context)
# --------------------------------------------------------------------
Base = declarative_base()
SessionLocal = sessionmaker(bind=get_sql_engine())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String(100), index=True, nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=sql_text("CURRENT_TIMESTAMP"))


class ChatContext(Base):
    __tablename__ = "chat_context"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String(100), unique=True, nullable=False)
    last_entity_type = Column(String(50), nullable=True)
    last_sql_query = Column(Text, nullable=True)
    last_patient_ids = Column(Text, nullable=True)  # comma-separated IDs


def init_chat_history_tables():
    """
    Ensure the chat_messages and chat_context tables exist.
    Safe to call multiple times.
    """
    engine = get_sql_engine()
    Base.metadata.create_all(bind=engine)


def get_chat_history(chat_id: str, limit: int = 10) -> List[dict]:
    """
    Return the last `limit` messages for this chat_id as:
      [{"role": "user"|"assistant", "content": "..."}]
    """
    session = SessionLocal()
    try:
        q = (
            session.query(ChatMessage)
            .filter(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.id.asc())
        )
        msgs = q.all()
        msgs = msgs[-limit:]
        return [{"role": m.role, "content": m.content} for m in msgs]
    finally:
        session.close()


def save_chat_turn(chat_id: str, user_q: str, answer: str) -> None:
    """Save one user → assistant turn into chat_messages."""
    session = SessionLocal()
    try:
        session.add(ChatMessage(chat_id=chat_id, role="user", content=user_q))
        session.add(ChatMessage(chat_id=chat_id, role="assistant", content=answer))
        session.commit()
    finally:
        session.close()


def get_last_context(chat_id: str) -> dict:
    """
    Return last context dict for this chat_id, or {} if nothing stored.
    """
    session = SessionLocal()
    try:
        ctx = (
            session.query(ChatContext)
            .filter(ChatContext.chat_id == chat_id)
            .first()
        )
        if not ctx:
            return {}
        ids = ctx.last_patient_ids.split(",") if ctx.last_patient_ids else []
        ids = [i for i in ids if i]
        return {
            "last_entity_type": ctx.last_entity_type,
            "last_sql_query": ctx.last_sql_query,
            "last_patient_ids": ids,
        }
    finally:
        session.close()


def update_last_context(
    chat_id: str,
    *,
    entity_type: Optional[str],
    sql_query: Optional[str],
    patient_ids: Optional[List[int]],
) -> None:
    """
    Upsert row in chat_context for this chat_id.
    """
    session = SessionLocal()
    try:
        ctx = (
            session.query(ChatContext)
            .filter(ChatContext.chat_id == chat_id)
            .first()
        )
        ids_str = ",".join(str(p) for p in (patient_ids or []))
        if ctx is None:
            ctx = ChatContext(
                chat_id=chat_id,
                last_entity_type=entity_type,
                last_sql_query=sql_query,
                last_patient_ids=ids_str,
            )
            session.add(ctx)
        else:
            ctx.last_entity_type = entity_type
            ctx.last_sql_query = sql_query
            ctx.last_patient_ids = ids_str
        session.commit()
    finally:
        session.close()


def infer_entity_and_ids(
    sql_query: Optional[str],
    table_dict: Optional[dict],
) -> Tuple[Optional[str], List[int]]:
    """
    Very light-weight heuristic:
    - entity_type based on table name in the SQL.
    - patient_ids parsed from a column named 'patient_id' or 'id'.
    """
    entity_type: Optional[str] = None
    ids: List[int] = []

    if sql_query:
        lower = sql_query.lower()
        for name in ["patients", "doctors", "appointments", "bills", "staff"]:
            if f" {name}" in lower or f"{name} " in lower:
                entity_type = name
                break

    if table_dict:
        cols = [c.lower() for c in table_dict.get("columns", [])]
        values = table_dict.get("values", [])
        idx = None
        for candidate in ["patient_id", "id"]:
            if candidate in cols:
                idx = cols.index(candidate)
                break
        if idx is not None:
            for row in values:
                try:
                    ids.append(int(row[idx]))
                except Exception:
                    continue

    return entity_type, ids



def build_table_from_sql(sql_query: str):
    """
    Execute a SELECT SQL query and convert the result into
    { "columns": [...], "values": [[...], ...] }.
    Returns None if SQL is empty / not SELECT / execution fails.
    """
    if not sql_query:
        return None

    normalized = sql_query.strip().lower()
    if not normalized.startswith("select"):
        # We only build table data for SELECT queries
        return None

    try:
        engine = get_sql_engine()
        with engine.connect() as conn:
            result = conn.execute(sql_text(sql_query))
            rows = result.fetchall()
            columns = list(result.keys())
    except SQLAlchemyError as e:
        print(f"[FastAPI/Text2SQL] Error executing SQL for table data: {e}")
        return None
    except Exception as e:
        print(f"[FastAPI/Text2SQL] Unexpected error executing SQL for table data: {e}")
        return None

    # Convert every row to a list of strings so JSON is clean
    values = [[str(cell) for cell in row] for row in rows]
    return {"columns": columns, "values": values}


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
- don't show these lines "The names of 10 patients are:" in the final answer.
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
        handle_parsing_errors=True
    )
    return agent


def ask_text2sql_question(agent, question: str) -> SQLQueryResult:
    """
    Run the Text2SQL agent on a natural-language question and attempt to
    pull out the SQL query + final answer.

    If the agent fails with an OUTPUT_PARSING_FAILURE, we try to salvage the
    natural-language answer from the error and still return it.
    """
    try:
        # Normal path: agent returns a dict with "output" + "intermediate_steps"
        result = agent.invoke({"input": question})
    except Exception as e:
        print(f"[TEXT2SQL] Agent error while invoking: {e}")
        fallback_answer = _extract_answer_from_parsing_error(e)

        if fallback_answer:
            # We couldn't reliably recover the SQL, but we *do* have a good
            # natural-language answer. Return that so the UI shows something.
            return SQLQueryResult(
                question=question,
                sql_query="(unavailable due to output parsing error)",
                final_answer=fallback_answer,
            )

        # No usable answer – re-raise so the caller can show a generic error.
        raise

    # If we get here, result is a normal successful agent output
    final_answer = result["output"]

    # Try to reconstruct the SQL query from intermediate_steps
    thoughts = result.get("intermediate_steps", [])
    sql_query = ""
    for step in thoughts:
        action = step[0]
        if hasattr(action, "tool") and action.tool == "sql_db_query":
            sql_query = action.tool_input

    return SQLQueryResult(
        question=question,
        sql_query=sql_query,
        final_answer=final_answer,
    )


def _extract_answer_from_parsing_error(err: Exception) -> Optional[str]:
    """
    If the Text2SQL agent crashes with an OUTPUT_PARSING_FAILURE, the nice
    natural-language answer is often inside backticks in the error message.
    This helper pulls that out so we can still show it to the user.
    """
    msg = str(err)

    # Only try to parse if it's clearly an output parsing error
    if "Could not parse LLM output" not in msg and "Parsing LLM output" not in msg:
        return None

    first = msg.find("`")
    last = msg.rfind("`")
    if first == -1 or last == -1 or last <= first:
        return None

    extracted = msg[first + 1 : last].strip()
    return extracted or None


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

def generate_other_agent_reply(user_q: str) -> str:
    """
    Use the LLM (via prompts) to handle greetings, small talk and
    out-of-scope queries for the hospital chatbot.

    Behaviour:
    - If the message is a greeting (with or without a name), reply politely.
      If a name is present like "hi am Vaibhav", include it in the reply,
      e.g. "Hello Vaibhav, how can I help you today?".
    - If it is casual small talk ("how are you", "what's up"), respond
      politely and then guide the user back to hospital / policy questions.
    - If it is completely out of scope (jokes, politics, random topics),
      politely say it is outside the scope of this hospital + policy chatbot.

    All behaviour here is controlled by the prompt; there is NO hard-coded
    greeting logic elsewhere.
    """
    llm = get_llm()

    prompt = f"""
You are the 'Other Agent' for a hospital + Apollo policy chatbot.

Your job now:
- The Intent Agent has already decided this user message is NOT a hospital
  database question and NOT a policy question.
- You must give a friendly, natural language reply.

Rules:
1) GREETINGS WITH NAME
   - If the message is a greeting that also mentions a name, like:
       "hi am Vaibhav"
       "hi i am Vaibhav"
       "hello, this is Vaibhav"
       "hey my name is Vaibhav"
   - Extract the name and respond like:
       "Hello Vaibhav, how can I help you today?"
   - Keep it short and friendly.

2) SIMPLE GREETINGS (NO NAME)
   - If it is just "hi", "hello", "hey", "good morning", "how are you", etc.,
     respond with a warm greeting such as:
       "Hello! How can I help you today with hospital or Apollo policy information?"

3) SMALL TALK
   - For things like "how are you":
       - Answer briefly (e.g. "I'm doing well, thanks for asking!")
       - Then guide them: "How can I help you with hospital or policy information?"

4) OUT OF SCOPE
   - If the message is clearly not about hospital or Apollo policies, and
     not just a greeting (for example: politics, random jokes, unrelated facts),
     reply politely:
       - Explain that the chatbot is focused only on hospital database
         information and Apollo policy documents.
       - Ask them to rephrase or ask something in scope.

VERY IMPORTANT:
- Do NOT invent database numbers or policy details here.
- Do NOT pretend to answer medical or policy questions in detail.
- Focus only on greetings, small talk and out-of-scope explanation.

User message:
{user_q}

Now write ONE friendly assistant reply:
"""

    response = llm.invoke(prompt)
    # ChatOpenAI returns an AIMessage; fall back to str() if needed.
    try:
        return response.content.strip()
    except AttributeError:
        return str(response).strip()

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

GREETINGS & SMALL TALK:
- If the user message is primarily a greeting or simple small talk, such as:
  - "hi", "hello", "hey", "hey there"
  - "good morning", "good afternoon", "good evening"
  - "namaste", "yo", "sup", "hii", "hiiii"
  - "how are you", "what's up"
- OR if it is a greeting that also includes the user’s name, for example:
  - "hi i am Vaibhav"
  - "hi am Vaibhav"
  - "hi i'm Vaibhav"
  - "hello, this is Vaibhav"
  - "hey, my name is Vaibhav"
- Then you MUST route to: OTHER_AGENT.
- When you route such a greeting to OTHER_AGENT, you MUST pass the
  full original user message (do NOT remove or change the name).
- The downstream OTHER_AGENT / code will generate a friendly reply that uses
  the user’s name when present, e.g.:
  - "Hello Vaibhav how can I help you?"
- Do NOT route greetings to TEXT2SQL_AGENT or RAG_AGENT.

VERY IMPORTANT RULES:
- For database or policy questions, you MUST NOT answer yourself.
- For database or policy questions, your ONLY job is routing:
  choose one of:
  - TEXT2SQL_AGENT
  - RAG_AGENT
  - OTHER_AGENT
- For pure greetings and greeting+name messages, you still ONLY do
  routing (you do not answer yourself), but you MUST classify them as
  OTHER_AGENT so the greeting logic can respond.


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
    

    try:
        init_chat_history_tables()
    except Exception as e:
        print(f"[FastAPI] Could not initialize chat history tables: {e}")


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

from typing import List  # already imported at line 688

# ...

def answer_hospital_query(user_q: str, chat_id: Optional[str] = None) -> "ChatResponse":
    """Single entry point used by the FastAPI backend for each user query."""
    _ensure_fastapi_agents_ready()

    # Normalise the text
    user_q = user_q.strip()
    if not user_q:
        return ChatResponse(
            result="Please enter a non-empty question.",
            data=[],
        )

    # --- Load recent history + last context (if we have a chat_id) ---
    history: List[dict] = []
    last_ctx: dict = {}
    if chat_id:
        try:
            history = get_chat_history(chat_id, limit=10)
            last_ctx = get_last_context(chat_id)
        except Exception as e:
            print(f"[FastAPI] Failed to load chat history for chat_id={chat_id}: {e}")

    # Build an augmented query that includes recent history + last context as hint
    augmented_q = user_q
    if history or last_ctx:
        history_lines = [
            f"{m['role']}: {m['content']}"
            for m in history[-6:]
        ]
        history_block = "\n".join(history_lines)
        ctx_block = ""
        if last_ctx:
            ctx_block = (
                "\n\nLast DB context (may be useful, but can be ignored if irrelevant): "
                f"entity_type={last_ctx.get('last_entity_type')}, "
                f"last_sql_query={last_ctx.get('last_sql_query')}, "
                f"last_patient_ids={last_ctx.get('last_patient_ids')}"
            )

        augmented_q = (
            f"{history_block}{ctx_block}\n\nCurrent user question: {user_q}"
            if history_block or ctx_block
            else user_q
        )

    # -------- INTENT AGENT ROUTING --------
    route = route_with_intent(_intent_crew_fastapi, augmented_q)
    print(route)
    # TEXT2SQL route
    if route == "TEXT2SQL_AGENT":
        try:
            sql_result = ask_text2sql_question(_text2sql_agent_fastapi, augmented_q)
            # sql_result is SQLQueryResult(question, sql_query, final_answer)
            print(sql_result)
            table_dict = build_table_from_sql(sql_result.sql_query)
            print(table_dict)
            tables: List[TableData] = []
            if table_dict is not None:
                tables.append(TableData(**table_dict))

            response = ChatResponse(
                result=sql_result.final_answer,
                data=tables,
                route=route,
            )

            # Persist conversation + context
            if chat_id:
                try:
                    save_chat_turn(chat_id, user_q, response.result)
                except Exception as e:
                    print(f"[FastAPI] Failed to save chat turn: {e}")

                try:
                    entity_type, patient_ids = infer_entity_and_ids(
                        sql_result.sql_query,
                        table_dict,
                    )
                    update_last_context(
                        chat_id=chat_id,
                        entity_type=entity_type,
                        sql_query=sql_result.sql_query,
                        patient_ids=patient_ids,
                    )
                except Exception as e:
                    print(f"[FastAPI] Failed to update last context: {e}")

            return response,route
        except Exception as e:
            # ✅ NEW: try to salvage the natural-language answer from parsing errors
            msg = str(e)
            if "OUTPUT_PARSING_FAILURE" in msg or "Could not parse LLM output" in msg:
                extracted = None

                # Often the raw LLM output is wrapped in backticks `...`
                if "`" in msg:
                    parts = msg.split("`")
                    if len(parts) >= 3:
                        extracted = parts[1]

                fallback_answer = extracted or (
                    "I ran a database query but there was a formatting error while "
                    "parsing the answer. Here is the raw message:\n" + msg
                )

                response = ChatResponse(result=fallback_answer, data=[],route=route,)
                if chat_id:
                    try:
                        save_chat_turn(chat_id, user_q, response.result)
                    except Exception as e2:
                        print(f"[FastAPI] Failed to save chat turn after parsing error: {e2}")
                return response,route

            # If it's some other kind of error, keep the old behaviour
            print(f"[FastAPI/TEXT2SQL_AGENT] Error: {e}")
            return ChatResponse(
                result=(
                    "There was an error while querying the hospital database. "
                    "Please rephrase your question or try again."
                ),
                data=[],
                route=route,
            )

    # RAG route
    if route == "RAG_AGENT":
        if _policy_rag_chain_fastapi is None:
            response = ChatResponse(
                result=(
                    "RAG is not initialized (policy documents are not loaded or there "
                    "was an error in setup). Please contact the administrator."
                ),
              route=route,
            )
            if chat_id:
                try:
                    save_chat_turn(chat_id, user_q, response.result)
                except Exception as e:
                    print(f"[FastAPI] Failed to save chat turn for RAG_AGENT: {e}")
            return response,route

        try:
            answer = ask_policy_question(_policy_rag_chain_fastapi, augmented_q)
            response = ChatResponse(result=answer, data=[],route=route,)
            if chat_id:
                try:
                    save_chat_turn(chat_id, user_q, response.result)
                except Exception as e:
                    print(f"[FastAPI] Failed to save chat turn for RAG_AGENT: {e}")
            return response,route
        except Exception as e:
            print(f"[FastAPI/RAG] Error: {e}")
            return ChatResponse(
                result=(
                    "Sorry, there was an error while looking up the policy documents. "
                    "Please try again."
                ),
                data=[],
                route=route,
            )

    # OTHER_AGENT route (greetings, small talk, out-of-scope)
    if route == "OTHER_AGENT":
        try:
            reply = generate_other_agent_reply(augmented_q)
            response = ChatResponse(result=reply, data=[],route=route)
            if chat_id:
                try:
                    save_chat_turn(chat_id, user_q, response.result)
                except Exception as e:
                    print(f"[FastAPI] Failed to save chat turn for OTHER_AGENT: {e}")
            return response,route
        except Exception as e:
            print(f"[FastAPI/OTHER_AGENT] Error: {e}")
            return ChatResponse(
                result=(
                    "I’m here to help with hospital database information and Apollo "
                    "policy documents. Please try asking a hospital or policy question."
                ),
                data=[],
                route=route,
            )







# ----------------------- FastAPI app definition -----------------------

# Pydantic models for tables and chat API

class TableData(BaseModel):
    columns: List[str]
    values: List[List[str]]  # always stringified for JSON cleanliness


class ChatRequest(BaseModel):
    """
    Incoming request from the UI for /chat.

    - message: user text
    - chat_id: string ID for this conversation (UI passes Date.now() as string)
    - history: (optional) list of previous messages from the UI. We accept it
      for compatibility, but the backend primarily uses DB-based chat history
      (chat_messages + chat_context).
    """
    message: str
    chat_id: Optional[str] = None
    username: str
    email: str



class ChatResponse(BaseModel):
    chat_id: Optional[str] = None
    # Summary / natural language answer (e.g., "10 patients having diabetes")
    result: str
    # Optional list of tables (for Text2SQL-style answers).
    # For greetings / RAG / out-of-context, this will usually be [].
    data: List[TableData] = []
    route: str 


class SearchQuery(BaseModel):
    query: str
    user_email: str = "guest"


class SignUpRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str



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


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """Endpoint used by the React UI (MedicalBotUI.tsx)."""
    user_message = req.message.strip()
    # Use chat_id from the UI if provided; otherwise create a new one
    chat_id = req.chat_id or str(uuid.uuid4())
    user_email = req.email
    name = req.username
    try:
        response,route = answer_hospital_query(user_message, chat_id=chat_id)
    except Exception as e:
        print(f"[FastAPI] Unhandled error while answering query: {e}")
        response = ChatResponse(
            result=(
                "Sorry, something went wrong while processing your request. "
                "Please try again in a moment."
            ),
            data=[],
        )
        route = "UNKNOWN"
    conn = get_pg_connection()
    cursor = conn.cursor()
    try:
        # Save USER message
        cursor.execute(
            "INSERT INTO chat_history (chat_id, user_email, sender, message,route, timestamp,username) VALUES (%s,%s, %s, %s, %s, %s, %s)",
            (chat_id, user_email, "user", user_message,route, datetime.now(),name)
        )
        # Save BOT reply ← bot_reply is the parameter/variable name
        cursor.execute(
            "INSERT INTO chat_history (chat_id, user_email, sender, message,route, timestamp,username) VALUES (%s,%s, %s, %s, %s, %s, %s)",
            (chat_id, user_email, "bot", response.result,route, datetime.now(),name)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return ChatResponse(
    result=response.result,
    data=response.data,
    route=route
)

@app.post("/signup")
def signup(req: SignUpRequest):
    conn = get_pg_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM user_login WHERE username = %s OR email = %s",
            (req.username, req.email),
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail="Username or email already exists",
            )

        hashed_password = hash_password(req.password)
        cursor.execute(
            "INSERT INTO user_login (username, email, password_hash, created_at) "
            "VALUES (%s, %s, %s, %s)",
            (req.username, req.email, hashed_password, datetime.now()),
        )
        conn.commit()
        return {"message": "User created successfully"}
    finally:
        cursor.close()
        conn.close()


@app.post("/login")
def login(req: LoginRequest):
    conn = get_pg_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM user_login WHERE username = %s",
            (req.username,),
        )
        user = cursor.fetchone()
        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return {"message": "Login successful", "email": user["email"]}
    finally:
        cursor.close()
        conn.close()


@app.post("/save-chat")
async def save_chat_history(chat: ChatRequest, user_email: str = "guest"):
    conn = get_pg_connection()
    cursor = conn.cursor()
    chat_id = chat.chat_id or int(datetime.now().timestamp() * 1000)
    try:
        cursor.execute(
            "INSERT INTO chat_history (chat_id, user_email, sender, message, timestamp) "
            "VALUES (%s, %s, %s, %s, %s)",
            (chat_id, user_email, "user", chat.message, datetime.now()),
        )
        conn.commit()
        return {"status": "saved", "chat_id": chat_id}
    finally:
        cursor.close()
        conn.close()


@app.post("/save-search")
async def save_search(search: SearchQuery):
    conn = get_pg_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO chat_history (chat_id, user_email, sender, message, route, timestamp) "
            "VALUES (0, %s, %s, %s, %s, %s)",
            (search.user_email, "search", search.query, "search", datetime.now()),
        )
        conn.commit()
        return {"status": "saved"}
    finally:
        cursor.close()
        conn.close()


@app.get("/load-search-history")
async def load_search_history(user_email: str = "guest"):
    conn = get_pg_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT message as query, timestamp FROM chat_history "
            "WHERE user_email = %s AND sender = 'search' "
            "ORDER BY timestamp DESC LIMIT 10",
            (user_email,),
        )
        results = [
            {"query": row["query"], "timestamp": str(row["timestamp"])}
            for row in cursor.fetchall()
        ]
        return results
    finally:
        cursor.close()
        conn.close()


@app.get("/load-chat-history")
async def load_chat_history(user_email: str = "guest", chat_id: Optional[int] = None):
    conn = get_pg_connection()
    cursor = conn.cursor()
    try:
        if chat_id:
            cursor.execute(
                "SELECT sender, message, route, timestamp "
                "FROM chat_history "
                "WHERE user_email = %s AND chat_id = %s "
                "ORDER BY timestamp",
                (user_email, chat_id),
            )
        else:
            cursor.execute(
                "SELECT DISTINCT chat_id, MAX(timestamp) as last_message "
                "FROM chat_history "
                "WHERE user_email = %s "
                "GROUP BY chat_id "
                "ORDER BY last_message DESC LIMIT 10",
                (user_email,),
            )
        results = [dict(row) for row in cursor.fetchall()]
        return results
    finally:
        cursor.close()
        conn.close()




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