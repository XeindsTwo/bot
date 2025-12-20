from fastapi import APIRouter, Query, Response
import httpx

router = APIRouter(prefix="/api", tags=["images"])


@router.get("/token-image")
async def token_image(url: str = Query(...)):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                return Response(
                    content=resp.content,
                    media_type=resp.headers.get("content-type", "image/png")
                )
        except Exception:
            pass
    return Response(status_code=404)
