from pydantic import BaseModel
from typing import Optional, List

class TokenPriceData(BaseModel):
    price: float
    change_24h: float
    high_24h: float
    low_24h: float
    volume_24h: float

class TransactionDetail(BaseModel):
    id: int
    type: str
    amount_usd: float
    amount_token: float
    date: str
    from_address: str
    to_address: str
    tx_hash: str
    fee: float
    explorer_link: str
    status: str

class TokenDetailResponse(BaseModel):
    success: bool
    token: dict
    transactions: List[TransactionDetail]
    chart_data: List[dict]