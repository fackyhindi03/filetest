# plugins/force_sub.py
from typing import List
from pyrogram import Client, enums
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid, ChannelPrivate
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import FORCE_SUB, FS_TEXT

def _channels() -> List: # Can be list of int or str
    if not FORCE_SUB:
        return []
    if isinstance(FORCE_SUB, (str, int)):
        return [FORCE_SUB]
    if isinstance(FORCE_SUB, list):
        return FORCE_SUB # Already a list from config
    return []

async def _invite_link(client: Client, chat: str) -> str:
    try:
        ch = await client.get_chat(chat)
        if ch.username:  # public
            return f"https://t.me/{ch.username}"
        # private – requires bot admin to export
        try:
            return await client.export_chat_invite_link(ch.id)
        except ChatAdminRequired:
            return "https://t.me/"
    except Exception as e:
        print(f"[ForceSub] invite link error for {chat}: {e}")
        return "https://t.me/"

async def ensure_subscribed(client: Client, message) -> bool:
    chs = _channels()
    if not chs:
        return True
    if not getattr(message, "from_user", None):
        return True

    user_id = message.from_user.id
    missing = []

    for ch in chs:
        try:
            m = await client.get_chat_member(ch, user_id)
            if m.status not in ("member", "administrator", "creator"):
                missing.append(ch)
        except UserNotParticipant:
            missing.append(ch)
        except (ChannelPrivate, PeerIdInvalid) as e:
            print(f"[ForceSub] cannot check {ch}: {e}")
            missing.append(ch)
        except ChatAdminRequired:
            print(f"[ForceSub] bot must be admin in {ch}")
            missing.append(ch)
        except Exception as e:
            print(f"[ForceSub] unexpected error for {ch}: {e}")
            missing.append(ch)

    if not missing:
        return True

    # If this was /start with a payload, preserve it in callback_data
    retry_cmd = ""
    if getattr(message, "text", None) and message.text.startswith("/start"):
        retry_cmd = message.text  # "/start <payload>"

    rows = []
    for ch in missing:
        url = await _invite_link(client, ch)
        rows.append([InlineKeyboardButton(f"Join {ch.lstrip('@')}", url=url)])

    # include prior command (if any) so we can resume exactly
    cbdata = "fsub_check" + (f"|{retry_cmd}" if retry_cmd else "")
    rows.append([InlineKeyboardButton("✅ I’ve joined", callback_data=cbdata)])

    await message.reply_text(
        FS_TEXT,
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode=enums.ParseMode.MARKDOWN
    )
    return False
