# main.py
import sys
from fetcher.qpesums import fetch_qpesums, find_nearest_rain
from fetcher.calendar_fetcher import get_upcoming_events
from fetcher.geocoding import geocode
from processor.decision import get_commute_suggestion
from messenger.linebot import send_weather_alert
from datetime import datetime, timezone
import os
import requests

ALERT_BEFORE_MINUTES = 60
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "")

def send_no_event_message():
    """手動觸發時，沒有行程才發送通知"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    body = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": "📅 未來 60 分鐘內沒有行程！"}]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=body)

def main(manual=False):
    print("=== 通勤天氣系統啟動 ===")

    print("抓取 QPESUMS 資料...")
    grid = fetch_qpesums()

    print("讀取 Google Calendar...")
    events = get_upcoming_events(hours_ahead=24)

    if not events:
        if manual:
            send_no_event_message()
        else:
            print("未來 24 小時沒有行程，結束。")
        return

    now = datetime.now(timezone.utc)
    has_alert = False

    for event in events:
        start_str = event["start"].get("dateTime")
        if not start_str:
            continue

        start_time = datetime.fromisoformat(start_str)
        time_until = (start_time - now).total_seconds() / 60
        print(f"行程：{event.get('summary')}，距離出發：{time_until:.0f} 分鐘")

        if not (0 < time_until <= ALERT_BEFORE_MINUTES):
            continue

        location_str = event.get("location", "")
        if not location_str:
            print("  → 無地點資訊，跳過")
            continue

        coords = geocode(location_str)
        if not coords:
            print(f"  → 找不到地點：{location_str}，跳過")
            continue

        rain = find_nearest_rain(grid, coords["lat"], coords["lon"])
        suggestion = get_commute_suggestion(rain)

        print(f"  → 雨量：{rain:.1f} mm，建議：{suggestion['suggestion']}")
        send_weather_alert(
            event_name=event.get("summary", "行程"),
            start_time=start_time.strftime("%H:%M"),
            location=location_str,
            suggestion=suggestion,
            rain=rain
        )
        has_alert = True

    if not has_alert and manual:
        send_no_event_message()

if __name__ == "__main__":
    # 如果帶入 --manual 參數就是手動觸發
    manual = "--manual" in sys.argv
    main(manual=manual)