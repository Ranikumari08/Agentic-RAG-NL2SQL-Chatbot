"""
tool_calling_agent.py
Wraps the existing tool functions (doctors_tools, appointment_tools,
pharmacy_tools, lab_tools, notification_tools — all already written and
tested via tools/test_tools.py) as LLM function-calling tools. The LLM
decides which tool(s) a query needs, we execute the real function
against Postgres, then the LLM turns the result into a natural-language
reply.

Exposes a single tool_calling_agent(query) function — same pattern as
agent/rag_agent.py and agent/nl2sql_agent.py — so the supervisor can
call all three sub-agents the same way.
"""

import os
import sys
import json

# tools/ lives one level up from agent/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from doctors_tools import check_doctor_availability  # noqa: E402
from appointment_tools import book_appointment, cancel_appointment  # noqa: E402
from pharmacy_tools import check_medicine_availability  # noqa: E402
from lab_tools import check_lab_test_availability  # noqa: E402
from notification_tools import send_notification  # noqa: E402

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_MODEL = "openai/gpt-oss-120b"
_llm_client = Groq(api_key=os.environ["GROQ_API_KEY"])

# --- Tool schema (Groq/OpenAI function-calling format) -------------------
# Descriptions here are what the LLM uses to decide WHEN to call a tool —
# keep them specific about what each tool does and doesn't cover, since
# vague descriptions cause the model to pick the wrong tool or miss an
# obvious call.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_doctor_availability",
            "description": (
                "Check a doctor's open appointment slots on a given date. "
                "Use this before booking, or whenever the user asks if a "
                "doctor is free / what slots are open."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "doctor_name": {"type": "string", "description": "Doctor's name, partial match ok"},
                    "doctor_id": {"type": "string", "description": "Doctor ID if known, e.g. D001"},
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "Book a new appointment for a patient with a doctor at a "
                "specific date and time. Only call this once the patient_id, "
                "doctor_id, date, and time are all known — ask the user for "
                "any that are missing rather than guessing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "doctor_id": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "HH:MM, 24-hour"},
                    "appointment_type": {"type": "string", "default": "Consultation"},
                    "booking_method": {"type": "string", "default": "Online"},
                    "reason_for_visit": {"type": "string"},
                },
                "required": ["patient_id", "doctor_id", "date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment by its appointment_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string", "description": "e.g. A0001"},
                },
                "required": ["appointment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_medicine_availability",
            "description": (
                "Check whether a medicine is in stock and its price. Matches "
                "on the generic medicine name (e.g. 'Metformin'), not a specific SKU."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "medicine_name": {"type": "string"},
                    "quantity": {"type": "integer", "description": "How many units the patient needs"},
                },
                "required": ["medicine_name", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_lab_test_availability",
            "description": (
                "Check availability, cost, and open slots for a lab test on a "
                "given date. Accepts common abbreviations like CBC, ECG, sugar test."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "test_name": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["test_name", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": (
                "Send an SMS/email reminder or message to a patient. Only call "
                "this if the user explicitly asks to notify/remind/message a patient."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "message": {"type": "string"},
                    "channel": {"type": "string", "enum": ["SMS", "Email"], "default": "SMS"},
                },
                "required": ["patient_id", "message"],
            },
        },
    },
]

# Maps tool name -> actual callable, so dispatch is a simple lookup
# instead of a long if/elif chain.
TOOL_FUNCTIONS = {
    "check_doctor_availability": check_doctor_availability,
    "book_appointment": book_appointment,
    "cancel_appointment": cancel_appointment,
    "check_medicine_availability": check_medicine_availability,
    "send_notification": send_notification,
    "check_lab_test_availability": check_lab_test_availability,
}

SYSTEM_PROMPT = """You are the action agent for Lifespring Clinic's assistant.
You handle bookings, cancellations, availability checks, and notifications
by calling the tools available to you. Never invent patient_id, doctor_id,
or appointment_id values — if one is required and the user hasn't given it,
ask for it instead of guessing or calling the tool with a made-up value.
After a tool call, summarize the result naturally — don't just repeat the
raw JSON back to the user.
"""

MAX_TOOL_ROUNDS = 4  # guard against a runaway tool-call loop


def _execute_tool_call(tool_call) -> dict:
    name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Could not parse tool arguments."}

    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return {"status": "error", "message": f"Unknown tool '{name}'."}

    try:
        return fn(**args)
    except Exception as e:
        return {"status": "error", "message": f"Tool '{name}' failed: {e}"}


def tool_calling_agent(query: str, return_debug: bool = False):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]
    tool_trace = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = _llm_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            # No more tools requested — this is the final natural-language answer.
            answer = msg.content
            if return_debug:
                return {"answer": answer, "tool_calls": tool_trace}
            return answer

        # The model wants to call one or more tools. Execute each, then
        # feed the results back so it can either call more tools or
        # produce the final answer on the next loop iteration.
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            result = _execute_tool_call(tc)
            tool_trace.append({"tool": tc.function.name, "args": tc.function.arguments, "result": result})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, default=str),
            })

    # Hit MAX_TOOL_ROUNDS without a final answer — avoid looping forever.
    answer = "I wasn't able to complete that after several tool calls — could you rephrase or simplify the request?"
    if return_debug:
        return {"answer": answer, "tool_calls": tool_trace}
    return answer


if __name__ == "__main__":
    test_queries = [
        "Is Dr. Ayesha Kapoor free on 2026-10-05?",
        "Do you have Metformin in stock, I need 20 tablets",
        "Book patient P001 with doctor D001 on 2026-10-05 at 10:00, routine checkup",
        "What's the weather like today?",  # should NOT call any tool
    ]
    for q in test_queries:
        print(f"\nQ: {q}")
        result = tool_calling_agent(q, return_debug=True)
        print("Tool calls:", [(t["tool"], t["args"]) for t in result["tool_calls"]])
        print("Answer:", result["answer"])