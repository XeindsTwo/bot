from aiogram.fsm.state import State, StatesGroup


class TokenStates(StatesGroup):
    """Состояния для управления токенами"""
    editing_address = State()


class ClearStates(StatesGroup):
    """Состояния для очистки истории"""
    confirming_clear = State()