from aiogram import Dispatcher
from bot.handlers.start import router as start_router
from bot.handlers.targets import router as targets_router
from bot.handlers.broadcast import router as broadcast_router
from bot.handlers.status import router as status_router
from bot.handlers.reports import router as reports_router
from bot.handlers.settings import router as settings_router


def register_all_handlers(dp: Dispatcher) -> None:
    """Register all modular handlers/routers to dispatcher."""
    dp.include_router(start_router)
    dp.include_router(targets_router)
    dp.include_router(broadcast_router)
    dp.include_router(status_router)
    dp.include_router(reports_router)
    dp.include_router(settings_router)
