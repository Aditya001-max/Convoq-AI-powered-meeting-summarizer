"""
Google Calendar OAuth2 integration for Convoq.
Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.
Users must also enable the Google Calendar API and add
http://localhost:5000/calendar/callback as an authorised redirect URI.
"""

import os
from datetime import datetime, timezone
from flask import session, request, url_for

_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
_TOKEN_KEY = "google_credentials"


def _client_config():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def is_connected() -> bool:
    return _TOKEN_KEY in session and bool(session[_TOKEN_KEY])


def get_auth_url() -> str | None:
    config = _client_config()
    if not config:
        return None
    try:
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_config(config, scopes=_SCOPES)
        flow.redirect_uri = url_for("main.calendar_callback", _external=True)
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        session["oauth_state"] = state
        return auth_url
    except Exception as exc:
        print(f"[Convoq Calendar] Auth URL error: {exc}")
        return None


def exchange_code(code: str) -> bool:
    config = _client_config()
    if not config:
        return False
    try:
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_config(config, scopes=_SCOPES, state=session.get("oauth_state"))
        flow.redirect_uri = url_for("main.calendar_callback", _external=True)
        flow.fetch_token(code=code)
        creds = flow.credentials
        session[_TOKEN_KEY] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else _SCOPES,
        }
        return True
    except Exception as exc:
        print(f"[Convoq Calendar] Token exchange error: {exc}")
        return False


def _build_service():
    creds_data = session.get(_TOKEN_KEY)
    if not creds_data:
        return None
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials(
            token=creds_data["token"],
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data["token_uri"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            scopes=creds_data.get("scopes", _SCOPES),
        )
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception as exc:
        print(f"[Convoq Calendar] Service build error: {exc}")
        return None


def get_upcoming_events(max_results: int = 20) -> list:
    """Return the next N calendar events as plain dicts."""
    service = _build_service()
    if not service:
        return []
    try:
        now = datetime.now(timezone.utc).isoformat()
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = []
        for item in result.get("items", []):
            start = item["start"].get("dateTime", item["start"].get("date", ""))
            end = item["end"].get("dateTime", item["end"].get("date", ""))
            attendees = [
                a.get("displayName") or a.get("email", "")
                for a in item.get("attendees", [])
            ]
            events.append({
                "id": item.get("id"),
                "title": item.get("summary", "No title"),
                "start": start,
                "end": end,
                "location": item.get("location", ""),
                "meet_link": item.get("hangoutLink", ""),
                "attendees": attendees,
                "description": item.get("description", ""),
            })
        return events
    except Exception as exc:
        print(f"[Convoq Calendar] Events fetch error: {exc}")
        session.pop(_TOKEN_KEY, None)  # token likely expired/revoked
        return []
