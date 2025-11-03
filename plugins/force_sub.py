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

async def _invite_link(client: Client, chat_id: int | str) -> (str, str):
    """Returns (invite_link, chat_display_name)"""
    try:
        ch = await client.get_chat(chat_id)
        display_name = ch.title or (f"@{ch.username}" if ch.username else str(chat_id))
        
        if ch.username:  # public
            return f"https://t.me/{ch.username}", display_name
        
        # private – requires bot admin to export
        try:
            link = await client.export_chat_invite_link(ch.id)
            return link, display_name
        except ChatAdminRequired:
            return "https://t.me/", display_name # Cannot get link
            
    except Exception as e:
        print(f"[ForceSub] invite link error for {chat_id}: {e}")
        return "https://t.me/", str(chat_id) # Fallback
        

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
            print(f"[Debug] Checking membership for user {user_id} in channel {ch}...")
            m = await client.get_chat_member(ch, user_id)
    
            # --- THIS IS THE FIX ---
            if m.status not in (enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.CREATOR):
            # --- END OF FIX ---
                print(f"[Debug] User is in channel, but has status: {m.status}. Adding to missing.")
                missing.append(ch)
            else:
                print(f"[Debug] User is confirmed member with status: {m.status}.")
    
        except UserNotParticipant:
            print(f"[Debug] UserNotParticipant error. User is NOT in channel. Adding to missing.")
            missing.append(ch)
        except (ChannelPrivate, PeerIdInvalid) as e:
            print(f"[Debug] Cannot check {ch}: {e}. Bot may not be in channel. Adding to missing.")
            missing.append(ch)
        except ChatAdminRequired:
            print(f"[Debug] ChatAdminRequired error. Bot is NOT ADMIN in {ch}. Adding to missing.")
            missing.append(ch)
        except Exception as e:
            print(f"[Debug] unexpected error for {ch}: {e}")
            missing.append(ch)

    if not missing:
        return True

    # If this was /start with a payload, preserve it in callback_data
    retry_cmd = ""
    if getattr(message, "text", None) and message.text.startswith("/start"):
        retry_cmd = message.text  # "/start <payload>"

    rows = []
    for ch in missing:
        url, display_name = await _invite_link(client, ch) # Get both link and name
        rows.append([InlineKeyboardButton(f"Join {display_name}", url=url)]) # Use the display_name

    # include prior command (if any) so we can resume exactly
    cbdata = "fsub_check" + (f"|{retry_cmd}" if retry_cmd else "")
    rows.append([InlineKeyboardButton("✅ I’ve joined", callback_data=cbdata)])

    await message.reply_text(
        FS_TEXT,
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode=enums.ParseMode.MARKDOWN
    )
    return False
