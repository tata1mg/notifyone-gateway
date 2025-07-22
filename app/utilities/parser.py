from typing import Dict

class V2PayloadParser:
    """
    Parses V2 Payload
    V2: {
        "app_name": app_name,
        "event_name": event_name,
        "to": {
            "email": email,
            "mobile": mobile,
        },
        "email": {
            "subject": email_subject,
            "cc": email_cc,
            "bcc": email_bcc,
        },
        "whatsapp": {"body_values": whatsapp_body_values},
        "attachments": attachments,
        "filename": attachments_filename,
        "body": {},
    }
    """

    @classmethod
    def parse(cls, payload: Dict) -> Dict:
        """
        Parse payload for V2 format
        """

        # If payload doesn't `to` field and `email` is string
        # then treat the payload as v1
        if not payload.get("to") and isinstance(payload.get("email"), str):
            return cls._handle_v1_payload(payload)
        # else return as it is
        return payload

    @classmethod
    def _handle_v1_payload(cls, payload: Dict) -> Dict:
        """
        Handle V1 payload and convert to V2 payload

        V1: {
            "app_name": app_name,
            "event_name": event_name,
            "email": email,
            "mobile": mobile,
            "attachments": attachments,
            "filename": attachments_filename,
            "whatsapp": {"body_values": whatsapp_body_values},
            "body": {},
        }
        """

        email = payload.get("email")
        mobile = payload.get("mobile")

        return {
            **payload,
            "to": {"email": email, "mobile": mobile},
            "email": {"subject": None, "cc": None, "bcc": None},
        }

