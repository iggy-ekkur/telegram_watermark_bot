from aiogram import Bot

async def check_admin_permissions(bot: Bot, channel_id: str, user_id: int) -> tuple[bool, str]:
    try:
        bot_id = (await bot.me()).id
        bot_member = await bot.get_chat_member(channel_id, bot_id)
        user_member = await bot.get_chat_member(channel_id, user_id)

        if bot_member.status not in ["administrator", "creator"]:
            return False, "❌ Бот не является админом в этом канале."

        if user_member.status not in ["administrator", "creator"]:
            return False, "❌ Ты не являешься админом в этом канале."

        return True, ""
    except Exception as e:
        return False, f"❌ Ошибка доступа к каналу: {e}"
