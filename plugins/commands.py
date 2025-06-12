# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import logging
import random
import asyncio
import json
import base64
import re
from urllib.parse import quote_plus

from validators import domain
from Script import script
from plugins.dbusers import db
from plugins.users_api import get_user, update_user_info
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import *
from utils import verify_user, check_token, check_verification, get_token
from config import *
from TechVJ.utils.file_properties import get_name, get_hash, get_media_file_size

logger = logging.getLogger(__name__)

BATCH_FILES = {}


def get_size(size):
    """Get size in readable format"""
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units) - 1:
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])


def formate_file_name(file_name):
    chars = ["[", "]", "(", ")"]
    for c in chars:
        file_name = file_name.replace(c, "")
    file_name = ' '.join(
        filter(
            lambda x: not x.startswith('http') and not x.startswith('@') and not x.startswith('www.'),
            file_name.split()
        )
    )
    return file_name


@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    username = client.me.username
    # add user to db
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT.format(
            message.from_user.id, message.from_user.mention))

    # simple start menu
    if len(message.command) != 2:
        buttons = [[
            InlineKeyboardButton(
                '💝 sᴜʙsᴄʀɪʙᴇ ᴍʏ ʏᴏᴜᴛᴜʙᴇ ᴄʜᴀɴɴᴇʟ',
                url='https://youtube.com/@chineseanimeshort?si=jSRmbRrsfm_P_95c'
            )
        ], [
            InlineKeyboardButton('🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ', url='https://t.me/Facky_Request_Talk_Group'),
            InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/Facky_Hindi_Donghua')
        ], [
            InlineKeyboardButton('💁‍♀️ ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('😊 ᴀʙᴏᴜᴛ', callback_data='about')
        ]]
        if CLONE_MODE:
            buttons.append([
                InlineKeyboardButton('🤖 ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')
            ])
        reply_markup = InlineKeyboardMarkup(buttons)
        me = client.me
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(
                message.from_user.mention, me.mention
            ),
            reply_markup=reply_markup
        )
        return

    data = message.command[1]
    # verify flow
    try:
        pre, file_id = data.split('_', 1)
    except ValueError:
        file_id = data
        pre = ""

    # handle verification link
    if data.startswith("verify-"):
        parts = data.split("-", 2)
        userid, token = parts[1], parts[2]
        if str(message.from_user.id) != userid:
            return await message.reply_text(
                text="<b>Invalid link or Expired link !</b>",
                protect_content=True
            )
        is_valid = await check_token(client, userid, token)
        if is_valid:
            await message.reply_text(
                text=f"<b>Hey {message.from_user.mention}, You are successfully verified !\n" \
                     "Now you have unlimited access for all files for 8 Hours.</b>",
                protect_content=True
            )
            await verify_user(client, userid, token)
        else:
            return await message.reply_text(
                text="<b>Invalid link or Expired link !</b>",
                protect_content=True
            )
        return

    # batch download flow
    if data.startswith("BATCH-"):
        # ensure verification if needed
        if VERIFY_MODE and not await check_verification(client, message.from_user.id):
            btn = [[
                InlineKeyboardButton(
                    "Verify",
                    url=await get_token(
                        client, message.from_user.id,
                        f"https://telegram.me/{username}?start="
                    )
                )
            ], [
                InlineKeyboardButton(
                    "How To Open Link & Verify",
                    url=VERIFY_TUTORIAL
                )
            ]]
            return await message.reply_text(
                text="<b>You are not verified !\nKindly verify to continue !</b>",
                protect_content=True,
                reply_markup=InlineKeyboardMarkup(btn)
            )

        sts = await message.reply("**🔺 ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ**")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            decode_file_id = base64.urlsafe_b64decode(
                file_id + "=" * (-len(file_id) % 4)
            ).decode("ascii")
            msg = await client.get_messages(LOG_CHANNEL, int(decode_file_id))
            media = getattr(msg, msg.media.value)
            file = await client.download_media(media.file_id)
            try:
                with open(file, 'r') as f:
                    msgs = json.loads(f.read())
            except Exception:
                await sts.edit("FAILED")
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs

        filesarr = []
        for m in msgs:
            channel_id = int(m.get("channel_id"))
            msgid = int(m.get("msg_id"))
            info = await client.get_messages(channel_id, msgid)
            if not info:
                continue
            info = info[0]
            # prepare caption and metadata
            f_caption = getattr(info, 'caption', '')
            if f_caption:
                f_caption = f_caption.html
            old_title = getattr(info.media, 'file_name', '')
            title = formate_file_name(old_title)
            size = get_size(getattr(info.media, 'file_size', 0))
            if BATCH_FILE_CAPTION:
                try:
                    f_caption = BATCH_FILE_CAPTION.format(
                        file_name=title or '',
                        file_size=size or '',
                        file_caption=f_caption or ''
                    )
                except Exception:
                    pass
            if not f_caption:
                f_caption = title

            # STREAM_MODE buttons
            if STREAM_MODE:
                if info.video or info.document:
                    file_name_q = quote_plus(get_name(info))
                    stream_url = f"{URL}watch/{info.id}/{file_name_q}?hash={get_hash(info)}"
                    download_url = f"{URL}{info.id}/{file_name_q}?hash={get_hash(info)}"
                    buttons = [
                        [
                            InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download_url),
                            InlineKeyboardButton("• ᴡᴀᴛᴄʜ •", url=stream_url)
                        ],
                        [
                            InlineKeyboardButton(
                                "• ᴡᴀᴛᴄʜ ɪɴ ᴡᴇʙ ᴀᴘᴘ •",
                                web_app=WebAppInfo(url=stream_url)
                            )
                        ],
                    ]
                    reply_markup = InlineKeyboardMarkup(buttons)
                else:
                    reply_markup = None
            else:
                reply_markup = None

            # copy media to user
            try:
                sent = await info.copy(
                    chat_id=message.from_user.id,
                    caption=f_caption,
                    protect_content=False,
                    reply_markup=reply_markup
                )
            except FloodWait as e:
                await asyncio.sleep(e.value)
                sent = await info.copy(
                    chat_id=message.from_user.id,
                    caption=f_caption,
                    protect_content=False,
                    reply_markup=reply_markup
                )
            except Exception:
                continue

            filesarr.append(sent)
            await asyncio.sleep(1)

        await sts.delete()

        # auto-delete after sending
        if AUTO_DELETE_MODE:
            notice = await client.send_message(
                chat_id=message.from_user.id,
                text=(
                    f"<b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\n"
                    f"This Movie File/Video will be deleted in <b><u>{AUTO_DELETE} minutes</u></b>.\n"
                    "<i>(Due to Copyright Issues)</i>.\n\n"
                    "<b><i>Please forward this File/Video to your Saved Messages to download later</i></b>"
                )
            )
            await asyncio.sleep(AUTO_DELETE_TIME)
            for x in filesarr:
                try:
                    await x.delete()
                except Exception:
                    pass
            await notice.edit_text("<b>Your all files/videos have been deleted successfully!</b>")
        return

    # single file download/stream flow
    try:
        pre, decode_file_id = base64.urlsafe_b64decode(
            data + "=" * (-len(data) % 4)
        ).decode("ascii").split("_", 1)
    except Exception:
        return

    # verify if needed
    if VERIFY_MODE and not await check_verification(
        client, message.from_user.id
    ):
        btn = [[
            InlineKeyboardButton(
                "Verify",
                url=await get_token(
                    client, message.from_user.id,
                    f"https://telegram.me/{username}?start="
                )
            )
        ], [
            InlineKeyboardButton(
                "How To Open Link & Verify",
                url=VERIFY_TUTORIAL
            )
        ]]
        return await message.reply_text(
            text="<b>You are not verified !\nKindly verify to continue !</b>",
            protect_content=True,
            reply_markup=InlineKeyboardMarkup(btn)
        )

    # fetch log message
    msg = await client.get_messages(LOG_CHANNEL, int(decode_file_id))
    if msg and msg.media:
        media = getattr(msg, msg.media.value)
        title = formate_file_name(getattr(media, 'file_name', ''))
        size = get_size(getattr(media, 'file_size', 0))
        caption = f"<code>{title}</code>"
        if CUSTOM_FILE_CAPTION:
            try:
                caption = CUSTOM_FILE_CAPTION.format(
                    file_name=title or '', file_size=size or '', file_caption=''  
                )
            except Exception:
                pass

        # STREAM_MODE buttons for single file
        if STREAM_MODE and (msg.video or msg.document):
            file_name_q = quote_plus(get_name(msg))
            stream_url = f"{URL}watch/{msg.id}/{file_name_q}?hash={get_hash(msg)}"
            download_url = f"{URL}{msg.id}/{file_name_q}?hash={get_hash(msg)}"
            buttons = [
                [
                    InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download_url),
                    InlineKeyboardButton("• ᴡᴀᴛᴄʜ •", url=stream_url)
                ],
                [
                    InlineKeyboardButton(
                        "• ᴡᴀᴛᴄʜ ɪɴ ᴡᴇʙ ᴀᴘᴘ •",
                        web_app=WebAppInfo(url=stream_url)
                    )
                ],
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
        else:
            reply_markup = None

        await msg.copy(
            chat_id=message.from_user.id,
            caption=caption,
            reply_markup=reply_markup,
            protect_content=False
        )

        # auto-delete single file
        if AUTO_DELETE_MODE:
            notice = await client.send_message(
                chat_id=message.from_user.id,
                text=(
                    f"<b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\n"
                    f"This file/video will be deleted in <b><u>{AUTO_DELETE} minutes</u></b>.\n"
                    "<i>(Due to Copyright Issues)</i>."
                )
            )
            await asyncio.sleep(AUTO_DELETE_TIME)
            try:
                await msg.delete()
            except Exception:
                pass
            await notice.edit_text("<b>Your file/video has been deleted successfully!</b>")
    return


@Client.on_message(filters.command('api') & filters.private)
async def shortener_api_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command

    if len(cmd) == 1:
        s = script.SHORTENER_API_MESSAGE.format(
            base_site=user['base_site'],
            shortener_api=user['shortener_api']
        )
        return await m.reply(s)

    elif len(cmd) == 2:
        api = cmd[1].strip()
        await update_user_info(user_id, {'shortener_api': api})
        await m.reply(
            '<b>Shortener API updated successfully to</b> ' + api
        )


@Client.on_message(filters.command("base_site") & filters.private)
async def base_site_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command
    help_text = (
        "`/base_site (base_site)`\n\n"
        "<b>Current base site: None\n\n EX:</b> `/base_site shortnerdomain.com`\n\n"
        "If You Want To Remove Base Site Then Paste `/base_site None`"
    )
    if len(cmd) == 1:
        return await m.reply(text=help_text, disable_web_page_preview=True)
    elif len(cmd) == 2:
        base_site = cmd[1].strip()
        if base_site.lower() == 'none':
            await update_user_info(user_id, {'base_site': None})
            return await m.reply('<b>Base Site removed successfully</b>')
        if not domain(base_site):
            return await m.reply(text=help_text, disable_web_page_preview=True)
        await update_user_info(user_id, {'base_site': base_site})
        await m.reply('<b>Base Site updated successfully</b>')


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == 'close_data':
        await query.message.delete()
    elif query.data == 'about':
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id,
            query.message.id,
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(me2),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == 'start':
        buttons = [[
            InlineKeyboardButton(
                '💝 sᴜʙsᴄʀɪʙᴇ ᴍʏ ʏᴏᴜᴛᴜʙᴇ ᴄʜᴀɴɴᴇʟ',
                url='https://youtube.com/@chineseanimeshort?si=jSRmbRrsfm_P_95c'
            )
        ], [
            InlineKeyboardButton('🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ', url='https://t.me/Facky_Request_Talk_Group'),
            InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/Facky_Hindi_Donghua')
        ], [
            InlineKeyboardButton('💁‍♀️ ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('😊 ᴀʙᴏᴜᴛ', callback_data='about')
        ]]
        if CLONE_MODE:
            buttons.append([
                InlineKeyboardButton('🤖 ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')
            ])
        await client.edit_message_media(
            query.message.chat.id,
            query.message.id,
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        await query.message.edit_text(
            text=script.START_TXT.format(
                query.from_user.mention, me2
            ),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == 'clone':
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id,
            query.message.id,
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CLONE_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == 'help':
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id,
            query.message.id,
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
