"""
Telegram Service Message Cleaner Bot
=====================================
Guruh/kanalga qo'shilish va chiqish xabarlarini avtomatik o'chiradi.

O'chiriladigan xabar turlari:
  - "User joined the group/channel"
  - "User was added by ..."
  - "User left the group/channel"
  - "User was removed by ..."

O'rnatish:
  pip install python-telegram-bot==21.*

Ishlatish:
  BOT_TOKEN=<token> python bot.py
  yoki .env fayl orqali (python-dotenv o'rnatilgan bo'lsa)
"""

import logging
import os

from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    Application,
    ChatMemberHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Handler: a'zolik o'zgarishlari (joined / left / added / removed)
# ---------------------------------------------------------------------------
async def log_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    ChatMember updatelarini tutib log yozadi (xabar o'chirish shart emas,
    chunki service xabarni alohida handler o'chiradi).
    """
    member_update = update.chat_member or update.my_chat_member
    if not member_update:
        return

    chat = member_update.chat
    logger.info(
        "ChatMember update | chat=%s (%s) | user=%s | %s -> %s",
        chat.title or chat.id,
        chat.type,
        member_update.new_chat_member.user.full_name,
        member_update.old_status,
        member_update.new_status,
    )


async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Guruhga qo'shilish / chiqish haqidagi service xabarlarini o'chiradi.

    Telegram bu xabarlarni Message.new_chat_members va
    Message.left_chat_member maydonlari orqali uzatadi.
    """
    message = update.effective_message
    if message is None:
        return

    chat_title = update.effective_chat.title or str(update.effective_chat.id)

    if message.new_chat_members:
        names = [u.full_name for u in message.new_chat_members]
        reason = f"joined/added: {', '.join(names)}"
    elif message.left_chat_member:
        reason = f"left/removed: {message.left_chat_member.full_name}"
    else:
        return

    try:
        await message.delete()
        logger.info("Deleted (%s) in [%s] | msg_id=%s", reason, chat_title, message.message_id)
    except BadRequest as exc:
        logger.warning("BadRequest deleting msg %s: %s", message.message_id, exc)
    except Forbidden as exc:
        logger.error(
            "Bot has no delete permission in [%s]: %s  "
            "-> Botga 'Delete messages' ruxsati bering!",
            chat_title,
            exc,
        )


# ---------------------------------------------------------------------------
# Asosiy funksiya
# ---------------------------------------------------------------------------
def main() -> None:
    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN topilmadi!\n"
            "  export BOT_TOKEN='7123456789:AAF...'  qilib ishga tushiring."
        )

    app = Application.builder().token(token).build()

    # ChatMemberHandler - a'zolik o'zgarishlarini log qilish
    app.add_handler(
        ChatMemberHandler(
            log_member_update,
            chat_member_types=ChatMemberHandler.CHAT_MEMBER,
        )
    )

    # new_chat_members -> "X joined" / "X was added by Y"
    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            delete_service_message,
        )
    )

    # left_chat_member -> "X left" / "X was removed by Y"
    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.LEFT_CHAT_MEMBER,
            delete_service_message,
        )
    )

    logger.info("Bot ishga tushdi. Toxtatish uchun Ctrl+C bosing.")
    app.run_polling(
        allowed_updates=[
            Update.MESSAGE,
            Update.CHAT_MEMBER,
            Update.MY_CHAT_MEMBER,
        ]
    )


if __name__ == "__main__":
    main()