from aiogram.fsm.state import State, StatesGroup

class SetWatermark(StatesGroup):
    text = State()

class SetChannel(StatesGroup):
    waiting_for_channel = State()
