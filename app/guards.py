from app.config import ALLOWED_IDS
from functools import wraps
from aiogram.types import Message

def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_IDS

def is_owner(user_id: int) -> bool:
    return user_id in ALLOWED_IDS

def whitelist_only(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if not is_allowed(message.from_user.id):
            return
        return await func(message, *args, **kwargs)
    return wrapper