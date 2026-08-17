"""Phase 3 adapters. Empty credentials intentionally return configuration_required."""
import httpx
from app.core.config import settings


async def dispatch(provider: str, payload: dict, target_url: str | None = None) -> dict:
    configurations = {
        "teams": settings.teams_webhook_url,
        "jira": settings.jira_base_url,
        "servicenow": settings.servicenow_base_url,
        "webhook": target_url or "",
    }
    endpoint = configurations[provider]
    if not endpoint:
        return {"status": "configuration_required", "provider": provider}
    headers = {}
    auth = None
    if provider == "jira": auth = (settings.jira_email, settings.jira_api_token)
    if provider == "servicenow": auth = (settings.servicenow_username, settings.servicenow_password)
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(endpoint, json=payload, headers=headers, auth=auth)
    return {"status": "sent" if response.is_success else "failed", "status_code": response.status_code, "body": response.text[:1000]}

