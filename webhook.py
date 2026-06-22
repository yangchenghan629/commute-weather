# webhook.py
import os
import requests
from datetime import datetime
from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage, FlexMessage, FlexContainer
)
from linebot.v3.webhooks import MessageEvent, PostbackEvent, TextMessageContent
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage, FlexMessage, FlexContainer,
    ImageMessage  # 加這個
)

app = Flask(__name__)

LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # 格式: "username/repo"

handler = WebhookHandler(LINE_CHANNEL_SECRET)
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

def trigger_github_actions():
    r = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/scheduler.yml/dispatches",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        },
        json={
            "ref": "main",
            "inputs": {"manual": "true"}
        }
    )
    print(f"GitHub API 回應：{r.status_code}")
    return r.status_code == 204

def send_menu(reply_token):
    """發送主選單"""
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#1A73E8",
                "contents": [
                    {"type": "text", "text": "🌤 通勤天氣助理",
                     "weight": "bold", "size": "lg", "color": "#FFFFFF"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical", "spacing": "sm",
                "contents": [
                    {"type": "text", "text": "請選擇功能", "size": "md", "color": "#555555"}
                ]
            },
            "footer": {
                "type": "box", "layout": "vertical", "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#1A73E8",
                        "action": {
                            "type": "postback",
                            "label": "🔍 立即查詢天氣",
                            "data": "action=check_weather"
                        }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": {
                            "type": "postback",
                            "label": "📅 查看今日行程",
                            "data": "action=check_calendar"
                        }
                    }
                ]
            }
        }
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=reply_token,
            messages=[FlexMessage(
                alt_text="通勤天氣助理",
                contents=FlexContainer.from_dict(flex_content)
            )]
        ))

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "Commute Weather Bot is running!"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """處理文字訊息，顯示選單"""
    send_menu(event.reply_token)

@handler.add(PostbackEvent)
def handle_postback(event):
    """處理按鈕點擊"""
    data = event.postback.data
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        if data == "action=check_weather":
            from fetcher.qpesums import fetch_qpesums, find_nearest_rain
            from fetcher.calendar_fetcher import get_upcoming_events
            from fetcher.geocoding import geocode
            from processor.decision import get_commute_suggestion
            from datetime import datetime, timezone

            # 取得雷達圖 URL
            import urllib3
            urllib3.disable_warnings()
            ts = int(datetime.now().timestamp())
            radar_url = f"https://cwaopendata.s3.ap-northeast-1.amazonaws.com/Observation/O-A0058-003.png?t={ts}"
            
            # 抓雨量格點
            grid = fetch_qpesums()
            events = get_upcoming_events(hours_ahead=24)
            now = datetime.now(timezone.utc)

            if not events:
                line_bot_api.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="📅 未來 24 小時沒有行程！"),
                        ImageMessage(original_content_url=radar_url, preview_image_url=radar_url)
                    ]
                ))
                return

            # 整理行程與雨量
            lines = ["🌧 通勤天氣查詢結果：\n"]
            for e in events:
                start_str = e["start"].get("dateTime")
                if not start_str:
                    continue
                start_time = datetime.fromisoformat(start_str)
                time_until = (start_time - now).total_seconds() / 60
                if time_until < -60:
                    continue
                name = e.get("summary", "（無標題）")
                location_str = e.get("location", "")
                time_str = start_time.strftime("%H:%M")

                if location_str:
                    coords = geocode(location_str)
                    if coords:
                        rain = find_nearest_rain(grid, coords["lat"], coords["lon"])
                        suggestion = get_commute_suggestion(rain)
                        lines.append(f"🕐 {time_str} {name}")
                        lines.append(f"📍 {location_str}")
                        lines.append(f"{suggestion['level']} {rain:.1f}mm → {suggestion['suggestion']}\n")
                    else:
                        lines.append(f"🕐 {time_str} {name}")
                        lines.append(f"📍 {location_str}（地點查詢失敗）\n")
                else:
                    lines.append(f"🕐 {time_str} {name}（無地點）\n")

            line_bot_api.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text="\n".join(lines)),
                    ImageMessage(
                        original_content_url=radar_url,
                        preview_image_url=radar_url
                    )
                ]
            ))

        elif data == "action=check_calendar":
            from fetcher.calendar_fetcher import get_upcoming_events
            from fetcher.geocoding import geocode
            events = get_upcoming_events(hours_ahead=24)

            if not events:
                msg = "📅 今日沒有任何行程！"
                line_bot_api.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=msg)]
                ))
                return

            # 整理行程清單
            lines = ["📅 今日行程：\n"]
            for e in events:
                start_str = e["start"].get("dateTime", e["start"].get("date", ""))
                try:
                    from datetime import datetime
                    start_time = datetime.fromisoformat(start_str).strftime("%H:%M")
                except:
                    start_time = start_str
                name = e.get("summary", "（無標題）")
                location = e.get("location", "（無地點）")
                lines.append(f"🕐 {start_time} {name}\n📍 {location}\n")

            line_bot_api.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="\n".join(lines))]
            ))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)