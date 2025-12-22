import httpx

BINANCE_SYMBOLS = {
    "bnb": "BNBUSDT",
    "btc": "BTCUSDT",
    "eth": "ETHUSDT",
    "matic": "MATICUSDT",
    "tron": "TRXUSDT",
    "twt": "TWTBUSD",
    "sol": "SOLUSDT",
    "ton": "TONUSDT",
}

async def fetch_binance_price(symbol: str) -> dict:
    """Получаем цену с Binance"""
    try:
        if symbol.startswith("usdt_"):
            return {
                "price": 1.0,
                "change_24h": 0.0,
                "high_24h": 1.0,
                "low_24h": 1.0,
                "volume_24h": 0
            }

        binance_symbol = BINANCE_SYMBOLS.get(symbol)
        if not binance_symbol:
            return None

        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "price": float(data["lastPrice"]),
                    "change_24h": float(data["priceChangePercent"]),
                    "high_24h": float(data["highPrice"]),
                    "low_24h": float(data["lowPrice"]),
                    "volume_24h": float(data["volume"])
                }
            elif resp.status_code == 400:
                busd_symbol = f"{symbol.upper()}BUSD"
                url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={busd_symbol}"
                resp2 = await client.get(url, timeout=3.0)

                if resp2.status_code == 200:
                    data = resp2.json()
                    return {
                        "price": float(data["lastPrice"]),
                        "change_24h": float(data["priceChangePercent"]),
                        "high_24h": float(data["highPrice"]),
                        "low_24h": float(data["lowPrice"]),
                        "volume_24h": float(data["volume"])
                    }

    except Exception as e:
        print(f"[ERROR] Binance price for {symbol}: {e}")

    return None