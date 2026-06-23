import os
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_calendar_service():
    """用 Service Account 建立 Google Calendar 連線（不需要用戶 token）"""
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise Exception("找不到 GOOGLE_SERVICE_ACCOUNT_JSON 環境變數")

    info = json.loads(sa_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds)


def get_upcoming_events(hours_ahead=24, calendar_id="primary"):
    """
    查詢指定 calendar_id 的未來行程。
    calendar_id 由用戶提供，存在 Redis，不需要儲存任何 token。
    """
    service = get_calendar_service()
    now = datetime.now(timezone.utc)
    time_max = now + timedelta(hours=hours_ahead)

    try:
        result = service.events().list(
            calendarId=calendar_id,
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "notFound" in error_msg:
            raise Exception("找不到行事曆，請確認 Calendar ID 是否正確，或是否已分享給 Service Account")
        if "403" in error_msg or "forbidden" in error_msg:
            raise Exception("無法存取行事曆，請確認已將行事曆分享給 Service Account（僅限查看）")
        raise

    return result.get("items", [])


# 本機測試
if __name__ == "__main__":
    test_id = input("請輸入 Calendar ID：").strip()
    print(f"查詢行事曆：{test_id}")
    events = get_upcoming_events(calendar_id=test_id)
    if not events:
        print("未來 24 小時沒有行程")
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date"))
        name = e.get("summary", "（無標題）")
        location = e.get("location", "（無地點）")
        print(f"{start} | {name} | {location}")