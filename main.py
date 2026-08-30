import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import glob
import importlib
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.enums import ChatType
from pyrogram.errors import UserNotParticipant
from db import db

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

app = Client("PremiumPosterBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# ==========================================
# 🔌 DYNAMIC OTT MODULE LOADER
# ==========================================
ott_modules = {}
if not os.path.exists("ott"): os.makedirs("ott")
with open("ott/__init__.py", "a") as f: pass

for file_path in glob.glob("ott/*.py"):
    module_name = os.path.basename(file_path)[:-3]
    if module_name != "__init__":
        try:
            ott_modules[module_name] = importlib.import_module(f"ott.{module_name}")
            print(f"✅ Loaded OTT Module: /{module_name}")
        except Exception as e: 
            print(f"❌ Failed to load {module_name}: {e}")

# ==========================================
# 🛡 STRICT MIDDLEWARES & AUTHENTICATION
# ==========================================
async def check_access(client: Client, message: Message, is_poster_cmd=False):
    user_id = message.from_user.id if message.from_user else None
    
    # 1. PM BLOCKER (Allows /start, blocks extractors)
    if message.chat.type == ChatType.PRIVATE:
        if is_poster_cmd and user_id not in ADMINS:
            await message.reply_text("⚠️ **Group Exclusive Feature**\n\nPoster extraction commands are restricted in private messages to prevent server overload. Please use this bot in an authorized group.", quote=True)
            return False
        return True 
        
    # 2. GROUP AUTHORIZATION & FSUB
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        settings = await db.get_settings()
        auth_groups = settings.get("auth_groups", [])
        
        if len(auth_groups) > 0 and message.chat.id not in auth_groups:
            await message.reply_text("⚠️ **Access Denied!**\n\nThis group is not authorized to utilize this bot. Contact the administrator. Leaving group...")
            await message.chat.leave()
            return False
            
        # Group Level Force Subscribe Check
        fsub_id = settings.get("fsub_id")
        fsub_link = settings.get("fsub_link")
        if fsub_id and fsub_link and user_id and user_id not in ADMINS:
            try:
                await client.get_chat_member(fsub_id, user_id)
            except UserNotParticipant:
                btn = [[InlineKeyboardButton("📢 Join Official Channel", url=fsub_link)]]
                await message.reply_text(
                    f"Hello {message.from_user.mention},\n\nYou must join our official channel to process requests in this group.",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return False
            except Exception:
                pass 
        return True
    return False

def verify_user(callback_query: CallbackQuery, uid: str):
    """Stateless verification: Checks if the user clicking matches the ID stored in the button"""
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
# 🎬 MAIN BOT & DYNAMIC OTT COMMANDS
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

valid_commands = list(ott_modules.keys())
if valid_commands:
    @app.on_message(filters.command(valid_commands))
    async def dynamic_ott_cmd(client: Client, message: Message):
        if not await check_access(client, message, is_poster_cmd=True): return
        cmd = message.command[0].lower()
        if len(message.command) < 2: 
            return await message.reply_text(f"⚠️ **Missing URL.** Example: `/{cmd} <url>`", reply_to_message_id=message.id)
        
        url = message.text.split(" ", 1)[1].strip()
        msg = await message.reply_text(f"🔄 Processing **{cmd.upper()}** payload... ⏳", reply_to_message_id=message.id)
        
        try:
            data = ott_modules[cmd].scrape(url) if hasattr(ott_modules[cmd], "scrape") else None
            if data:
                user_mention = message.from_user.mention if message.from_user else "Anonymous"
                caption = (
                    f"👤 **Requested By:** {user_mention}\n"
                    f"🔗 **Source Query:** `/{cmd} {url}`\n\n"
                    f"🖼 **Main {cmd.upper()} Poster:**\n{data['main_poster']}\n\n"
                    f"📱 **Portrait View:** [Direct Link]({data['portrait']})\n\n"
                    f"🌄 **Cover/Landscape:** [Direct Link]({data['cover']})\n\n"
                    f"🎬 **Title:** **{data['title']}**"
                )
                await message.reply_photo(photo=data['main_poster'], caption=caption, reply_to_message_id=message.id)
                await msg.delete()
            else: 
                await msg.edit_text("⚠️ **Extraction Failed.** The link might be invalid, or the platform's DRM blocked the request.")
        except Exception as e: 
            await msg.edit_text(f"⚠️ **Runtime Error:** {str(e)}")

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
# 📱 DYNAMIC MENUS (SMART FILTERS)
# ==========================================
@app.on_callback_query(filters.regex(r"^opt_"))
async def show_main_options(client: Client, callback_query: CallbackQuery):
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
async def show_sub_options(client: Client, callback_query: CallbackQuery):
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
async def paginate_images(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    cat, flt, s_type, m_id, index, uid = data[1], data[2], data[3], data[4], int(data[5]), data[6]
    
    if not verify_user(callback_query, uid):
        return await callback_query.answer("⚠️ Access Denied. Initiate your own request.", show_alert=True)
        
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

@app.on_callback_query(filters.regex(r"^(about_bot|help_bot)$"))
async def home_menus(client: Client, callback_query: CallbackQuery):
    if callback_query.data == "about_bot":
        text = (
            "ℹ️ **About the Premium Extractor**\n\n"
            "This bot is a highly advanced utility designed for channel administrators, editors, and content creators.\n\n"
            "**Key Features:**\n"
            "• Extracts 4K & UHD Backgrounds (Clean/Textless).\n"
            "• Extracts Official Boxart & Posters (With Text/Titles).\n"
            "• Extracts Transparent Logos.\n"
            "• Direct DRM bypass integration for major OTT platforms (Netflix, Prime Video, etc.).\n\n"
            "_The system accesses hidden backend APIs to provide raw image files instantly without compression._"
        )
    else:
        text = (
            "❓ **How to Use the Bot**\n\n"
            "**1. General Search (TMDB):**\n"
            "`/p <Movie or Series Name>`\n"
            "Example: `/p Inception` or `/p Dark 2017`\n"
            "_(Adding the release year filters out inaccurate results)._\n\n"
            "**2. OTT Specific Extraction:**\n"
            "`/nf <Netflix URL>` - Extracts Netflix Boxart, Portrait & Cover.\n"
            "`/prime <Prime URL>` - Extracts Amazon Prime Video high-res thumbnails.\n\n"
            "**Filtering System:**\n"
            "• **Landscape:** Horizontal 16:9 aspect ratio.\n"
            "• **Portrait:** Vertical 2:3 aspect ratio.\n"
            "• **Posters:** Official Boxart containing the movie title.\n"
            "• **Screenshots:** Pure textless backgrounds."
        )
    await callback_query.answer(text, show_alert=True)

if __name__ == "__main__":
    app.run()
