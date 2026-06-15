# messenger/linebot.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import requests

def send_weather_alert(event_name, start_time, location, suggestion, rain):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}"
    }

    flex_content = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1A73E8",
            "contents": [
                {"type": "text", "text": "🌧 通勤天氣提醒", "weight": "bold",
                 "size": "lg", "color": "#FFFFFF"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"📅 {event_name}", "weight": "bold", "size": "md"},
                {"type": "text", "text": f"🕐 出發時間：{start_time}", "size": "sm", "color": "#555555"},
                {"type": "text", "text": f"📍 地點：{location}", "size": "sm", "color": "#555555"},
                {"type": "separator"},
                {"type": "text", "text": suggestion["level"], "weight": "bold",
                 "size": "xl", "color": suggestion["color"]},
                {"type": "text", "text": f"雨量：{rain:.1f} mm", "size": "sm", "color": "#888888"},
                {"type": "text", "text": f"👉 {suggestion['suggestion']}", "weight": "bold",
                 "size": "md", "color": suggestion["color"]}
            ]
        }
    }

    body = {
        "to": config.LINE_USER_ID,
        "messages": [
            {
                "type": "flex",
                "altText": f"通勤天氣提醒：{suggestion['suggestion']}",
                "contents": flex_content
            }
        ]
    }

    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        json=body
    )
    print(f"Line 推播狀態：{r.status_code}")
    if r.status_code != 200:
        print(r.json())

# 測試
if __name__ == "__main__":
    from processor.decision import get_commute_suggestion
    suggestion = get_commute_suggestion(10)
    send_weather_alert(
        event_name="期末考",
        start_time="14:00",
        location="台中火車站",
        suggestion=suggestion,
        rain=10
    )