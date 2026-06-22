import os
import requests
import urllib3
from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage, FlexMessage, FlexContainer,
    ImageMessage
)
from linebot.v3.webhooks import MessageEvent, PostbackEvent, TextMessageContent

app = Flask(__name__)

LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
SERVICE_ACCOUNT_EMAIL = os.environ.get("SERVICE_ACCOUNT_EMAIL", "（尚未設定）")

handler = WebhookHandler(LINE_CHANNEL_SECRET)
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)


# ── 工具函式 ──────────────────────────────────────────────

def trigger_github_actions():
    r = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/scheduler.yml/dispatches",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        },
        json={"ref": "main", "inputs": {"manual": "true"}}
    )
    print(f"GitHub API 回應：{r.status_code}")
    return r.status_code == 204


def reply(reply_token, messages: list):
    """統一回覆入口"""
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=messages)
        )


def reply_text(reply_token, text: str):
    reply(reply_token, [TextMessage(text=text)])


# ── 選單 ──────────────────────────────────────────────────

def send_menu(reply_token):
    """發送主選單"""
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
                    "type": "button", "style": "primary", "color": "#1A73E8",
                    "action": {
                        "type": "postback",
                        "label": "🔍 立即查詢天氣",
                        "data": "action=check_weather"
                    }
                },
                {
                    "type": "button", "style": "secondary",
                    "action": {
                        "type": "postback",
                        "label": "📅 查看今日行程",
                        "data": "action=check_calendar"
                    }
                },
                {
                    "type": "button", "style": "secondary",
                    "action": {
                        "type": "postback",
                        "label": "🔗 綁定 Google 行事曆",
                        "data": "action=bind_calendar"
                    }
                },
                {
                    "type": "button", "style": "secondary",
                    "action": {
                        "type": "postback",
                        "label": "❌ 解除綁定",
                        "data": "action=unbind_calendar"
                    }
                }
            ]
        }
    }
    reply(reply_token, [FlexMessage(
        alt_text="通勤天氣助理",
        contents=FlexContainer.from_dict(flex_content)
    )])


# ── Webhook 路由 ──────────────────────────────────────────

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


# ── 訊息處理 ──────────────────────────────────────────────

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    from db.redis_client import get_redis, set_calendar_id
    r = get_redis()

    # 正在等待用戶輸入 Calendar ID
    if r.get(f"pending_bind:{user_id}"):
        if "@" in text:
            calendar_id = text
            # 先驗證這個 calendar_id 是否真的可以存取
            try:
                from fetcher.calendar_fetcher import get_upcoming_events
                get_upcoming_events(calendar_id=calendar_id, hours_ahead=1)
                # 驗證成功才存
                set_calendar_id(user_id, calendar_id)
                r.delete(f"pending_bind:{user_id}")
                reply_text(event.reply_token,
                           "✅ 綁定成功！現在可以用「查詢天氣」或「查看行程」了")
            except Exception as e:
                reply_text(event.reply_token,
                           f"❌ 綁定失敗：{str(e)}\n\n請確認步驟後重新貼上 Calendar ID")
        else:
            reply_text(event.reply_token,
                       "❌ 格式不對，Calendar ID 通常包含 @ 符號（例如：xxx@gmail.com）\n請重新貼上")
        return

    # 一般訊息 → 顯示主選單
    send_menu(event.reply_token)


# ── Postback 處理 ─────────────────────────────────────────

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    data = event.postback.data

    from db.redis_client import get_redis, get_calendar_id, delete_calendar_id
    r = get_redis()

    # ── 綁定行事曆 ──
    if data == "action=bind_calendar":
        msg = (
            f"請依下列步驟綁定你的 Google 行事曆：\n\n"
            f"1️⃣ 開啟 Google Calendar（電腦版）\n"
            f"2️⃣ 左側找到你的行事曆 → 右鍵「設定」\n"
            f"3️⃣ 「與特定人員共用」→ 新增以下 Email（僅限查看）：\n"
            f"\n{SERVICE_ACCOUNT_EMAIL}\n\n"
            f"4️⃣ 同一頁往下找「整合」→ 複製「行事曆 ID」\n"
            f"5️⃣ 回到這裡，直接把 Calendar ID 貼給我\n\n"
            f"⏱ 請在 10 分鐘內完成"
        )
        r.set(f"pending_bind:{user_id}", "1", ex=600)
        reply_text(event.reply_token, msg)
        return

    # ── 解除綁定 ──
    if data == "action=unbind_calendar":
        existing = get_calendar_id(user_id)
        if existing:
            delete_calendar_id(user_id)
            reply_text(event.reply_token,
                       "✅ 已解除綁定。你的 Calendar ID 已從系統中刪除。\n"
                       "記得也可以在 Google Calendar 中移除分享給 Service Account 的權限。")
        else:
            reply_text(event.reply_token, "你目前沒有綁定任何行事曆")
        return

    # ── 以下功能需要先綁定 ──
    calendar_id = get_calendar_id(user_id)
    if not calendar_id:
        reply_text(event.reply_token,
                   "⚠️ 尚未綁定 Google 行事曆\n請先點「🔗 綁定 Google 行事曆」")
        return

    # ── 立即查詢天氣 ──
    if data == "action=check_weather":
        from fetcher.qpesums import fetch_qpesums, find_nearest_rain
        from fetcher.calendar_fetcher import get_upcoming_events
        from fetcher.geocoding import geocode
        from processor.decision import get_commute_suggestion
        from datetime import datetime, timezone

        urllib3.disable_warnings()
        from datetime import datetime as dt
        ts = int(dt.now().timestamp())
        radar_url = (
            f"https://cwaopendata.s3.ap-northeast-1.amazonaws.com"
            f"/Observation/O-A0058-003.png?t={ts}"
        )

        try:
            grid = fetch_qpesums()
            events = get_upcoming_events(calendar_id=calendar_id, hours_ahead=24)
        except Exception as e:
            reply_text(event.reply_token, f"❌ 查詢失敗：{str(e)}")
            return

        now = datetime.now(timezone.utc)

        if not events:
            reply(event.reply_token, [
                TextMessage(text="📅 未來 24 小時沒有行程！"),
                ImageMessage(original_content_url=radar_url, preview_image_url=radar_url)
            ])
            return

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

        reply(event.reply_token, [
            TextMessage(text="\n".join(lines)),
            ImageMessage(original_content_url=radar_url, preview_image_url=radar_url)
        ])

    # ── 查看今日行程 ──
    elif data == "action=check_calendar":
        from fetcher.calendar_fetcher import get_upcoming_events
        from datetime import datetime

        try:
            events = get_upcoming_events(calendar_id=calendar_id, hours_ahead=24)
        except Exception as e:
            reply_text(event.reply_token, f"❌ 查詢失敗：{str(e)}")
            return

        if not events:
            reply_text(event.reply_token, "📅 今日沒有任何行程！")
            return

        lines = ["📅 今日行程：\n"]
        for e in events:
            start_str = e["start"].get("dateTime", e["start"].get("date", ""))
            try:
                start_time = datetime.fromisoformat(start_str).strftime("%H:%M")
            except Exception:
                start_time = start_str
            name = e.get("summary", "（無標題）")
            location = e.get("location", "（無地點）")
            lines.append(f"🕐 {start_time} {name}\n📍 {location}\n")

        reply_text(event.reply_token, "\n".join(lines))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)