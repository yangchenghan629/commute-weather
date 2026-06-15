# webhook.py
import os
import requests
from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage, FlexMessage, FlexContainer
)
from linebot.v3.webhooks import MessageEvent, PostbackEvent, TextMessageContent

app = Flask(__name__)

LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # 格式: "username/repo"

handler = WebhookHandler(LINE_CHANNEL_SECRET)
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

def trigger_github_actions():
    """觸發 GitHub Actions workflow"""
    r = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/scheduler.yml/dispatches",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        },
        json={"ref": "main"}
    )
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
            # 觸發 GitHub Actions
            success = trigger_github_actions()
            if success:
                msg = "⏳ 正在查詢天氣，約 30 秒後會收到通知！"
            else:
                msg = "❌ 查詢失敗，請稍後再試"
            line_bot_api.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=msg)]
            ))

        elif data == "action=check_calendar":
            line_bot_api.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="📅 行程查詢功能開發中...")]
            ))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)