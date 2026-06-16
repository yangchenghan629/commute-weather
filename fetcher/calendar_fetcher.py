# fetcher/calendar_fetcher.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "token.json")
CREDS_PATH = os.path.join(os.path.dirname(__file__), "..", "credentials.json")

def get_calendar_service():
    creds = None

    # 從環境變數讀取 token（GitHub Actions 和 Render 都用這個）
    token_json = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json:
        import json
        creds = Credentials.from_authorized_user_info(
            json.loads(token_json), SCOPES
        )

    # 本機環境：從檔案讀取
    elif os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists(TOKEN_PATH):
            # 只有本機才能互動式授權
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
            auth_url, _ = flow.authorization_url(prompt="consent")
            print(f"\n請用瀏覽器開啟此網址授權：\n{auth_url}\n")
            code = input("授權完成後，把網頁上的授權碼貼在這裡：").strip()
            flow.fetch_token(code=code)
            creds = flow.credentials
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        else:
            raise Exception("無法取得 Google 授權，請設定 GOOGLE_TOKEN_JSON 環境變數")

    return build("calendar", "v3", credentials=creds)

def get_upcoming_events(hours_ahead=24):
    service = get_calendar_service()
    now = datetime.now(timezone.utc)
    time_max = now + timedelta(hours=hours_ahead)

    result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = result.get("items", [])
    return events

# 測試
if __name__ == "__main__":
    print("讀取 Google Calendar 行程...")
    events = get_upcoming_events()
    if not events:
        print("未來 24 小時沒有行程")
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date"))
        name = e.get("summary", "（無標題）")
        location = e.get("location", "（無地點）")
        print(f"{start} | {name} | {location}")