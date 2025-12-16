from app.db import get_tokens


def find_token_by_id(token_id: str):
    tokens = get_tokens()

    try:
        token_id_int = int(token_id)
        for token in tokens:
            if token[0] == token_id_int:
                return token
    except ValueError:
        for token in tokens:
            if str(token[0]) == token_id:
                return token

    return None