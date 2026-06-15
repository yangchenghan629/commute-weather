# processor/decision.py

def get_commute_suggestion(rain_mm: float) -> dict:
    if rain_mm == 0:
        return {"level": "☀️ 晴朗", "suggestion": "適合騎車", "color": "#27AE60"}
    elif rain_mm < 2.5:
        return {"level": "🌦 小雨", "suggestion": "建議帶傘騎車", "color": "#F39C12"}
    elif rain_mm < 15:
        return {"level": "🌧 中雨", "suggestion": "建議搭公車", "color": "#E67E22"}
    elif rain_mm < 40:
        return {"level": "⛈ 大雨", "suggestion": "強烈建議搭車", "color": "#E74C3C"}
    else:
        return {"level": "🌊 豪雨", "suggestion": "請勿外出騎車", "color": "#8E44AD"}

# 測試
if __name__ == "__main__":
    for rain in [0, 1, 10, 25, 50]:
        result = get_commute_suggestion(rain)
        print(f"{rain:>4} mm → {result['level']}｜{result['suggestion']}")