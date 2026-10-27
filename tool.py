import os, datetime as dt
from dotenv import load_dotenv
from slack_sdk import WebClient
from email.utils import parseaddr, parsedate_to_datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))
TOKEN = os.path.join(BASE, "token.json")
CREDS = os.path.join(BASE, "credentials.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/calendar.readonly"]

def _google_creds():
    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(CREDS, SCOPES).run_local_server(port=0)
        open(TOKEN, "w").write(creds.to_json())
    return creds
def _short_date(s):
    try:
        return parsedate_to_datetime(s).astimezone().strftime("%d %b, %I:%M %p")
    except Exception:
        return s or ""

def _cell(t, n=70):
    t = (t or "").replace("|", "/").replace("\n", " ").strip()
    return t if len(t) <= n else t[:n - 1] + "…"

def _when(s):
    try:
        if "T" in s:
            return dt.datetime.fromisoformat(s).strftime("%a %d %b, %I:%M %p")
        return dt.date.fromisoformat(s).strftime("%a %d %b") + " (all day)"
    except Exception:
        return s

def search_gmail(query: str = "in:inbox", max_results: int = 5) -> str:
    """Search the user's Gmail and list matching emails. Use query "in:inbox" for recent emails, or Gmail syntax like 'from:sbi newer_than:7d' or 'is:unread'."""
    svc = build("gmail", "v1", credentials=_google_creds())
    ids = svc.users().messages().list(userId="me", q=query or "in:inbox",
                                      maxResults=max_results).execute().get("messages", [])
    if not ids:
        return "No emails found."
    rows = ["| # | From | Subject | Received |", "|---|---|---|---|"]
    for i, m in enumerate(ids, 1):
        msg = svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                         metadataHeaders=["From", "Subject", "Date"]).execute()
        h = {x["name"]: x["value"] for x in msg["payload"]["headers"]}
        name, addr = parseaddr(h.get("From", ""))
        rows.append(f"| {i} | {_cell(name or addr, 30)} | {_cell(h.get('Subject'), 80)} | {_short_date(h.get('Date'))} |")
    return f"**{len(ids)} emails:**\n\n" + "\n".join(rows)

def get_calendar_events(days: int = 7) -> str:
    """List upcoming meetings, events, holidays and festivals from ALL of the user's Google calendars for the next N days. Use for any question about schedule, meetings, holidays, festivals or the calendar."""
    svc = build("calendar", "v3", credentials=_google_creds())
    now = dt.datetime.now(dt.timezone.utc)
    end = now + dt.timedelta(days=days)
    rows = []
    for cal in svc.calendarList().list().execute().get("items", []):
        try:
            evs = svc.events().list(calendarId=cal["id"], timeMin=now.isoformat(),
                                    timeMax=end.isoformat(), singleEvents=True,
                                    orderBy="startTime").execute().get("items", [])
        except Exception:
            continue
        for e in evs:
            raw = e["start"].get("dateTime", e["start"].get("date"))
            rows.append((raw, f"- **{_when(raw)}**: {e.get('summary', '(no title)')} _({cal.get('summary')})_"))
    rows.sort()
    if not rows:
        return f"No events or holidays in the next {days} days."
    return f"**Next {days} days:**\n\n" + "\n".join(r[1] for r in rows)

if __name__ == "__main__":      # run once to authorize Google and test the tools
    _google_creds()
    print("Google authorized.")
    print(get_calendar_events(3))