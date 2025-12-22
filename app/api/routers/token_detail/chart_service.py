from datetime import datetime, timedelta
import math

def generate_chart_data_1d(base_price: float, change_24h: float) -> list:
    """Генерируем данные для графика за 1 день"""
    data = []
    now = datetime.now()
    price_24h_ago = base_price * (1 - change_24h / 100)

    for i in range(24, 0, -1):
        timestamp = now - timedelta(hours=i)
        progress = (24 - i) / 24
        current_price = price_24h_ago + (base_price - price_24h_ago) * progress

        hour = timestamp.hour
        wave = math.sin(hour * math.pi / 12) * 0.001
        price_with_wave = current_price * (1 + wave)

        if 9 <= hour <= 17:
            volume = 12000
        elif 0 <= hour <= 5:
            volume = 4000
        else:
            volume = 8000

        data.append({
            "timestamp": timestamp.isoformat(),
            "price": round(price_with_wave, 4),
            "volume": volume
        })

    return data