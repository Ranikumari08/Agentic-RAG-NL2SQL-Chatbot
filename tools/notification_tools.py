"""
notification_tool.py
Sends a notification to a patient. No DB read is required for this
tool (it doesn't look anything up), but it does validate the patient
exists and generates a unique message_id per call instead of a static
placeholder.

Wire the `_dispatch` function to your actual SMS/email gateway (Twilio,
SES, etc.) — this stays a stand-in until that integration is added.
"""

from typing import Dict, Any
import uuid
from db import get_cursor


def _dispatch(patient_id: str, message: str, channel: str) -> bool:
    """
    Placeholder for the actual gateway call. Replace with e.g.:
        twilio_client.messages.create(to=phone, body=message)
    Returns True on success.
    """
    return True


def send_notification(
    patient_id: str,
    message: str,
    channel: str = "SMS",
) -> Dict[str, Any]:

    with get_cursor() as cur:
        cur.execute("SELECT 1 FROM patients WHERE patient_id = %s", (patient_id,))
        if not cur.fetchone():
            return {"status": "error", "message": f"Patient '{patient_id}' not found."}

    sent = _dispatch(patient_id, message, channel)
    message_id = f"MSG-{uuid.uuid4().hex[:10].upper()}"

    return {
        "status": "sent" if sent else "failed",
        "patient_id": patient_id,
        "channel": channel,
        "message": message,
        "message_id": message_id,
    }