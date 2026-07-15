from datetime import date, datetime, time
from typing import Optional
from utils.db import get_current_user_id
from dao import calendar_dao


class CalendarService:
    """
    日历服务 — 统一管理日程事件，排除忙碌时段。
    支持来源：本地（manual）、Google Calendar API、CalDAV。
    """

    def __init__(self, user_id=None):
        self.user_id = user_id if user_id is not None else get_current_user_id()

    def add_event(self, title, start_time, end_time, source="manual", is_busy=True, external_id=None):
        calendar_dao.add_calendar_event(
            self.user_id, source, title, start_time, end_time, is_busy, external_id
        )

    def get_events(self, dt: Optional[date] = None, include_manual=True):
        if dt is None:
            dt = date.today()
        return calendar_dao.get_events_by_date(self.user_id, dt, include_manual)

    def get_events_in_range(self, start_date, end_date, include_manual=True):
        return calendar_dao.get_events_by_range(self.user_id, start_date, end_date, include_manual)

    def get_busy_slots(self, dt: Optional[date] = None) -> list[tuple[datetime, datetime]]:
        events = self.get_events(dt)
        return [
            (datetime.fromisoformat(e.start_time), datetime.fromisoformat(e.end_time))
            for e in events
        ]

    def get_available_slots(self, dt: Optional[date] = None,
                            work_start_h=9, work_end_h=18,
                            lunch_start_h=12, lunch_end_h=13,
                            work_start_m=0, work_end_m=0,
                            lunch_start_m=0, lunch_end_m=0) -> list[tuple[datetime, datetime]]:
        if dt is None:
            dt = date.today()
        base = datetime.combine(dt, time())
        work_slots = [
            (base.replace(hour=work_start_h, minute=work_start_m),
             base.replace(hour=lunch_start_h, minute=lunch_start_m)),
            (base.replace(hour=lunch_end_h, minute=lunch_end_m),
             base.replace(hour=work_end_h, minute=work_end_m)),
        ]
        busy_slots = self.get_busy_slots(dt)
        available = []
        for ws_start, ws_end in work_slots:
            current = ws_start
            for bs_start, bs_end in sorted(busy_slots):
                if bs_end <= current:
                    continue
                if bs_start >= ws_end:
                    break
                if current < bs_start:
                    available.append((current, min(bs_start, ws_end)))
                current = max(current, bs_end)
            if current < ws_end:
                available.append((current, ws_end))
        return available

    def delete_event(self, event_id):
        calendar_dao.delete_calendar_event(event_id, self.user_id)

    def _sync_events(self, events: list[dict], source: str):
        calendar_dao.sync_events(self.user_id, events, source)

    def sync_google_calendar(self, google_events: list[dict]):
        self._sync_events(google_events, 'google')

    def sync_caldav(self, caldav_events: list[dict]):
        self._sync_events(caldav_events, 'caldav')


class GoogleCalendarClient:
    """Google Calendar API 客户端封装。"""

    def __init__(self, credentials_path=None, token_path=None):
        self.credentials_path = credentials_path
        self.token_path = token_path

    def fetch_events(self, dt: date, calendar_id='primary') -> list[dict]:
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import os.path
            import pickle
        except ImportError:
            return []

        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        creds = None

        if self.token_path and os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if self.credentials_path and os.path.exists(self.credentials_path):
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    return []
            if self.token_path:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)

        try:
            service = build('calendar', 'v3', credentials=creds)
            start_of_day = datetime.combine(dt, datetime.min.time()).isoformat() + 'Z'
            end_of_day = datetime.combine(dt, datetime.max.time()).isoformat() + 'Z'
            events_result = service.events().list(
                calendarId=calendar_id, timeMin=start_of_day, timeMax=end_of_day,
                singleEvents=True, orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            return [
                {
                    "id": e.get('id', ''),
                    "title": e.get('summary', ''),
                    "start": e['start'].get('dateTime', e['start'].get('date')),
                    "end": e['end'].get('dateTime', e['end'].get('date')),
                }
                for e in events if 'dateTime' in e.get('start', {})
            ]
        except Exception:
            return []


class CalDAVClient:
    """CalDAV 协议客户端封装。"""

    def __init__(self, url="", username="", password=""):
        self.url = url
        self.username = username
        self.password = password

    def fetch_events(self, dt: date) -> list[dict]:
        try:
            import caldav
            from caldav.elements import dav, cdav
        except ImportError:
            return []

        if not self.url or not self.username:
            return []

        try:
            client = caldav.DAVClient(url=self.url, username=self.username, password=self.password)
            principal = client.principal()
            calendars = principal.calendars()
            if not calendars:
                return []
            start = datetime.combine(dt, datetime.min.time())
            end = datetime.combine(dt, datetime.max.time())
            results = []
            for cal in calendars:
                events = cal.date_search(start=start, end=end)
                for e in events:
                    results.append({
                        "id": str(e.data.find('.//{DAV:}href') or ''),
                        "title": str(e.data.find('.//{DAV:}displayname') or ''),
                        "start": str(e.data.find('.//{CALDAV:}dtstart') or ''),
                        "end": str(e.data.find('.//{CALDAV:}dtend') or ''),
                    })
            return results
        except Exception:
            return []