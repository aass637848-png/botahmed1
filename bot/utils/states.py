from aiogram.fsm.state import State, StatesGroup


class TargetStates(StatesGroup):
    waiting_for_identifier = State()


class BroadcastStates(StatesGroup):
    waiting_for_content = State()
    selecting_targets = State()
    waiting_for_repeat = State()
    waiting_for_interval = State()
    waiting_for_delay = State()
    waiting_for_schedule = State()
    confirming = State()


class SettingsStates(StatesGroup):
    waiting_for_timezone = State()
    waiting_for_default_delay = State()
