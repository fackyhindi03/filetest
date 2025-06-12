import json
import os
import base64
from aiohttp import web
from urllib.parse import unquote, quote_plus
from pyrogram import Client
from TechVJ.utils.file_properties import get_name, get_hash

# Configuration
API_ID = 27999679                  # Your Pyrogram API ID
API_HASH = "f553398ca957b9c92bcb672b05557038"      # Your Pyrogram API HASH
BOT_TOKEN = "7947042930:AAE14yUT642RjiiwkaM_dgoGazQdh54SkcU"    # Your bot token
LOG_CHANNEL = -1002631218069     # Your log channel ID
URL = "https://file-sharing-j1yu.onrender.com/"    # Base URL of your file server

# Initialize Pyrogram Client
app_bot = Client("file_sharing_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def batch_handler(request):
    # Extract path and query params
    batch_id = request.match_info['batch_id']
    filename = request.match_info['filename']
    hash_token = request.query.get('hash', '')

    # Fetch the JSON batch message
    try:
        decode_id = base64.urlsafe_b64decode(batch_id + "=" * (-len(batch_id) % 4)).decode('ascii')
        batch_msg = await app_bot.get_messages(LOG_CHANNEL, int(decode_id))
    except Exception:
        return web.Response(status=404, text="Batch not found")

    # Download and parse JSON
    tmp_file = await app_bot.download_media(batch_msg)
    try:
        with open(tmp_file, 'r') as f:
            entries = json.load(f)
    except Exception:
        os.remove(tmp_file)
        return web.Response(status=500, text="Invalid batch JSON")
    os.remove(tmp_file)

    # Build HTML list of links
    items = []
    for item in entries:
        cid = int(item.get('channel_id', 0))
        mid = int(item.get('msg_id', 0))
        real_msg = await app_bot.get_messages(cid, mid)
        if not real_msg:
            continue
        m = real_msg[0]
        name_q = quote_plus(get_name(m))
        d_url = f"{URL}{mid}/{name_q}?hash={get_hash(m)}"
        s_url = f"{URL}watch/{mid}/{name_q}?hash={get_hash(m)}"
        items.append(f"<li><strong>{get_name(m)}</strong>: "
                     f"<a href='{d_url}'>Download</a> | "
                     f"<a href='{s_url}'>Stream</a></li>")

    if not items:
        return web.Response(status=404, text="No valid files in batch")

    html = f"<html><body><h3>Batch Files</h3><ul>{''.join(items)}</ul></body></html>"
    return web.Response(body=html, content_type='text/html')


async def file_handler(request):
    # Extract params
    msg_id = request.match_info['msg_id']
    filename = unquote(request.match_info['filename'])
    hash_token = request.query.get('hash', '')

    # Fetch the logged file message
    try:
        msg = await app_bot.get_messages(LOG_CHANNEL, int(msg_id))
    except Exception:
        return web.Response(status=404, text="File not found")

    if not msg or not msg.media:
        return web.Response(status=404, text="File not found")

    m = msg[0]
    # Validate hash
    if hash_token != get_hash(m):
        return web.Response(status=403, text="Invalid hash")

    # Download the media locally
    tmp = await app_bot.download_media(m)
    if not tmp:
        return web.Response(status=500, text="Download error")

    # Send file as response
    resp = web.FileResponse(path=tmp)
    # Optionally cleanup after sending
    resp.on_cleanup.append(lambda _: os.remove(tmp))
    return resp


async def favicon_handler(request):
    # Prevent 500 on favicon requests
    return web.Response(status=404)


def main():
    # Start the Pyrogram client
    app_bot.start()

    # Build and run aiohttp app
    app = web.Application()
    app.router.add_get('/favicon.ico', favicon_handler)
    app.router.add_get('/batch/{batch_id}/{filename}', batch_handler)
    app.router.add_get('/watch/{msg_id}/{filename}', file_handler)
    app.router.add_get('/{msg_id}/{filename}', file_handler)
    web.run_app(app, host='0.0.0.0', port=8080)


if __name__ == '__main__':
    main()
