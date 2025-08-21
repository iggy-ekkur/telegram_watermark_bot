from aiogram import types, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    CallbackQuery
)

from bot.storage import (
    user_messages, bot_messages,
    user_channels, user_watermarks,
    last_menu_message
)
from bot.states import SetWatermark, SetChannel
from bot.keyboards.settings import get_settings_menu  # inline-меню

router = Router()

@router.message(CommandStart())
async def start(message: types.Message):
    uid = message.from_user.id

    # ⬇️ ТРИГГЕРИМ ДЕФОЛТЫ через defaultdict (важно — не .get)
    _ = user_channels[uid]      # "@testplaygroundwatermark"
    _ = user_watermarks[uid]    # "FLP STONE"

    warning = (
        "⚠️ *Перед началом работы убедитесь:*\n\n"
        "1. Бот добавлен в канал\n"
        "2. У него есть права администратора\n"
        "3. Вы тоже администратор канала\n\n"
        "После этого отправьте фото или пост 👇"
    )
    msg = await message.answer(
        warning,
        parse_mode="Markdown",  # ок, здесь можно Markdown; в остальных местах держим HTML
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⚙️ Настройки")]],
            resize_keyboard=True,
            is_persistent=True,      # чтобы клавиатура не пропадала сама по себе
            one_time_keyboard=False
        )
    )
    user_messages[uid].append(message.message_id)
    bot_messages[uid].append(msg.message_id)


@router.message(F.text == "⚙️ Настройки")
async def open_settings(message: types.Message):
    uid = message.from_user.id
    user_messages[uid].append(message.message_id)

    # по возможности удалим триггер-сообщение "⚙️ Настройки" от пользователя (чистим чат)
    try:
        await message.bot.delete_message(chat_id=uid, message_id=message.message_id)
    except:
        pass

    # если старое меню ещё висит — удалим, чтобы не плодить меню
    old_menu_id = last_menu_message[uid]
    if old_menu_id:
        try:
            await message.bot.delete_message(chat_id=uid, message_id=old_menu_id)
        except:
            pass

    # показываем inline-меню настроек (не зависит от reply-клавиатуры)
    menu_msg = await message.answer("Настройки:", reply_markup=get_settings_menu())
    last_menu_message[uid] = menu_msg.message_id
    bot_messages[uid].append(menu_msg.message_id)


@router.callback_query(F.data == "hide_menu")
async def hide_menu(callback: CallbackQuery):
    uid = callback.from_user.id
    try:
        await callback.message.delete()
    except:
        pass
    # меню скрыто — просто сбрасываем id; reply-клава остаётся persistent
    last_menu_message[uid] = None


@router.callback_query(F.data == "set_channel")
async def ask_channel(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📡 Введи @канал, куда бот будет публиковать посты:",
                                     reply_markup=get_settings_menu())
    await state.set_state(SetChannel.waiting_for_channel)


@router.message(SetChannel.waiting_for_channel)
async def save_channel(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    if not message.text:
        return await message.reply("❗ Пожалуйста, введи название канала.")
    channel = message.text.strip()
    try:
        bot_member = await message.bot.get_chat_member(channel, (await message.bot.me()).id)
        if bot_member.status not in ["administrator", "creator"]:
            return await message.reply("❌ Бот не является админом канала.")
        user_member = await message.bot.get_chat_member(channel, uid)
        if user_member.status not in ["administrator", "creator"]:
            return await message.reply("❌ Ты не админ в этом канале.")

        user_channels[uid] = channel
        await message.answer(f"✅ Канал {channel} установлен.")
        await state.clear()
    except Exception as e:
        await message.reply(f"Ошибка: {e}")


@router.callback_query(F.data == "setmark_text")
async def ask_watermark(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍️ Введи новый текст водяного знака:",
                                     reply_markup=get_settings_menu())
    await state.set_state(SetWatermark.text)


@router.message(SetWatermark.text)
async def save_watermark(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    if not message.text:
        return await message.reply("❗ Пожалуйста, введи текст для водяного знака.")
    txt = message.text.strip()
    user_watermarks[uid] = txt
    await message.answer(f"✅ Вотермарк установлен: {txt}")
    await state.clear()


@router.callback_query(F.data == "info")
async def show_info(callback: CallbackQuery):
    uid = callback.from_user.id
    channel = user_channels[uid]
    watermark = user_watermarks[uid]
    await callback.message.edit_text(
        f"🔧 Настройки:\n\n📡 Канал: {channel}\n💧 Вотермарк: {watermark}",
        reply_markup=get_settings_menu()
    )
