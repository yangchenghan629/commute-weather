# fetcher/geocoding.py
import requests
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "locations.json")

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def geocode(location_str):
    cache = load_cache()
    if location_str in cache:
        print(f"（快取）{location_str}")
        return cache[location_str]

    # 嘗試完整地址
    queries = [location_str]

    # 如果包含逗號，也試試第一段
    if "," in location_str:
        queries.append(location_str.split(",")[0].strip())

    # 也試試移除郵遞區號（純數字開頭的部分）
    import re
    simplified = re.sub(r"^\d+", "", location_str).strip()
    if simplified != location_str:
        queries.append(simplified)

    for q in queries:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": 1},
            headers={"User-Agent": "commute-weather-app"}
        )
        results = r.json()
        if results:
            coords = {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])}
            cache[location_str] = coords
            save_cache(cache)
            print(f"找到：{location_str} → {coords}（查詢：{q}）")
            return coords

    print(f"找不到地點：{location_str}")
    return None

# 測試
if __name__ == "__main__":
    places = ["台中火車站", "台灣大學", "高雄85大樓"]
    for p in places:
        coords = geocode(p)
        print(f"{p} → {coords}")