from app.config import OWNER_ID

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID