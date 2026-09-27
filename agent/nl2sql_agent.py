"""
nl2sql_agent.py
Standalone NL2SQL agent: takes a natural-language question, generates a
SQL query against the Lifespring Postgres schema, validates it's a safe
read-only SELECT, executes it via tools/db.py's existing connection
pool, and returns a natural-language answer.

Exposes a single nl2sql_agent(question) function so this can be tested
in isolation before the supervisor calls it as a sub-agent — same
pattern as agent/rag_agent.py.
"""

import os
import re
import sys
import json

# tools/db.py lives one level up from agent/ — add it to the path so
# `from db import get_cursor` resolves the same connection pool used by
# doctors_tools.py, appointment_tools.py, etc, instead of opening a new one.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from db import get_cursor  # noqa: E402

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_MODEL = "openai/gpt-oss-120b"
_llm_client = Groq(api_key=os.environ["GROQ_API_KEY"])

# --- Schema description --------------------------------------------------
# Confirmed against the real Postgres schema via schema_check.py — column
# names, types, and nullability match exactly what insert_data.py implied.
SCHEMA_DESCRIPTION = """
departments(department_id varchar, department_name varchar, location varchar)

doctors(doctor_id varchar, doctor_name varchar, specialization varchar,
        qualification varchar, experience_years int, consultation_fee numeric,
        department_id varchar, joining_date date)
    -- department_id references departments(department_id)

patients(patient_id varchar, first_name varchar, last_name varchar,
          date_of_birth date, gender varchar, phone varchar, email varchar,
          city varchar, registration_date date, blood_group varchar,
          insurance_provider varchar)

appointments(appointment_id varchar, patient_id varchar, doctor_id varchar,
             appointment_date date, appointment_time time, appointment_type varchar,
             status varchar, booking_method varchar, reason_for_visit text)
    -- appointment_date and appointment_time are SEPARATE columns (date + time,
    --    not a single timestamp) — filter/compare them separately
    -- status is one of: Scheduled, Completed, Cancelled, No-show
    -- patient_id references patients(patient_id)
    -- doctor_id references doctors(doctor_id)

billing(bill_id varchar, patient_id varchar, appointment_id varchar,
        bill_date date, consultation_fee numeric, lab_charges numeric,
        medicine_charges numeric, discount numeric, insurance_coverage numeric,
        total_amount numeric, payment_method varchar, payment_status varchar)
    -- payment_status is one of: Paid, Pending
    -- appointment_id references appointments(appointment_id)

lab_tests(test_id varchar, patient_id varchar, appointment_id varchar,
          test_name varchar, test_category varchar, test_date date,
          result text, normal_range varchar, status varchar, cost numeric)

medical_records(record_id varchar, patient_id varchar, appointment_id varchar,
                 doctor_id varchar, diagnosis varchar, symptoms text,
                 record_date date, severity varchar, notes text)
    -- severity is one of: Mild, Moderate, Severe

medications(medication_id varchar, medication_name varchar, category varchar,
            manufacturer varchar, unit_price numeric, stock_quantity int)

prescriptions(prescription_id varchar, patient_id varchar, doctor_id varchar,
              appointment_id varchar, medication_id varchar, dosage varchar,
              frequency varchar, duration_days int, prescription_date date)
    -- medication_id references medications(medication_id)
"""

# Few-shot examples covering single-table lookups and multi-table joins.
# Add more here as you find questions the agent gets wrong — this list
# is the main lever for improving accuracy, more so than prompt wording.
FEW_SHOT_EXAMPLES = """
Q: What is Dr. Ayesha Kapoor's consultation fee?
SQL: SELECT consultation_fee FROM doctors WHERE doctor_name ILIKE '%Ayesha Kapoor%';

Q: How many appointments does doctor D001 have that are still scheduled?
SQL: SELECT COUNT(*) FROM appointments WHERE doctor_id = 'D001' AND status = 'Scheduled';

Q: What appointments does Dr. Mehta have tomorrow, and at what times?
SQL: SELECT a.appointment_time, a.patient_id FROM appointments a JOIN doctors d ON a.doctor_id = d.doctor_id WHERE d.doctor_name ILIKE '%Mehta%' AND a.appointment_date = CURRENT_DATE + INTERVAL '1 day' ORDER BY a.appointment_time;

Q: What is patient P001's total pending bill amount?
SQL: SELECT SUM(total_amount) FROM billing WHERE patient_id = 'P001' AND payment_status = 'Pending';

Q: List all medications that are out of stock.
SQL: SELECT medication_name, manufacturer FROM medications WHERE stock_quantity = 0;

Q: Which patients were diagnosed with Diabetes?
SQL: SELECT DISTINCT p.first_name, p.last_name FROM patients p JOIN medical_records mr ON p.patient_id = mr.patient_id WHERE mr.diagnosis ILIKE '%Diabetes%';

Q: What lab tests did patient P271 take and what were the results?
SQL: SELECT test_name, result, test_date FROM lab_tests WHERE patient_id = 'P271' ORDER BY test_date DESC;

Q: How much revenue did the clinic collect from paid bills in total?
SQL: SELECT SUM(total_amount) FROM billing WHERE payment_status = 'Paid';

Q: Which doctor has treated the most patients in the Cardiology department?
SQL: SELECT d.doctor_name, COUNT(DISTINCT a.patient_id) AS patient_count FROM doctors d JOIN departments dep ON d.department_id = dep.department_id JOIN appointments a ON d.doctor_id = a.doctor_id WHERE dep.department_name = 'Cardiology' GROUP BY d.doctor_name ORDER BY patient_count DESC LIMIT 1;
"""

SYSTEM_PROMPT = f"""You are a PostgreSQL query generator for Lifespring Clinic's database.

Schema:
{SCHEMA_DESCRIPTION}

Rules:
- Output ONLY the SQL query. No explanation, no markdown code fences, no comments.
- Always end the query with a semicolon.
- Only generate SELECT queries. Never INSERT, UPDATE, DELETE, DROP, ALTER, or any
  data-modifying statement — if the question implies a write action (booking,
  cancelling, prescribing), respond with exactly: NOT_A_QUERY
- Use ILIKE for name/text matching so case differences don't cause misses.
- Use table aliases and explicit JOIN ... ON clauses for multi-table questions.
- If the question is ambiguous or can't be answered from this schema, respond
  with exactly: NOT_A_QUERY

Examples:
{FEW_SHOT_EXAMPLES}
"""

# --- Safety guard ---------------------------------------------------------
# Anything other than a single, plain SELECT is rejected before it ever
# reaches the database. This is a second line of defense in addition to
# the system prompt — a prompt can be worked around, this check can't.
FORBIDDEN_KEYWORDS = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE|MERGE|CALL)\b',
    re.IGNORECASE,
)


def is_safe_select(sql: str) -> bool:
    stripped = sql.strip().rstrip(";").strip()

    if not stripped:
        return False
    if not re.match(r'^\s*SELECT\b', stripped, re.IGNORECASE):
        return False
    if FORBIDDEN_KEYWORDS.search(stripped):
        return False
    # Reject stacked statements (a second statement after a semicolon) —
    # only one trailing semicolon at the very end is allowed.
    if ";" in stripped:
        return False
    return True


def generate_sql(question: str) -> str:
    response = _llm_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Q: {question}\nSQL:"},
        ],
        temperature=0,  # deterministic — SQL generation shouldn't be creative
    )
    sql = response.choices[0].message.content.strip()
    # strip markdown fences in case the model adds them despite instructions
    sql = re.sub(r'^```sql\s*|^```\s*|```$', '', sql, flags=re.MULTILINE).strip()
    return sql


def execute_query(sql: str):
    with get_cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def summarize_results(question: str, sql: str, rows) -> str:
    """Turn raw rows into a natural-language answer via the LLM."""
    rows_json = json.dumps(rows, default=str)[:4000]  # cap payload size
    response = _llm_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": (
                "You answer the user's question using ONLY the query results "
                "given. Be concise and natural — don't mention SQL or the "
                "database. If the results are empty, say so plainly. "
                "All monetary amounts in this database are in Indian Rupees — "
                "always format them with the ₹ symbol (e.g. ₹800.00), never $."
            )},
            {"role": "user", "content": (
                f"Question: {question}\nQuery results: {rows_json}"
            )},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def nl2sql_agent(question: str, return_debug: bool = False):
    sql = generate_sql(question)

    if sql.strip() == "NOT_A_QUERY" or not is_safe_select(sql):
        answer = (
            "I can only answer questions by looking up existing data — "
            "I can't make bookings, updates, or changes through this. "
            "Try rephrasing as a lookup, or use the appointment/pharmacy "
            "tools for actions."
        )
        if return_debug:
            return {"answer": answer, "sql": sql, "rows": None}
        return answer

    try:
        rows = execute_query(sql)
    except Exception as e:
        answer = "I couldn't run that query against the database. Could you rephrase the question?"
        if return_debug:
            return {"answer": answer, "sql": sql, "error": str(e)}
        return answer

    answer = summarize_results(question, sql, rows)

    if return_debug:
        return {"answer": answer, "sql": sql, "rows": rows}
    return answer


if __name__ == "__main__":
    test_questions = [
        "What is Dr. Ayesha Kapoor's consultation fee?",
        "How much does patient P001 owe in pending bills?",
        "Which medications are out of stock?",
        "Book me an appointment with Dr. Kapoor tomorrow",  # should be refused
    ]
    for q in test_questions:
        print(f"\nQ: {q}")
        result = nl2sql_agent(q, return_debug=True)
        print("SQL:", result.get("sql"))
        print("Answer:", result["answer"])