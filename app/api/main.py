from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from .routers import tokens, transactions, images, alpha, token_detail


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tokens.router)
app.include_router(transactions.router)
app.include_router(images.router)
app.include_router(alpha.router)
app.include_router(token_detail.router)


@app.get("/")
async def root():
    return {"message": "Crypto Wallet API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
