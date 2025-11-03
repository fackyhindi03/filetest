# plugins/force_sub.py

from typing import List
from pyrogram import Client, enums
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid, ChannelPrivate
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import FORCE_SUB, FS_TEXT


def _channels() -> List[str]:
    if not FORCE_SUB:
        return []
    if isinstance(FORCE_SUB, str):
        return [FORCE_SUB]
    return list(FORCE_SUB)


async def _invite_link(client: Client, chat: str) -> str:
    try:
        chat_obj = await client.get_chat(chat)
        if chat_obj.username:
            return f"https://t.me/{chat_obj.username}"
        try:
            return await client.export_chat_invite_link(chat_obj.id)
        except ChatAdminRequired:
            return "https://t.me/"
    except Exception as e:
        print(f"[ForceSub] invite link error: {e}")
        return "https://t.me/"


async def ensure_subscribed(client: Client, message) -> bool:
    chs = _channels()
    if not chs:
        return True

    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return True

    missing = []

    for ch in chs:
        try:
            member = await client.get_chat_member(ch, user_id)
            if member.status not in ("member", "administrator", "creator"):
                missing.append(ch)
        except UserNotParticipant:
            missing.append(ch)
        except (ChannelPrivate, PeerIdInvalid) as e:
            print(f"[ForceSub] Cannot check channel {ch}: {e}")
            missing.append(ch)
        except ChatAdminRequired:
            print(f"[ForceSub] Bot must be admin in {ch}")
            missing.append(ch)
        except Exception as e:
            print(f"[ForceSub] Unexpected error checking {ch}: {e}")
            missing.append(ch)

    if not missing:
        return True

    # Ask user to join
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
