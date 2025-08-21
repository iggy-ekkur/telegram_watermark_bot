from aiogram import types, F, Router
from aiogram.types import (
    BufferedInputFile,
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.enums import ParseMode
from bot.utils.add_watermark import add_watermark
from bot.storage import (
    album_buffer,
    album_timers,          # таймеры для дебаунса
    post_cache,
    user_watermarks,
    user_messages,
    bot_messages,
    user_channels,
    preview_messages,      # сюда складываем id превью, чтобы их не удалять
)
import asyncio

router = Router()
DEBOUNCE_SEC = 1.6  # пауза тишины, после которой финализируем альбом

async def _finalize_album(bot, user_id: int, media_group_id: str, wm_text: str):
    """Финализирует набор фото данного media_group_id, отправляет превью и кнопки."""
    album = album_buffer.pop(media_group_id, None)
    if not album:
        return

    messages = album["messages"]
    status_msg_id = album.get("status_msg_id")

    # убрать статус «Обрабатываю альбом…»
    if status_msg_id:
        try:
            await bot.delete_message(chat_id=user_id, message_id=status_msg_id)
        except:
            pass

    # ===== если пришёл РОВНО 1 кадр — считаем одиночным =====
    if len(messages) == 1:
        m = messages[0]
        f = await bot.get_file(m.photo[-1].file_id)
        fb = await bot.download_file(f.file_path)
        wm = add_watermark(fb.read(), wm_text)

        input_photo = BufferedInputFile(wm.read(), "photo.jpg")
        caption = m.caption or ""
        caption_entities = m.caption_entities

        media = [InputMediaPhoto(media=input_photo)]
        post_cache[user_id] = {
            "media": media,
            "caption": caption,
            "caption_entities": caption_entities,
            "is_album": False
        }

        # превью пользователю (entities → parse_mode=None; иначе → HTML)
        if caption_entities:
            prev = await bot.send_photo(user_id, photo=input_photo,
                                        caption=caption, caption_entities=caption_entities,
                                        parse_mode=None)
        else:
            prev = await bot.send_photo(user_id, photo=input_photo,
                                        caption=caption, parse_mode=ParseMode.HTML)
        bot_messages[user_id].append(prev.message_id)
        preview_messages[user_id].append(prev.message_id)

        # кнопки
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Опубликовать", callback_data="post_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="post_cancel")]
        ])
        ask = await bot.send_message(user_id, "Готово. Отправить в канал?", reply_markup=markup)
        bot_messages[user_id].append(ask.message_id)
        return

    # ===== нормальный альбом (>=2) =====
    # подпись/энтити берём из первого сообщения, где они есть
    caption = next((msg.caption for msg in messages if msg.caption), "") or ""
    caption_entities = next((msg.caption_entities for msg in messages if msg.caption_entities), None)

    media = []
    for i, msg in enumerate(messages):
        f = await bot.get_file(msg.photo[-1].file_id)
        fb = await bot.download_file(f.file_path)
        wm = add_watermark(fb.read(), wm_text)
        input_file = BufferedInputFile(wm.read(), f"album_{i}.jpg")

        if i == 0:
            if caption_entities:
                media.append(InputMediaPhoto(
                    media=input_file,
                    caption=caption,
                    caption_entities=caption_entities,
                    parse_mode=None  # ВАЖНО: при entities parse_mode НЕ ставим
                ))
            else:
                media.append(InputMediaPhoto(
                    media=input_file,
                    caption=caption,
                    parse_mode=ParseMode.HTML
                ))
        else:
            media.append(InputMediaPhoto(media=input_file))

    post_cache[user_id] = {
        "media": media,
        "caption": caption,
        "caption_entities": caption_entities,
        "is_album": True
    }

    # превью альбома
    preview = await bot.send_media_group(chat_id=user_id, media=media)
    ids = [m.message_id for m in preview]
    bot_messages[user_id].extend(ids)
    preview_messages[user_id].extend(ids)

    # кнопки
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Опубликовать", callback_data="post_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="post_cancel")]
    ])
    ask = await bot.send_message(user_id, "Готово. Отправить в канал?", reply_markup=markup)
    bot_messages[user_id].append(ask.message_id)


@router.message(F.photo)
async def handle_photos(message: types.Message):
    user_id = message.from_user.id
    media_group_id = message.media_group_id

    # триггерим дефолты
    _ = user_channels[user_id]
    wm_text = user_watermarks[user_id]

    user_messages.setdefault(user_id, []).append(message.message_id)
    bot_messages.setdefault(user_id, [])
    preview_messages.setdefault(user_id, [])

    # ====== часть альбома (с дебаунсом) ======
    if media_group_id:
        album = album_buffer.setdefault(media_group_id, {
            "messages": [],
            "shown": False,
            "status_msg_id": None
        })
        album["messages"].append(message)

        if not album["shown"]:
            album["shown"] = True
            status = await message.answer("🕓 Обрабатываю альбом…")
            bot_messages[user_id].append(status.message_id)
            album["status_msg_id"] = status.message_id

        # перезапускаем дебаунс-таймер на DEBOUNCE_SEC тишины
        old_task = album_timers.get(media_group_id)
        if old_task and not old_task.done():
            old_task.cancel()

        async def _debounce():
            try:
                await asyncio.sleep(DEBOUNCE_SEC)
            except asyncio.CancelledError:
                return
            await _finalize_album(message.bot, user_id, media_group_id, wm_text)

        album_timers[media_group_id] = asyncio.create_task(_debounce())
        return

    # ====== одиночное фото ======
    status_msg = await message.answer("🕓 Добавляю водяной знак…")
    bot_messages[user_id].append(status_msg.message_id)

    f = await message.bot.get_file(message.photo[-1].file_id)
    fb = await message.bot.download_file(f.file_path)
    result = add_watermark(fb.read(), wm_text)

    caption = message.caption or ""
    caption_entities = message.caption_entities
    input_photo = BufferedInputFile(result.read(), "photo.jpg")

    media = [InputMediaPhoto(media=input_photo)]
    post_cache[user_id] = {
        "media": media,
        "caption": caption,
        "caption_entities": caption_entities,
        "is_album": False
    }

    if caption_entities:
        prev = await message.bot.send_photo(
            user_id, photo=input_photo, caption=caption,
            caption_entities=caption_entities, parse_mode=None
        )
    else:
        prev = await message.bot.send_photo(
            user_id, photo=input_photo, caption=caption, parse_mode=ParseMode.HTML
        )
    bot_messages[user_id].append(prev.message_id)
    preview_messages[user_id].append(prev.message_id)

    ask = await message.bot.send_message(
        user_id,
        "Готово. Отправить в канал?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Опубликовать", callback_data="post_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="post_cancel")]
        ])
    )
    bot_messages[user_id].append(ask.message_id)

    try:
        await status_msg.delete()
    except:
        pass
