import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import TOKEN
from bot.handlers import base, handle_photos, post_confirm

# ⬇️ если хочешь проверить наличие шрифта для водяного знака
from bot.utils.add_watermark import _load_font  # да, можно импортировать (это не "приватно" в Python)

# ---- Логирование ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot")

# ---- Хуки запуска/остановки -------------------------------------------------
async def on_startup(bot: Bot):
    me = await bot.get_me()
    log.info(f"✅ Запущен бот @{me.username} (id={me.id})")

    # Проверка шрифта: просто попробуем загрузить — если не найдём, напишем предупреждение
    try:
        font = _load_font(40)
        font_info = getattr(font, "path", None) or "Pillow default"
        log.info(f"🅵 Шрифт для водяного знака: {font_info}")
    except Exception as e:
        log.warning(f"⚠️ Не удалось проверить шрифт: {e}")

    # Пример: убедимся, что папка с данными существует (если нужна)
    data_dir = Path(__file__).resolve().parent / "data"
    if not data_dir.exists():
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"📁 Создана папка {data_dir}")
        except Exception as e:
            log.warning(f"⚠️ Не могу создать {data_dir}: {e}")

async def on_shutdown(bot: Bot):
    try:
        me = await bot.get_me()
        log.info(f"🛑 Останавливаем бота @{me.username}")
    except Exception:
        pass
    # aiogram сам корректно закрывает сессии, но можно явно:
    await bot.session.close()
    log.info("✅ Сессия Telegram закрыта. До связи!")

# ---- Точка входа ------------------------------------------------------------
async def main():
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")  # дефолтный HTML везде
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутеры
    dp.include_router(base.router)
    dp.include_router(handle_photos.router)
    dp.include_router(post_confirm.router)

    # Подписываемся на события старта/остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    log.info("🚀 Стартуем polling…")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("🧹 Завершение по сигналу пользователя…")
    except Exception:
        log.exception("💥 Критическая ошибка на верхнем уровне:")
