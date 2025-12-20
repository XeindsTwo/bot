from fastapi import APIRouter
import httpx

router = APIRouter(prefix="/api/alpha", tags=["alpha"])


def format_large_number(value: float) -> str:
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"${value:,.0f}"
    else:
        return f"${value:.2f}"


@router.get("/tokens")
async def alpha_tokens():
    url = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()

    tokens = []
    for t in data.get("data", [])[:6]:
        image_url = t.get("iconUrl") or t.get("chainIconUrl") or ""
        proxied_image = ""
        if image_url:
            proxied_image = f"http://localhost:8000/api/token-image?url={image_url}"
        market_cap = float(t.get("marketCap", 0))

        tokens.append({
            "network": t.get("chainName", ""),
            "name": t.get("name", ""),
            "symbol": t.get("symbol", ""),
            "image": proxied_image,
            "price": round(float(t.get("price", 0)), 2),
            "change24h": float(t.get("percentChange24h", 0)),
            "market_cap_formatted": format_large_number(market_cap),
        })

    return tokens
