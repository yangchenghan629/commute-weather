import requests
import json
import os
import sys
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "locations.json")

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def nominatim_search(query: str) -> dict | None:
    """對 Nominatim 發出單次查詢，失敗最多 retry 3 次"""
    for attempt in range(3):
        try:
            time.sleep(1.5)  # Nominatim 要求每秒最多 1 次
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1, "countrycodes": "tw"},
                headers={
                    "User-Agent": "commute-weather-bot/1.0 (personal project)",
                    "Accept-Language": "zh-TW,zh;q=0.9"
                },
                timeout=10
            )
            # 確認回傳是 JSON
            if "application/json" not in r.headers.get("Content-Type", ""):
                print(f"Nominatim 回傳非 JSON（attempt {attempt+1}）：{r.text[:100]}")
                time.sleep(2)
                continue

            results = r.json()
            if results:
                return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])}

        except requests.exceptions.Timeout:
            print(f"查詢逾時（attempt {attempt+1}）：{query}")
            time.sleep(2)
        except Exception as e:
            print(f"查詢失敗（attempt {attempt+1}）：{query}，錯誤：{e}")
            time.sleep(2)

    return None

def geocode(location_str: str) -> dict | None:
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

    # 快取命中直接回傳
    cache = load_cache()
    if location_str in cache:
        return cache[location_str]

    import re

    # 依序嘗試不同精簡程度的查詢
    queries = []

    # 1. 原始字串
    queries.append(location_str)

    # 2. 逗號前的部分
    first_part = location_str.split(",")[0].strip()
    if first_part not in queries:
        queries.append(first_part)

    # 3. 移除數字、台灣、臺灣
    simplified = re.sub(r"(\d+|台灣|臺灣)", "", first_part).strip()
    if simplified and simplified not in queries:
        queries.append(simplified)

    # 4. 只取機構名稱（到館/院/校/站等）
    match = re.match(r"(.{2,10}[館院校站廳場樓區])", first_part)
    if match and match.group(1) not in queries:
        queries.append(match.group(1))

    # 5. 只取大學名稱
    short = re.match(r"([\u4e00-\u9fff]{2,6}大學|[\u4e00-\u9fff]{2,6}學校)", first_part)
    if short and short.group(1) not in queries:
        queries.append(short.group(1))

    for q in queries:
        coords = nominatim_search(q)
        if coords:
            cache[location_str] = coords
            save_cache(cache)
            print(f"地點查詢成功：{location_str} → {coords}（使用查詢：{q}）")
            return coords

    print(f"找不到地點：{location_str}")
    return None


# 測試
if __name__ == "__main__":
    places = ["台中火車站", "台灣大學", "高雄85大樓"]
    for p in places:
        coords = geocode(p)
        print(f"{p} → {coords}")