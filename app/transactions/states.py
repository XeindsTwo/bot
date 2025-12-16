from aiogram.fsm.state import State, StatesGroup

class IncomeStates(StatesGroup):
    choosing_token = State()
    entering_amount = State()
    choosing_time_option = State()
    choosing_day = State()
    entering_time = State()
    entering_from_address = State()
    entering_tx_hash = State()
    entering_fee = State()
    entering_explorer_link = State()