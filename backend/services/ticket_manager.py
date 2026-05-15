import uuid
from datetime import datetime, timezone
from typing import Dict, List

# In-memory ticket database
_tickets: Dict[str, dict] = {}

def save_ticket(session_id: str, ticket_data: dict, phone_number: str = "Unknown") -> dict:
    """Save a newly generated ticket draft."""
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    
    ticket = {
        "ticket_id": ticket_id,
        "session_id": session_id,
        "phone_number": phone_number,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "OPEN",
        "category": ticket_data.get("category", "General"),
        "sub_category": ticket_data.get("sub_category", ""),
        "description": ticket_data.get("description", ""),
        "location": ticket_data.get("location", "Unknown"),
        "priority": ticket_data.get("priority", "normal").lower(),
        "language": ticket_data.get("language", "en"),
        "suggested_department": ticket_data.get("suggested_department", "General Administration")
    }
    
    _tickets[ticket_id] = ticket
    return ticket

def get_all_tickets() -> List[dict]:
    """Retrieve all tickets, newest first."""
    return sorted(_tickets.values(), key=lambda t: t["created_at"], reverse=True)
