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
POWERED_BY = "@MrSagarBots"
UPDATE_CHANNEL_URL = "https://t.me/MrSagarBots"
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
        except Exception as e: print(f"❌ Failed to load {module_name}: {e}")

# ==========================================
# 🛡 STRICT MIDDLEWARES & AUTHENTICATION
# ==========================================
async def check_access(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else None
    
    # 1. PM BLOCKER (Strictly Group Only)
    if message.chat.type == ChatType.PRIVATE:
        if user_id not in ADMINS:
            await message.reply_text("⚠️ **Access Denied!**\nYe bot PM (Private Message) me allow nahi hai. Kripya ise authorized group me use karein.")
            return False
        return True # Admin can test in PM
        
    # 2. GROUP AUTHORIZATION & FSUB
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        settings = await db.get_settings()
        auth_groups = settings.get("auth_groups", [])
        
        if len(auth_groups) > 0 and message.chat.id not in auth_groups:
            await message.reply_text("⚠️ **Access Denied!**\nYe group Authorized nahi hai. Bot leaving...")
            await message.chat.leave()
            return False
            
        # Group Level Force Sub Check
        fsub_id = settings.get("fsub_id")
        fsub_link = settings.get("fsub_link")
        if fsub_id and fsub_link and user_id and user_id not in ADMINS:
            try:
                await client.get_chat_member(fsub_id, user_id)
            except UserNotParticipant:
                btn = [[InlineKeyboardButton("📢 Join Channel To Use Bot", url=fsub_link)]]
                await message.reply_text(
                    f"Hello {message.from_user.mention}, bot use karne ke liye pehle channel join karein.",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return False
            except Exception as e:
                pass # Accept Anonymous admins or cache errors
        return True
    return False

async def is_authorized(callback_query: CallbackQuery):
    """Ensure no one else can click the buttons (Fixed Anonymous Admins)"""
    if callback_query.message.reply_to_message:
        orig_msg = callback_query.message.reply_to_message
        requester_id = orig_msg.from_user.id if orig_msg.from_user else (orig_msg.sender_chat.id if orig_msg.sender_chat else None)
        
        if requester_id and callback_query.from_user.id != requester_id and callback_query.from_user.id not in ADMINS:
            await callback_query.answer("⚠️ This is not for you! Kisi aur ka search mat chhedo.", show_alert=True)
            return False
        return True
    else:
        await callback_query.answer("⚠️ Session Expired! Naya search karein.", show_alert=True)
        return False

# ==========================================
# 👑 ADMIN COMMANDS
# ==========================================
@app.on_message(filters.command("auth") & filters.user(ADMINS) & filters.group)
async def auth_group(client, message):
    await db.add_auth_group(message.chat.id)
    await message.reply_text("✅ Group Authorized!")

@app.on_message(filters.command("admin") & filters.user(ADMINS))
async def admin_dashboard(client: Client, message: Message):
    settings = await db.get_settings()
    text = (
        "👑 **Admin Dashboard** 👑\n\n"
        f"👥 **Total Users:** {await db.total_users()}\n"
        f"🛡 **Auth Groups Count:** {len(settings.get('auth_groups', []))}\n\n"
        "**Commands:**\n`/setfsub <id> <link>`\n`/auth` - Authorize Group"
    )
    await message.reply_text(text)

@app.on_message(filters.command("setfsub") & filters.user(ADMINS))
async def set_fsub(client, message):
    try:
        _, ch_id, link = message.text.split(" ", 2)
        await db.update_setting("fsub_id", int(ch_id))
        await db.update_setting("fsub_link", link)
        await message.reply_text("✅ FSub Set!")
    except: await message.reply_text("❌ Format: `/setfsub -100xxx https://t.me/...`")

# ==========================================
# 🎬 MAIN BOT & DYNAMIC OTT COMMANDS
# ==========================================
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    if not await check_access(client, message): return
    await db.add_user(message.from_user.id if message.from_user else 0)
    
    text = "🔥 **Welcome to Premium Poster Extractor!** 🔥\n\nHigh-Quality Posters, Clean Screenshots, and Logos."
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("ℹ️ About Bot", callback_data="about_bot"), InlineKeyboardButton("❓ Help", callback_data="help_bot")]])
    await message.reply_photo(photo=WELCOME_IMAGE, caption=text, reply_markup=buttons)

valid_commands = list(ott_modules.keys())
if valid_commands:
    @app.on_message(filters.command(valid_commands))
    async def dynamic_ott_cmd(client: Client, message: Message):
        if not await check_access(client, message): return
        cmd = message.command[0].lower()
        if len(message.command) < 2: return await message.reply_text(f"⚠️ URL dein. Example: `/{cmd} <url>`", reply_to_message_id=message.id)
        
        url = message.text.split(" ", 1)[1].strip()
        msg = await message.reply_text(f"🔄 **{cmd.upper()}** link scrape kar raha hoon... ⏳", reply_to_message_id=message.id)
        
        try:
            data = ott_modules[cmd].scrape(url) if hasattr(ott_modules[cmd], "scrape") else None
            if data:
                user_mention = message.from_user.mention if message.from_user else "Admin"
                caption = (
                    f"{user_mention}\n`/{cmd} {url}`\n\n**{cmd.upper()} Poster:**\n{data['main_poster']}\n\n"
                    f"**Portrait:** [Click Here]({data['portrait']})\n\n**Cover:** [Click Here]({data['cover']})\n\n**{data['title']}**"
                )
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Update Channel", url=UPDATE_CHANNEL_URL)]])
                await message.reply_photo(photo=data['main_poster'], caption=caption, reply_markup=btn, reply_to_message_id=message.id)
                await msg.delete()
            else: await msg.edit_text("⚠️ Image nahi mili. Link invalid hai ya DRM blocked hai.")
        except Exception as e: await msg.edit_text(f"⚠️ Error: {str(e)}")

# ==========================================
# 🔍 TMDB SEARCH SYSTEM
# ==========================================
@app.on_message(filters.command("p"))
async def search_media(client: Client, message: Message):
    if not await check_access(client, message): return
    if len(message.command) < 2: return await message.reply_text("Example: `/p War 2019`", reply_to_message_id=message.id)
    
    raw_query = message.text.split(" ", 1)[1].strip()
    parts = raw_query.split()
    year = parts[-1] if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 4 else ""
    query = " ".join(parts[:-1]) if year else raw_query
    
    msg = await message.reply_text(f"🔍 Searching for '{raw_query}'...", reply_to_message_id=message.id)
    
    if year:
        m_res = requests.get(f"{TMDB_BASE_URL}/search/movie", params={"query": query, "primary_release_year": year}).json()
        t_res = requests.get(f"{TMDB_BASE_URL}/search/tv", params={"query": query, "first_air_date_year": year}).json()
        results = m_res.get("results", []) + t_res.get("results", [])
    else:
        res = requests.get(f"{TMDB_BASE_URL}/search/multi", params={"query": query}).json()
        results = [r for r in res.get("results", []) if r.get("media_type") in ["movie", "tv"]]
    
    if not results: return await msg.edit_text("Sorry, aisi koi Movie/Series nahi mili.")

    buttons = []
    for item in results[:6]:
        title = item.get('title') or item.get('name', 'Unknown')
        r_year = (item.get('release_date') or item.get('first_air_date', ''))[:4] or "N/A"
        m_type = item.get('media_type') or ("movie" if "title" in item else "tv")
        
        icon = "🎬" if m_type == "movie" else "📺"
        short_type = "m" if m_type == "movie" else "t"
        buttons.append([InlineKeyboardButton(f"{icon} {title} ({r_year})", callback_data=f"opt_{short_type}_{item.get('id')}")])
    
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_menu")])
    await msg.edit_text(f"🔍 Search: **{raw_query}**\n\n✨ **Select Media:**", reply_markup=InlineKeyboardMarkup(buttons))

# ==========================================
# 📱 DYNAMIC MENUS (SMART FILTERS)
# ==========================================
@app.on_callback_query(filters.regex(r"^opt_"))
async def show_main_options(client: Client, callback_query: CallbackQuery):
    if not await is_authorized(callback_query): return
    s_type, m_id = callback_query.data.split("_")[1:3]
    
    buttons = [
        [InlineKeyboardButton("🌄 Landscape (Horizontal)", callback_data=f"sub_b_{s_type}_{m_id}")],
        [InlineKeyboardButton("🖼 Portrait (Vertical)", callback_data=f"sub_p_{s_type}_{m_id}")],
        [InlineKeyboardButton("🅰 Logos", callback_data=f"img_l_all_{s_type}_{m_id}_0")],
        [InlineKeyboardButton("❌ Close", callback_data="close_menu")]
    ]
    await callback_query.message.edit_text(f"✨ **Selected!**\nChoose aspect ratio:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^sub_"))
async def show_sub_options(client: Client, callback_query: CallbackQuery):
    if not await is_authorized(callback_query): return
    cat, s_type, m_id = callback_query.data.split("_")[1:4]
    
    buttons = [
        [InlineKeyboardButton("📝 Posters (With Text)", callback_data=f"img_{cat}_txt_{s_type}_{m_id}_0")],
        [InlineKeyboardButton("🖼 Screenshots (Clean)", callback_data=f"img_{cat}_cln_{s_type}_{m_id}_0")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"opt_{s_type}_{m_id}")]
    ]
    await callback_query.message.edit_text(f"**Options:**\nText wali image chahiye ya clean background?", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^img_"))
async def paginate_images(client: Client, callback_query: CallbackQuery):
    if not await is_authorized(callback_query): return
    data = callback_query.data.split("_")
    cat, flt, s_type, m_id, index = data[1], data[2], data[3], data[4], int(data[5])
    m_type = "movie" if s_type == "m" else "tv"
    
    movie_info = requests.get(f"{TMDB_BASE_URL}/{m_type}/{m_id}").json()
    name = movie_info.get("title") or movie_info.get("name", "Unknown")
    res = requests.get(f"{TMDB_BASE_URL}/{m_type}/{m_id}/images").json()
    
    cat_key = "backdrops" if cat == "b" else "posters" if cat == "p" else "logos"
    raw_images = res.get(cat_key, [])
    
    if flt == "txt": images_list = [img for img in raw_images if img.get('iso_639_1') not in [None, "xx"]]
    elif flt == "cln": images_list = [img for img in raw_images if img.get('iso_639_1') in [None, "xx"]]
    else: images_list = raw_images
        
    if not images_list: return await callback_query.answer("❌ Is criteria me koi image nahi mili!", show_alert=True)
        
    index = max(0, min(index, len(images_list) - 1))
    img_data = images_list[index]
    full_image_url = f"{TMDB_IMAGE_BASE}{img_data['file_path']}"
    lang_display = img_data.get('iso_639_1') if img_data.get('iso_639_1') not in [None, 'xx'] else "N/A (Clean)"
    cat_display = "Landscape" if cat == "b" else "Portrait" if cat == "p" else "Logo"
    
    caption_text = (
        f"🔍 **Search:** {name}\n\n• **Category:** {cat_display}\n• **Language:** {lang_display}\n"
        f"• **Size:** {img_data.get('width')}x{img_data.get('height')}\n• **Image:** [Link (JPG)]({full_image_url})\n\n🚀 **Powered By** {POWERED_BY}"
    )
    cb_prefix = f"img_{cat}_{flt}_{s_type}_{m_id}"

    nav_buttons = []
    nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{cb_prefix}_{index-1}") if index > 0 else InlineKeyboardButton("⛔", callback_data="ignore"))
    nav_buttons.append(InlineKeyboardButton(f"{index + 1}/{len(images_list)}", callback_data="ignore"))
    nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{cb_prefix}_{index+1}") if index < len(images_list) - 1 else InlineKeyboardButton("⛔", callback_data="ignore"))
    
    back_data = f"opt_{s_type}_{m_id}" if cat == "l" else f"sub_{cat}_{s_type}_{m_id}"
    markup = InlineKeyboardMarkup([nav_buttons, [InlineKeyboardButton("🔙 Back", callback_data=back_data)], [InlineKeyboardButton("❌ Close", callback_data="close_menu")]])
    
    try:
        if not callback_query.message.photo:
            await callback_query.message.delete()
            await client.send_photo(chat_id=callback_query.message.chat.id, photo=full_image_url, caption=caption_text, reply_markup=markup)
        else:
            await client.edit_message_media(chat_id=callback_query.message.chat.id, message_id=callback_query.message.id, media=InputMediaPhoto(media=full_image_url, caption=caption_text), reply_markup=markup)
    except: await callback_query.answer("Error loading image!", show_alert=True)

@app.on_callback_query(filters.regex("close_menu"))
async def close_menu(client, callback_query):
    if await is_authorized(callback_query): await callback_query.message.delete()

@app.on_callback_query(filters.regex("ignore"))
async def ignore_btn(client, callback_query): await callback_query.answer()

@app.on_callback_query(filters.regex(r"^(about_bot|help_bot)$"))
async def home_menus(client: Client, callback_query: CallbackQuery):
    text = "ℹ️ **About Bot**\nHigh-Quality Backgrounds aur Posters nikalne ke liye." if callback_query.data == "about_bot" else "❓ **Help & Commands**\n`/p <name>` - Search\n`/nf <url>` - Netflix"
    await callback_query.answer(text, show_alert=True)

if __name__ == "__main__":
    app.run()
