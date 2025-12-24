import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_IDS = []

allowed_str = os.getenv("ALLOWED_IDS", "")
if allowed_str:
    for id_str in allowed_str.split(","):
        id_str = id_str.strip()
        if id_str.isdigit():
            ALLOWED_IDS.append(int(id_str))

if not ALLOWED_IDS:
    old_owner = os.getenv("OWNER_ID")
    if old_owner and old_owner.isdigit():
        ALLOWED_IDS.append(int(old_owner))