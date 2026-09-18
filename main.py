import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import requests
import io
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.enums import ChatType
from pyrogram.errors import UserNotParticipant
from db import db
from ott.ott import OTT_PLATFORMS, scrape_ott
from commands import get_help_text

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8603433381:AAFXNTkde8LbIzYO66Fajgxpde_DxDihops"
API_ID = 32541562
API_HASH = "e37e4432298d5a5eb4a6e32c18804283"
ADMINS = [2021145517] 

WELCOME_IMAGE = "https://i.ibb.co/Y49BGZbp/20260823-215817.jpg"
TMDB_BASE_URL = "https://tmdbapi.the-zake.workers.dev/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"

# Stateless In-Memory Cache for OTT Navigation
OTT_CACHE = {} 

app = Client("PremiumPosterBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# ==========================================
# 🛡 STRICT MIDDLEWARES & AUTHENTICATION
# ==========================================
async def check_access(client: Client, message: Message, is_poster_cmd=False):
    user_id = message.from_user.id if message.from_user else None
    
    # PM BLOCKER
    if message.chat.type == ChatType.PRIVATE:
        if is_poster_cmd and user_id not in ADMINS:
            await message.reply_text("⚠️ **Group Exclusive Feature**\n\nPoster extraction commands are restricted in private messages. Please use this bot in an authorized group.", quote=True)
            return False
        return True 
        
    # GROUP AUTHORIZATION & FSUB
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        settings = await db.get_settings()
        auth_groups = settings.get("auth_groups", [])
        
        if len(auth_groups) > 0 and message.chat.id not in auth_groups:
            await message.reply_text("⚠️ **Access Denied!**\n\nThis group is not authorized to utilize this bot. Leaving group...")
            await message.chat.leave()
            return False
            
        fsub_id = settings.get("fsub_id")
        fsub_link = settings.get("fsub_link")
        if fsub_id and fsub_link and user_id and user_id not in ADMINS:
            try:
                await client.get_chat_member(fsub_id, user_id)
            except UserNotParticipant:
                btn = [[InlineKeyboardButton("📢 Join Official Channel", url=fsub_link)]]
                await message.reply_text(f"Hello {message.from_user.mention},\n\nYou must join our official channel to process requests in this group.", reply_markup=InlineKeyboardMarkup(btn))
                return False
            except Exception:
                pass 
        return True
    return False

def verify_user(callback_query: CallbackQuery, uid: str):
    clicker_id = callback_query.from_user.id
    if clicker_id != int(uid) and clicker_id not in ADMINS:
        return False
    return True

# ==========================================
# 👑 ADMIN COMMANDS
# ==========================================
@app.on_message(filters.command("auth") & filters.user(ADMINS) & filters.group)
async def auth_group(client, message):
    await db.add_auth_group(message.chat.id)
    await message.reply_text("✅ **Group Authorized Successfully!**")

@app.on_message(filters.command("admin") & filters.user(ADMINS))
async def admin_dashboard(client: Client, message: Message):
    settings = await db.get_settings()
    text = (
        "👑 **Administrator Dashboard** 👑\n\n"
        f"👥 **Total Registered Users:** {await db.total_users()}\n"
        f"🛡 **Authorized Groups:** {len(settings.get('auth_groups', []))}\n\n"
        "**Available Commands:**\n"
        "`/setfsub <channel_id> <invite_link>` - Enforce channel subscription\n"
        "`/auth` - Authorize the current group"
    )
    await message.reply_text(text)

@app.on_message(filters.command("setfsub") & filters.user(ADMINS))
async def set_fsub(client, message):
    try:
        _, ch_id, link = message.text.split(" ", 2)
        await db.update_setting("fsub_id", int(ch_id))
        await db.update_setting("fsub_link", link)
        await message.reply_text("✅ **Force Subscribe Configuration Updated!**")
    except: 
        await message.reply_text("❌ **Invalid Format:** `/setfsub -100xxx https://t.me/...`")

# ==========================================
# 🎬 CENTRAL OTT COMMAND HANDLER
# ==========================================
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    if not await check_access(client, message, is_poster_cmd=False): return
    await db.add_user(message.from_user.id if message.from_user else 0)
    
    text = (
        "🎬 **Welcome to the Premium Poster Extractor!** 🎬\n\n"
        "Extract high-resolution, uncompressed posters, screenshots, and transparent logos directly from TMDB and major OTT platforms.\n\n"
        "_Use the menu below to explore my features and commands._"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("ℹ️ About Extractor", callback_data="about_bot"), InlineKeyboardButton("❓ Help & Commands", callback_data="help_bot")]
    ])
    await message.reply_photo(photo=WELCOME_IMAGE, caption=text, reply_markup=buttons)

@app.on_message(filters.command(OTT_PLATFORMS))
async def dynamic_ott_cmd(client: Client, message: Message):
    if not await check_access(client, message, is_poster_cmd=True): return
    cmd = message.command[0].lower()
    if len(message.command) < 2: 
        return await message.reply_text(f"⚠️ **Missing URL.** Example: `/{cmd} <url>`", quote=True)
    
    url = message.text.split(" ", 1)[1].strip()
    msg = await message.reply_text(f"🔄 Processing **{cmd.upper()}** payload via API... ⏳", quote=True)
    
    data = scrape_ott(cmd, url)
    
    if data and isinstance(data, dict):
        uid = str(message.from_user.id if message.from_user else 0)
        cache_id = str(msg.id)
        
        # Save to stateless dictionary mapping
        data['platform'] = cmd
        OTT_CACHE[cache_id] = data
        
        init_img = data.get("landscape") or data.get("portrait") or data.get("cover")
        if not init_img:
            return await msg.edit_text("⚠️ **Extraction Failed.** Valid images were not provided by the API.")
            
        buttons = []
        if data.get("landscape"): buttons.append([InlineKeyboardButton("🌄 Landscape", callback_data=f"ottcb_landscape_{cache_id}_{uid}")])
        if data.get("portrait"): buttons.append([InlineKeyboardButton("🖼 Portrait", callback_data=f"ottcb_portrait_{cache_id}_{uid}")])
        if data.get("cover"): buttons.append([InlineKeyboardButton("📚 Cover", callback_data=f"ottcb_cover_{cache_id}_{uid}")])
        buttons.append([InlineKeyboardButton("❌ Close Menu", callback_data=f"close_{uid}")])
        
        caption = (
            f"🎬 **Title:** **{data.get('title', 'Unknown Title')}**\n"
            f"🌐 **Platform:** {cmd.upper()}\n\n"
            f"_Please select an image format below:_"
        )
        
        await message.reply_photo(photo=init_img, caption=caption, reply_markup=InlineKeyboardMarkup(buttons), reply_to_message_id=message.id)
        await msg.delete()
    else: 
        await msg.edit_text("⚠️ **Extraction Failed.** The link might be invalid, or the API encountered an error.")

# ==========================================
# 🖥 OTT MENU CALLBACKS (VIEW & DOWNLOAD)
# ==========================================
@app.on_callback_query(filters.regex(r"^ottcb_"))
async def ott_view_image(client: Client, callback_query: CallbackQuery):
    _, img_format, cache_id, uid = callback_query.data.split("_")
    
    if not verify_user(callback_query, uid):
        return await callback_query.answer("⚠️ This menu belongs to someone else.", show_alert=True)
        
    data = OTT_CACHE.get(cache_id)
    if not data:
        return await callback_query.answer("⚠️ Session Expired! Please request again.", show_alert=True)
    
    img_url = data.get(img_format)
    caption = (
        f"🎬 **Title:** **{data.get('title', 'Unknown')}**\n"
        f"📐 **Format:** {img_format.capitalize()}\n\n"
        f"🔗 **Raw Image:** [Direct Link]({img_url})"
    )
    
    buttons = [
        [InlineKeyboardButton("⬇️ Download as File", callback_data=f"ottdl_{img_format}_{cache_id}_{uid}")],
        [InlineKeyboardButton("🔙 Go Back", callback_data=f"ottback_{cache_id}_{uid}")],
        [InlineKeyboardButton("❌ Close", callback_data=f"close_{uid}")]
    ]
    
    try:
        await callback_query.edit_message_media(media=InputMediaPhoto(media=img_url, caption=caption), reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await callback_query.answer("⚠️ Network error while rendering image.", show_alert=True)

@app.on_callback_query(filters.regex(r"^ottback_"))
async def ott_go_back(client: Client, callback_query: CallbackQuery):
    _, cache_id, uid = callback_query.data.split("_")
    
    if not verify_user(callback_query, uid):
        return await callback_query.answer("⚠️ Access Denied.", show_alert=True)
        
    data = OTT_CACHE.get(cache_id)
    if not data:
        return await callback_query.answer("⚠️ Session Expired!", show_alert=True)
        
    init_img = data.get("landscape") or data.get("portrait") or data.get("cover")
    
    buttons = []
    if data.get("landscape"): buttons.append([InlineKeyboardButton("🌄 Landscape", callback_data=f"ottcb_landscape_{cache_id}_{uid}")])
    if data.get("portrait"): buttons.append([InlineKeyboardButton("🖼 Portrait", callback_data=f"ottcb_portrait_{cache_id}_{uid}")])
    if data.get("cover"): buttons.append([InlineKeyboardButton("📚 Cover", callback_data=f"ottcb_cover_{cache_id}_{uid}")])
    buttons.append([InlineKeyboardButton("❌ Close Menu", callback_data=f"close_{uid}")])
    
    caption = f"🎬 **Title:** **{data.get('title', 'Unknown')}**\n🌐 **Platform:** {data.get('platform', '').upper()}\n\n_Please select an image format below:_"
    
    try:
        await callback_query.edit_message_media(media=InputMediaPhoto(media=init_img, caption=caption), reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass

@app.on_callback_query(filters.regex(r"^ottdl_"))
async def ott_download_file(client: Client, callback_query: CallbackQuery):
    _, img_format, cache_id, uid = callback_query.data.split("_")
    
    if not verify_user(callback_query, uid):
        return await callback_query.answer("⚠️ Access Denied.", show_alert=True)
        
    data = OTT_CACHE.get(cache_id)
    if not data:
        return await callback_query.answer("⚠️ Session Expired!", show_alert=True)
        
    img_url = data.get(img_format)
    await callback_query.answer("⏳ Downloading file securely... Please wait.", show_alert=False)
    
    try:
        response = requests.get(img_url, timeout=10)
        if response.status_code == 200:
            file_stream = io.BytesIO(response.content)
            file_stream.name = f"{data.get('title', 'Poster').replace(' ', '_')}_{img_format}.jpg"
            
            await client.send_document(
                chat_id=callback_query.message.chat.id,
                document=file_stream,
                caption=f"📁 **{img_format.capitalize()} High-Res Image**\n🎬 **Title:** {data.get('title')}",
                reply_to_message_id=callback_query.message.id
            )
        else:
            await callback_query.message.reply_text("❌ Failed to fetch the image from the server.")
    except Exception as e:
        await callback_query.message.reply_text(f"❌ Network Error: {str(e)}")

# ==========================================
# 🔍 TMDB SEARCH SYSTEM
# ==========================================
@app.on_message(filters.command("p"))
async def search_media(client: Client, message: Message):
    if not await check_access(client, message, is_poster_cmd=True): return
    if len(message.command) < 2: 
        return await message.reply_text("⚠️ **Missing Query.** Example: `/p Inception` or `/p Dark 2017`", reply_to_message_id=message.id)
    
    uid = message.from_user.id if message.from_user else 0
    raw_query = message.text.split(" ", 1)[1].strip()
    parts = raw_query.split()
    year = parts[-1] if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 4 else ""
    query = " ".join(parts[:-1]) if year else raw_query
    
    msg = await message.reply_text(f"🔍 Searching database for '{raw_query}'...", reply_to_message_id=message.id)
    
    if year:
        m_res = requests.get(f"{TMDB_BASE_URL}/search/movie", params={"query": query, "primary_release_year": year}).json()
        t_res = requests.get(f"{TMDB_BASE_URL}/search/tv", params={"query": query, "first_air_date_year": year}).json()
        results = m_res.get("results", []) + t_res.get("results", [])
    else:
        res = requests.get(f"{TMDB_BASE_URL}/search/multi", params={"query": query}).json()
        results = [r for r in res.get("results", []) if r.get("media_type") in ["movie", "tv"]]
    
    if not results: 
        return await msg.edit_text("❌ No relevant Movies or Web Series found.")

    buttons = []
    for item in results[:6]:
        title = item.get('title') or item.get('name', 'Unknown')
        r_year = (item.get('release_date') or item.get('first_air_date', ''))[:4] or "N/A"
        m_type = item.get('media_type') or ("movie" if "title" in item else "tv")
        
        icon = "🎬" if m_type == "movie" else "📺"
        short_type = "m" if m_type == "movie" else "t"
        buttons.append([InlineKeyboardButton(f"{icon} {title} ({r_year})", callback_data=f"opt_{short_type}_{item.get('id')}_{uid}")])
    
    buttons.append([InlineKeyboardButton("❌ Close Menu", callback_data=f"close_{uid}")])
    await msg.edit_text(f"🔍 **Search Query:** `{raw_query}`\n\n✨ **Select the correct media:**", reply_markup=InlineKeyboardMarkup(buttons))

# ==========================================
# 📱 TMDB DYNAMIC MENUS
# ==========================================
@app.on_callback_query(filters.regex(r"^opt_"))
async def tmdb_main_options(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    s_type, m_id, uid = data[1], data[2], data[3]
    
    if not verify_user(callback_query, uid):
        return await callback_query.answer("⚠️ This menu belongs to someone else. Please run your own search.", show_alert=True)
        
    type_label = "Movie" if s_type == "m" else "Web Series"
    
    buttons = [
        [InlineKeyboardButton("🌄 Landscape (Horizontal)", callback_data=f"sub_b_{s_type}_{m_id}_{uid}")],
        [InlineKeyboardButton("🖼 Portrait (Vertical)", callback_data=f"sub_p_{s_type}_{m_id}_{uid}")],
        [InlineKeyboardButton("🅰 Transparent Logos", callback_data=f"img_l_all_{s_type}_{m_id}_0_{uid}")],
        [InlineKeyboardButton("❌ Close", callback_data=f"close_{uid}")]
    ]
    await callback_query.message.edit_text(f"✨ **{type_label} Selected!**\n\nPlease choose an aspect ratio format:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^sub_"))
async def tmdb_sub_options(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    cat, s_type, m_id, uid = data[1], data[2], data[3], data[4]
    
    if not verify_user(callback_query, uid):
        return await callback_query.answer("⚠️ Access Denied. Initiate your own request.", show_alert=True)
        
    cat_label = "Landscape" if cat == "b" else "Portrait"
    
    buttons = [
        [InlineKeyboardButton("📝 Posters (Contains Text/Title)", callback_data=f"img_{cat}_txt_{s_type}_{m_id}_0_{uid}")],
        [InlineKeyboardButton("🖼 Screenshots (Clean Background)", callback_data=f"img_{cat}_cln_{s_type}_{m_id}_0_{uid}")],
        [InlineKeyboardButton("🔙 Go Back", callback_data=f"opt_{s_type}_{m_id}_{uid}")]
    ]
    await callback_query.message.edit_text(f"**{cat_label} Formatting Options:**\n\nDo you want the official Boxart (with text) or a clean screenshot?", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^img_"))
async def tmdb_paginate_images(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    cat, flt, s_type, m_id, index, uid = data[1], data[2], data[3], data[4], int(data[5]), data[6]
    
    if not verify_user(callback_query, uid):
        return await callback_query.answer("⚠️ Access Denied.", show_alert=True)
        
    m_type = "movie" if s_type == "m" else "tv"
    movie_info = requests.get(f"{TMDB_BASE_URL}/{m_type}/{m_id}").json()
    name = movie_info.get("title") or movie_info.get("name", "Unknown")
    res = requests.get(f"{TMDB_BASE_URL}/{m_type}/{m_id}/images").json()
    
    cat_key = "backdrops" if cat == "b" else "posters" if cat == "p" else "logos"
    raw_images = res.get(cat_key, [])
    
    if flt == "txt": images_list = [img for img in raw_images if img.get('iso_639_1') not in [None, "xx"]]
    elif flt == "cln": images_list = [img for img in raw_images if img.get('iso_639_1') in [None, "xx"]]
    else: images_list = raw_images
        
    if not images_list: 
        return await callback_query.answer("❌ No images found under this specific filter!", show_alert=True)
        
    index = max(0, min(index, len(images_list) - 1))
    img_data = images_list[index]
    full_image_url = f"{TMDB_IMAGE_BASE}{img_data['file_path']}"
    lang_display = img_data.get('iso_639_1').upper() if img_data.get('iso_639_1') not in [None, 'xx'] else "N/A (Clean/Textless)"
    cat_display = "Landscape" if cat == "b" else "Portrait" if cat == "p" else "Transparent Logo"
    
    caption_text = (
        f"🔍 **Subject:** {name}\n\n"
        f"• **Format:** {cat_display}\n"
        f"• **Language Tag:** {lang_display}\n"
        f"• **Resolution:** {img_data.get('width')}x{img_data.get('height')}\n"
        f"• **Raw Image:** [Direct Download (JPG)]({full_image_url})"
    )
    cb_prefix = f"img_{cat}_{flt}_{s_type}_{m_id}"

    nav_buttons = []
    nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{cb_prefix}_{index-1}_{uid}") if index > 0 else InlineKeyboardButton("⛔", callback_data="ignore"))
    nav_buttons.append(InlineKeyboardButton(f"Page {index + 1} of {len(images_list)}", callback_data="ignore"))
    nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{cb_prefix}_{index+1}_{uid}") if index < len(images_list) - 1 else InlineKeyboardButton("⛔", callback_data="ignore"))
    
    back_data = f"opt_{s_type}_{m_id}_{uid}" if cat == "l" else f"sub_{cat}_{s_type}_{m_id}_{uid}"
    markup = InlineKeyboardMarkup([
        nav_buttons, 
        [InlineKeyboardButton("🔙 Go Back", callback_data=back_data)], 
        [InlineKeyboardButton("❌ Close", callback_data=f"close_{uid}")]
    ])
    
    try:
        if not callback_query.message.photo:
            await callback_query.message.delete()
            await client.send_photo(chat_id=callback_query.message.chat.id, photo=full_image_url, caption=caption_text, reply_markup=markup)
        else:
            await client.edit_message_media(chat_id=callback_query.message.chat.id, message_id=callback_query.message.id, media=InputMediaPhoto(media=full_image_url, caption=caption_text), reply_markup=markup)
    except: 
        await callback_query.answer("⚠️ Network error while loading the image.", show_alert=True)

# ==========================================
# 🛑 UTILITY (CLOSE, IGNORE) & INFO MENUS
# ==========================================
@app.on_callback_query(filters.regex(r"^close_"))
async def close_menu(client, callback_query):
    uid = callback_query.data.split("_")[1]
    if verify_user(callback_query, uid): 
        await callback_query.message.delete()
    else:
        await callback_query.answer("⚠️ You cannot close someone else's menu.", show_alert=True)

@app.on_callback_query(filters.regex("ignore"))
async def ignore_btn(client, callback_query): 
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^(about_bot|help_bot|home_bot)$"))
async def home_menus(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    
    if data == "about_bot":
        text = (
            "ℹ️ **About the Premium Extractor**\n\n"
            "This bot is a highly advanced utility designed for channel administrators, editors, and content creators.\n\n"
            "**Key Features:**\n"
            "• Extracts 4K & UHD Backgrounds (Clean/Textless).\n"
            "• Extracts Official Boxart & Posters (With Text/Titles).\n"
            "• Extracts Transparent Logos.\n"
            "• API integration covering 40+ global OTT platforms.\n\n"
            "_The system accesses hidden backend APIs to provide raw image files instantly without compression._"
        )
        buttons = [[InlineKeyboardButton("🔙 Go Back", callback_data="home_bot")]]
        
    elif data == "help_bot":
        from commands import get_help_text
        text = get_help_text()
        buttons = [[InlineKeyboardButton("🔙 Go Back", callback_data="home_bot")]]
        
    elif data == "home_bot":
        text = (
            "🎬 **Welcome to the Premium Poster Extractor!** 🎬\n\n"
            "Extract high-resolution, uncompressed posters, screenshots, and transparent logos directly from TMDB and major OTT platforms.\n\n"
            "_Use the menu below to explore my features and commands._"
        )
        buttons = [
            [InlineKeyboardButton("ℹ️ About Extractor", callback_data="about_bot"), InlineKeyboardButton("❓ Help & Commands", callback_data="help_bot")]
        ]
        
    try:
        await callback_query.message.edit_caption(caption=text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await callback_query.answer(f"UI Error: {str(e)}", show_alert=True)

if __name__ == "__main__":
    app.run()
