import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.errors import UserNotParticipant
from pyrogram.enums import ChatType
from db import db
from ott.nf import get_netflix_data

# Credentials
BOT_TOKEN = "8603433381:AAFXNTkde8LbIzYO66Fajgxpde_DxDihops"
API_ID = 32541562
API_HASH = "e37e4432298d5a5eb4a6e32c18804283"
ADMINS = [7006602588] # Apna Admin ID yahan daalein
POWERED_BY = "@MrSagarBots"
UPDATE_CHANNEL_URL = "https://t.me/MrSagarBots"

TMDB_BASE_URL = "https://tmdbapi.the-zake.workers.dev/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"

app = Client("PremiumPosterBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# ==========================================
# 🛡 MIDDLEWARES (FSUB & AUTH GROUPS)
# ==========================================
async def check_access(client: Client, message: Message):
    """FSub aur Authorized Groups check karta hai"""
    settings = await db.get_settings()
    
    # 1. Group Authorization Check
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        auth_groups = settings.get("auth_groups", [])
        if message.chat.id not in auth_groups:
            await message.reply_text("⚠️ Ye bot is group me allowed nahi hai! Contact Admin.")
            await message.chat.leave()
            return False
        return True # Group check pass
        
    # 2. Private Chat FSub Check
    if message.chat.type == ChatType.PRIVATE:
        fsub_id = settings.get("fsub_id")
        fsub_link = settings.get("fsub_link")
        
        if fsub_id and fsub_link:
            try:
                await client.get_chat_member(fsub_id, message.from_user.id)
            except UserNotParticipant:
                btn = [[InlineKeyboardButton("📢 Join Channel", url=fsub_link)]]
                await message.reply_text(
                    "⚠️ **Access Denied!**\n\nBot use karne ke liye pehle hamara official channel join karein.",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return False
            except Exception as e:
                print(f"FSub Error: {e}")
                
    return True

# ==========================================
# 👑 ADMIN PANEL COMMANDS
# ==========================================
@app.on_message(filters.command("admin") & filters.user(ADMINS))
async def admin_dashboard(client: Client, message: Message):
    settings = await db.get_settings()
    total = await db.total_users()
    
    text = (
        "👑 **Admin Dashboard** 👑\n\n"
        f"👥 **Total Users:** {total}\n"
        f"📢 **FSub Channel:** `{settings.get('fsub_id', 'Not Set')}`\n"
        f"📝 **Log Channel:** `{settings.get('log_channel', 'Not Set')}`\n"
        f"🛡 **Auth Groups Count:** {len(settings.get('auth_groups', []))}\n\n"
        "**Commands:**\n"
        "`/setfsub <channel_id> <link>` - Set Force Sub\n"
        "`/setlog <channel_id>` - Set New User Alerts\n"
        "`/auth` - Group me command deke authorize karein\n"
        "`/broadcast` (Reply to msg) - Sabko msg bhejein"
    )
    await message.reply_text(text)

@app.on_message(filters.command("setfsub") & filters.user(ADMINS))
async def set_fsub(client, message):
    try:
        _, ch_id, link = message.text.split(" ", 2)
        await db.update_setting("fsub_id", int(ch_id))
        await db.update_setting("fsub_link", link)
        await message.reply_text(f"✅ FSub Set Successfully!\nID: {ch_id}\nLink: {link}")
    except:
        await message.reply_text("❌ Syntax Error: `/setfsub -100xxxx https://t.me/...`")

@app.on_message(filters.command("setlog") & filters.user(ADMINS))
async def set_log(client, message):
    try:
        ch_id = int(message.command[1])
        await db.update_setting("log_channel", ch_id)
        await message.reply_text(f"✅ Log Channel Set to: {ch_id}")
    except:
        await message.reply_text("❌ Syntax Error: `/setlog -100xxxx`")

@app.on_message(filters.command("auth") & filters.user(ADMINS) & filters.group)
async def auth_group(client, message):
    await db.add_auth_group(message.chat.id)
    await message.reply_text(f"✅ Ye group ab authorized hai! Bot yahan kaam karega.")

@app.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast_msg(client, message):
    if not message.reply_to_message:
        return await message.reply_text("⚠️ Kripya us message par reply karein jise broadcast karna hai.")
    
    msg = await message.reply_text("🚀 Broadcasting started...")
    users = await db.get_all_users()
    success, failed = 0, 0
    
    async for user in users:
        try:
            await message.reply_to_message.copy(user["_id"])
            success += 1
            await asyncio.sleep(0.1) # Flood wait avoid
        except:
            failed += 1
            
    await msg.edit_text(f"✅ **Broadcast Complete!**\n\n🟢 Success: {success}\n🔴 Failed: {failed}")

# ==========================================
# 🎬 MAIN BOT COMMANDS
# ==========================================
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    if not await check_access(client, message): return
    
    # New User Logic & Logging
    is_new = await db.add_user(message.from_user.id)
    if is_new:
        settings = await db.get_settings()
        log_id = settings.get("log_channel")
        if log_id:
            try:
                await client.send_message(log_id, f"🆕 **New User Alert!**\n\n👤 Name: {message.from_user.mention}\n🆔 ID: `{message.from_user.id}`")
            except: pass

    text = "🔥 **Premium Poster Extract Bot** 🔥\n\n🎬 `/p {name}` - Posters/Screenshots.\n🟥 `/nf {url}` - Netflix thumbnail."
    await message.reply_text(text)

@app.on_message(filters.command("nf"))
async def scrape_netflix_cmd(client: Client, message: Message):
    if not await check_access(client, message): return
    if len(message.command) < 2: return await message.reply_text("Example: `/nf https://www.netflix.com/title/...`")
    
    url = message.text.split(" ", 1)[1].strip()
    msg = await message.reply_text("🟥 Netflix link scrape kar raha hoon... ⏳")
    netflix_data = get_netflix_data(url)
    
    if netflix_data:
        caption_text = f"{message.from_user.mention}\n`/nf {url}`\n\n**Netflix Poster:**\n{netflix_data['main_poster']}\n\n**Portrait:** [Click Here]({netflix_data['portrait']})\n\n**Cover:** [Click Here]({netflix_data['cover']})\n\n**{netflix_data['title']}**"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Update Channel", url=UPDATE_CHANNEL_URL)]])
        await message.reply_photo(photo=netflix_data['main_poster'], caption=caption_text, reply_markup=buttons)
        await msg.delete()
    else:
        await msg.edit_text("⚠️ Sorry, link invalid ya blocked hai.")

@app.on_message(filters.command("p"))
async def search_media(client: Client, message: Message):
    if not await check_access(client, message): return
    if len(message.command) < 2: return await message.reply_text("Example: `/p Alpha`")
    
    query = message.text.split(" ", 1)[1].strip()
    msg = await message.reply_text(f"🔍 Searching for '{query}'...")
    
    res = requests.get(f"{TMDB_BASE_URL}/search/multi", params={"query": query}).json()
    filtered_results = [r for r in res.get("results", []) if r.get("media_type") in ["movie", "tv"]]
    
    if not filtered_results: return await msg.edit_text("Sorry, aisi koi Movie/Series nahi mili.")

    buttons = []
    for item in filtered_results[:6]:
        title = item.get('title') or item.get('name', 'Unknown')
        date = item.get('release_date') or item.get('first_air_date', '')
        year = date[:4] if date else "N/A"
        icon = "🎬" if item.get('media_type') == "movie" else "📺"
        buttons.append([InlineKeyboardButton(f"{icon} {title} ({year})", callback_data=f"opt_{item.get('media_type')}_{item.get('id')}")])
    
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_menu")])
    await msg.edit_text(f"🔍 Search: **{query}**\n\n✨ **Select a Movie or Series:**", reply_markup=InlineKeyboardMarkup(buttons))

# --- CATEGORY MENU (Smart Filter Logic Added) ---
@app.on_callback_query(filters.regex(r"^opt_"))
async def show_options(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    m_type, m_id = data[1], data[2]
    
    buttons = [
        [InlineKeyboardButton("🖼 Thumbnails (With Text)", callback_data=f"img_text_{m_type}_{m_id}_0")],
        [InlineKeyboardButton("🌄 Screenshots (Clean/N/A)", callback_data=f"img_notext_{m_type}_{m_id}_0")],
        [InlineKeyboardButton("🅰 Logos", callback_data=f"img_logos_{m_type}_{m_id}_0")],
        [InlineKeyboardButton("❌ Close", callback_data="close_menu")]
    ]
    await callback_query.message.edit_text("✨ **Choose Image Type:**", reply_markup=InlineKeyboardMarkup(buttons))

# --- IMAGE VIEWER & PAGINATION ---
@app.on_callback_query(filters.regex(r"^img_"))
async def paginate_images(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    filter_type, m_type, m_id, index = data[1], data[2], data[3], int(data[4])
    
    movie_info = requests.get(f"{TMDB_BASE_URL}/{m_type}/{m_id}").json()
    name = movie_info.get("title") or movie_info.get("name", "Unknown")
    
    res = requests.get(f"{TMDB_BASE_URL}/{m_type}/{m_id}/images").json()
    
    # Smart Filtering Logic
    if filter_type == "logos":
        raw_images = res.get("logos", [])
    else:
        # Both thumbnails and screenshots come from backdrops/posters. 
        # Using backdrops as they usually have the clean vs text variations.
        raw_images = res.get("backdrops", []) + res.get("posters", [])
        
    if filter_type == "text":
        # Jisme language (iso_639_1) likhi ho wo Thumbnails
        images_list = [img for img in raw_images if img.get('iso_639_1') is not None]
    elif filter_type == "notext":
        # Jisme language N/A ya None ho wo Screenshots
        images_list = [img for img in raw_images if img.get('iso_639_1') is None or img.get('iso_639_1') == "xx"]
    else:
        images_list = raw_images
        
    if not images_list:
        return await callback_query.answer("Is category me image nahi mili!", show_alert=True)
        
    if index >= len(images_list) or index < 0: index = 0
    img_data = images_list[index]
    full_image_url = f"{TMDB_IMAGE_BASE}{img_data['file_path']}"
    
    # Caption Setup
    lang = img_data.get('iso_639_1')
    lang_display = lang if lang else "N/A (Clean)"
    cat_display = "Thumbnail" if filter_type == "text" else "Screenshot" if filter_type == "notext" else "Logo"
    
    caption_text = (
        f"🔍 **Search:** {name}\n\n"
        f"• **Category:** {cat_display}\n"
        f"• **Language:** {lang_display}\n"
        f"• **Size:** {img_data.get('width')}x{img_data.get('height')}\n"
        f"• **Image:** [Link (JPG)]({full_image_url})\n\n"
        f"🚀 **Powered By** {POWERED_BY}"
    )
    cb_prefix = f"img_{filter_type}_{m_type}_{m_id}"

    nav_buttons = []
    if index > 0: nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{cb_prefix}_{index-1}"))
    else: nav_buttons.append(InlineKeyboardButton("⛔", callback_data="ignore"))
        
    nav_buttons.append(InlineKeyboardButton(f"{index + 1}/{len(images_list)}", callback_data="ignore"))
    
    if index < len(images_list) - 1: nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{cb_prefix}_{index+1}"))
    else: nav_buttons.append(InlineKeyboardButton("⛔", callback_data="ignore"))
        
    markup = InlineKeyboardMarkup([
        nav_buttons,
        [InlineKeyboardButton("🔙 Back", callback_data=f"opt_{m_type}_{m_id}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_menu")]
    ])
    
    try:
        if not callback_query.message.photo:
            await callback_query.message.delete()
            await client.send_photo(chat_id=callback_query.message.chat.id, photo=full_image_url, caption=caption_text, reply_markup=markup)
        else:
            await client.edit_message_media(chat_id=callback_query.message.chat.id, message_id=callback_query.message.id, media=InputMediaPhoto(media=full_image_url, caption=caption_text), reply_markup=markup)
    except Exception as e:
        await callback_query.answer("Error loading image!", show_alert=True)

@app.on_callback_query(filters.regex("close_menu"))
async def close_menu(client, callback_query):
    await callback_query.message.delete()

@app.on_callback_query(filters.regex("ignore"))
async def ignore_btn(client, callback_query):
    await callback_query.answer()

if __name__ == "__main__":
    app.run()
