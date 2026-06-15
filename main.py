# main.py
from fetcher.qpesums import fetch_qpesums, find_nearest_rain
from fetcher.calendar_fetcher import get_upcoming_events
from fetcher.geocoding import geocode
from processor.decision import get_commute_suggestion
from messenger.linebot import send_weather_alert
from datetime import datetime, timezone

ALERT_BEFORE_MINUTES = 90  # 出發前幾分鐘提醒

def main():
    print("=== 通勤天氣系統啟動 ===")

    # 抓雨量格點
    print("抓取 QPESUMS 資料...")
    grid = fetch_qpesums()

    # 抓行程
    print("讀取 Google Calendar...")
    events = get_upcoming_events(hours_ahead=24)
    if not events:
        print("未來 24 小時沒有行程，結束。")
        return

    now = datetime.now(timezone.utc)

    for event in events:
        start_str = event["start"].get("dateTime")
        if not start_str:
            continue  # 全天行程跳過

        start_time = datetime.fromisoformat(start_str)
        time_until = (start_time - now).total_seconds() / 60
        print(f"行程：{event.get('summary')}，距離出發：{time_until:.0f} 分鐘")

        # 只提醒出發前 N 分鐘內的行程
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

if __name__ == "__main__":
    main()