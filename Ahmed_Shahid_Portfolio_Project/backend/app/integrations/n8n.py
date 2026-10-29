"""Authenticated outbound calls to optional n8n webhook workflows."""
from __future__ import annotations
import asyncio, logging, uuid
import httpx
from app.core.config import N8N_CONTACT_WEBHOOK_URL, N8N_REVIEW_WEBHOOK_URL, N8N_ADMIN_WEBHOOK_URL, N8N_WEBHOOK_TOKEN

logger = logging.getLogger("portfolio.n8n")

def _url_for(event_type: str) -> str:
    return {
        "contact.created": N8N_CONTACT_WEBHOOK_URL,
        "review.created": N8N_REVIEW_WEBHOOK_URL,
        "admin.updated": N8N_ADMIN_WEBHOOK_URL,
    }.get(event_type, "")

async def send_event(event_type: str, payload: dict, event_id: str | None = None) -> bool:
    url = _url_for(event_type)
    if not url or not N8N_WEBHOOK_TOKEN:
        logger.info("n8n integration not configured for event=%s", event_type)
        return False
    event_id = event_id or str(uuid.uuid4())
    headers = {"X-Portfolio-Token": N8N_WEBHOOK_TOKEN, "Idempotency-Key": event_id}
    body = {"event": event_type, "event_id": event_id, "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), "data": payload}
    # Two brief retries for transient failures. The stable event_id and Idempotency-Key
    # allow an n8n workflow or downstream service to deduplicate retries.
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(4.0)) as client:
                response = await client.post(url, json=body, headers=headers)
            if 200 <= response.status_code < 300:
                return True
            if response.status_code < 500 or attempt == 2:
                logger.warning("n8n delivery failed event=%s status=%s", event_type, response.status_code)
                return False
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt == 2:
                logger.warning("n8n delivery unavailable event=%s type=%s", event_type, type(exc).__name__)
                return False
        await asyncio.sleep(0.2 * (attempt + 1))
    return False
