from aiogram.fsm.state import State, StatesGroup

class OutcomeStates(StatesGroup):
    choosing_token = State()
    entering_amount = State()
    choosing_time_option = State()
    choosing_day = State()
    entering_time = State()
    entering_to_address = State()
    entering_tx_hash = State()
    entering_fee = State()
    confirming_transaction = State()