import os
import redis


def get_redis():
    url = os.environ.get("REDIS_URL")
    if not url:
        raise Exception("找不到 REDIS_URL 環境變數")
    return redis.from_url(url, decode_responses=True)


def get_calendar_id(user_id: str) -> str | None:
    r = get_redis()
    return r.get(f"calendar:{user_id}")


def set_calendar_id(user_id: str, calendar_id: str):
    r = get_redis()
    r.set(f"calendar:{user_id}", calendar_id)


def delete_calendar_id(user_id: str):
    r = get_redis()
    r.delete(f"calendar:{user_id}")