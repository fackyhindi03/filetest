# plugins/force_sub.py

from typing import List, Union
from pyrogram import Client, enums
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, ChannelPrivate
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import FORCE_SUB, FS_TEXT

def _channels() -> List[str]:
    if not FORCE_SUB:
        return []
    if isinstance(FORCE_SUB, str):
        return [FORCE_SUB]
    return list(FORCE_SUB)

async def _invite_link(client: Client, chat: str) -> str:
    """
    Return a usable join link for a channel.
    - If public: https://t.me/username
    - If private: export a new invite link (requires bot admin in channel)
    """
    try:
        chat_obj = await client.get_chat(chat)
        if chat_obj.username:  # public
            return f"https://t.me/{chat_obj.username}"
        # private – need admin privilege to export invite
        try:
            link = await client.export_chat_invite_link(chat_obj.id)
            return link
        except ChatAdminRequired:
            # Fallback – won’t work for private channels but avoids crash
            return "https://t.me/"
    except Exception:
        return "https://t.me/"

async def ensure_subscribed(client: Client, message) -> bool:
    """
    Gatekeeper: returns True if user is subscribed to every channel in FORCE_SUB.
    If not, it sends a join UI and returns False.
    """
    chs = _channels()
    if not chs:
        return True

    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return True

    missing = []
    for ch in chs:
        try:
            await client.get_chat_member(ch, user_id)
        except UserNotParticipant:
            missing.append(ch)
        except ChannelPrivate:
            # Channel is private; if user not member it will behave like not participant
            missing.append(ch)
        except Exception:
            # On any unexpected error, don’t block the user
            pass

    if not missing:
        return True

    # Build buttons for all missing channels + recheck button
    rows = []
    for ch in missing:
        url = await _invite_link(client, ch)
        rows.append([InlineKeyboardButton(f"Join {ch.lstrip('@')}", url=url)])

    rows.append([InlineKeyboardButton("✅ I’ve joined", callback_data="fsub_check")])

    await message.reply_text(
        FS_TEXT,
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode=enums.ParseMode.MARKDOWN
    )
    return False
