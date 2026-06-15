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
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def geocode(location_str):
    # 確保 data 資料夾存在
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    
    cache = load_cache()
    if location_str in cache:
        return cache[location_str]

    import re
    queries = [location_str]

    # 逗號前的部分
    first_part = location_str.split(",")[0].strip()
    queries.append(first_part)

    # 移除數字、台灣、臺灣
    simplified = re.sub(r"(^\d+|台灣|臺灣)", "", first_part).strip()
    if simplified and simplified not in queries:
        queries.append(simplified)

    # 只取機構名稱（到館/院/校/站等）
    match = re.match(r"(.{2,10}[館院校站廳場樓區])", first_part)
    if match:
        queries.append(match.group(1))

    # 只取大學名稱
    short = re.match(r"([\u4e00-\u9fff]{2,6}大學|[\u4e00-\u9fff]{2,6}學校)", first_part)
    if short:
        queries.append(short.group(1))

    for q in queries:
        try:
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": 1},
                headers={"User-Agent": "commute-weather-app"},
                timeout=10
            )
            results = r.json()
            if results:
                coords = {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])}
                cache[location_str] = coords
                save_cache(cache)
                return coords
        except Exception as e:
            print(f"查詢失敗：{q}，錯誤：{e}")

    print(f"找不到地點：{location_str}")
    return None

# 測試
if __name__ == "__main__":
    places = ["台中火車站", "台灣大學", "高雄85大樓"]
    for p in places:
        coords = geocode(p)
        print(f"{p} → {coords}")