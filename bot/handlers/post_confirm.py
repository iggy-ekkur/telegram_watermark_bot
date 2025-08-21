from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.enums import ParseMode
from aiogram.types import InputMediaPhoto, InputMediaVideo

from bot.utils.is_admin import check_admin_permissions
from bot.storage import (
    post_cache,
    user_channels,
    user_messages,
    bot_messages,
    protected_messages,
    preview_messages,
    publishing_in_progress,   # флаг защиты от двойного клика
)

router = Router()

async def cleanup_bot_messages(bot, user_id: int, keep_ids: set[int] | None = None):
    """
    Удаляем служебные сообщения бота (превью не трогаем),
    не трогаем:
      - protected_messages[user_id]
      - preview_messages[user_id]
      - keep_ids (например, текущее callback.message)
    """
    prot = set(protected_messages.get(user_id, set()))
    prev = set(preview_messages.get(user_id, []))
    keep = set(keep_ids or set())
    skip = prot | prev | keep

    for msg_id in bot_messages.get(user_id, []):
        if msg_id in skip:
            continue
        try:
            await bot.delete_message(chat_id=user_id, message_id=msg_id)
        except:
            pass
    bot_messages.get(user_id, []).clear()


@router.callback_query(F.data == "post_confirm")
async def confirm_post(callback: CallbackQuery):
    user_id = callback.from_user.id

    # анти-даблклик
    if publishing_in_progress[user_id]:
        await callback.answer("⏳ Уже публикую…")
        return
    publishing_in_progress[user_id] = True

    await callback.answer("📤 Публикую пост...")

    post_data = post_cache.get(user_id)
    if not post_data:
        publishing_in_progress[user_id] = False
        await callback.message.answer("❌ Нет сохранённого поста.")
        return

    channel_id = user_channels[user_id]
    ok, error_msg = await check_admin_permissions(callback.bot, channel_id, user_id)
    if not ok:
        publishing_in_progress[user_id] = False
        await callback.message.answer(error_msg)
        return

    caption: str = post_data.get("caption", "") or ""
    caption_entities = post_data.get("caption_entities")
    media = post_data["media"]
    is_album: bool = post_data.get("is_album", False)

    try:
        # ===== Публикация =====
        if is_album:
            if media:
                first = media[0]
                if isinstance(first, (InputMediaPhoto, InputMediaVideo)):
                    if caption_entities:
                        first.caption = caption
                        first.caption_entities = caption_entities
                        first.parse_mode = None
                    else:
                        first.caption = caption or None
                        first.parse_mode = ParseMode.HTML
                # остальные — без подписи
                for m in media[1:]:
                    m.caption = None
                    m.caption_entities = None
                    m.parse_mode = None

            await callback.bot.send_media_group(chat_id=channel_id, media=media)

        else:
            if caption_entities:
                await callback.bot.send_photo(
                    chat_id=channel_id,
                    photo=media[0].media,
                    caption=caption,
                    caption_entities=caption_entities,
                    parse_mode=None
                )
            else:
                await callback.bot.send_photo(
                    chat_id=channel_id,
                    photo=media[0].media,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )

        # ===== Сначала редактируем кнопочное сообщение =====
        try:
            await callback.message.edit_text(
                f"✅ Пост опубликован в <code>{channel_id}</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        # ===== Потом чистим служебные сообщения (не трогаем превью/текущее) =====
        await cleanup_bot_messages(callback.bot, user_id, keep_ids={callback.message.message_id})

        # Чистим сообщения пользователя
        for msg_id in user_messages.get(user_id, []):
            try:
                await callback.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except:
                pass
        user_messages.get(user_id, []).clear()

        # Кэш поста можно очистить, превью оставляем в чате
        post_cache.pop(user_id, None)

    except Exception as e:
        await callback.bot.send_message(chat_id=user_id, text=f"❌ Ошибка при публикации: {e}")
    finally:
        publishing_in_progress[user_id] = False


@router.callback_query(F.data == "post_cancel")
async def cancel_post(callback: CallbackQuery):
    user_id = callback.from_user.id

    # редактируем кнопочное сообщение
    try:
        await callback.message.edit_text("❌ Публикация отменена")
    except Exception:
        try:
            await callback.message.answer("❌ Публикация отменена")
        except Exception:
            pass

    # чистим служебные (без превью и без текущего)
    await cleanup_bot_messages(callback.bot, user_id, keep_ids={callback.message.message_id})

    # чистим сообщения пользователя и кэш
    user_messages.get(user_id, []).clear()
    post_cache.pop(user_id, None)
