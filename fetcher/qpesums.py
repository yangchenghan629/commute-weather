# fetcher/qpesums.py
import requests
import numpy as np
import urllib3
import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 格點參數
LON_START = 118.0
LAT_START = 20.0
RESOLUTION = 0.0125
DIM_X = 441  # 經向
DIM_Y = 561  # 緯向

def fetch_qpesums():
    r = requests.get(
        "https://opendata.cwa.gov.tw/dataset/observation/F-B0046-001",
        params={"Authorization": config.CWA_API_KEY, "format": "JSON"},
        verify=False
    )
    data = r.json()
    content = data["cwaopendata"]["dataset"]["contents"]["content"]
    values = [float(v) for v in content.split(",")]
    grid = np.array(values).reshape(DIM_Y, DIM_X)
    return grid

def find_nearest_rain(grid, target_lat, target_lon):
    """輸入經緯度，回傳該格點未來1小時雨量估計(mm)"""
    x = round((target_lon - LON_START) / RESOLUTION)
    y = round((target_lat - LAT_START) / RESOLUTION)

    # 確保不超出範圍
    x = max(0, min(x, DIM_X - 1))
    y = max(0, min(y, DIM_Y - 1))

    rain = grid[y, x]
    return rain if rain >= 0 else 0.0  # -1 為無效值

# 測試
if __name__ == "__main__":
    print("正在抓取 QPESUMS 資料...")
    import json, urllib3, requests
    urllib3.disable_warnings()
    r = requests.get(
        "https://opendata.cwa.gov.tw/dataset/observation/F-B0046-001",
        params={"Authorization": config.CWA_API_KEY, "format": "JSON"},
        verify=False
    )
    data = r.json()
    dt = data["cwaopendata"]["dataset"]["datasetInfo"]["parameterSet"]["DateTime"]
    print(f"資料時間：{dt}")

    grid = fetch_qpesums()
    rain = find_nearest_rain(grid, 24.1477, 120.6736)
    print(f"台中目前雨量：{rain:.3f} mm")