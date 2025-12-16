from aiogram.fsm.state import State, StatesGroup

class TokenStates(StatesGroup):
    editing_address = State()