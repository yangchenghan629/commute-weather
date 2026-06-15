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
    # 產生多個查詢候選：原始 → 逗號前 → 移除數字和"台灣" → 只取前兩個中文詞
    queries = [location_str]
    if "," in location_str:
        queries.append(location_str.split(",")[0].strip())
    simplified = re.sub(r"(^\d+|台灣|臺灣)", "", location_str.split(",")[0]).strip()
    if simplified:
        queries.append(simplified)

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