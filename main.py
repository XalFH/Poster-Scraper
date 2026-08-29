import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.errors import UserNotParticipant
from pyrogram.enums import ChatType
from db import db
from ott.nf import get_netflix_data

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8603433381:AAFXNTkde8LbIzYO66Fajgxpde_DxDihops"
API_ID = 32541562
API_HASH = "e37e4432298d5a5eb4a6e32c18804283"
ADMINS = [7006602588] 
POWERED_BY = "@MrSagarBots"
UPDATE_CHANNEL_URL = "https://t.me/MrSagarBots"
WELCOME_IMAGE = "https://i.ibb.co/Y49BGZbp/20260823-215817.jpg"

TMDB_BASE_URL = "https://tmdbapi.the-zake.workers.dev/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"

app = Client("PremiumPosterBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# ==========================================
# 🛡 MIDDLEWARES (STRICT FSUB & AUTH)
# ==========================================
async def check_access(client: Client, message: Message):
    settings = await db.get_settings()
    
    # 1. STRICT Group Authorization Check
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        auth_groups = settings.get("auth_groups", [])
        # Agar admin ne koi bhi group auth kiya hai, toh unauthorized groups ko block kar do
        if len(auth_groups) > 0 and message.chat.id not in auth_groups:
            await message.reply_text("⚠️ **Access Denied!**\nYe bot yahan allowed nahi hai. Contact Admin.")
            await message.chat.leave()
            return False
        return True
        
    # 2. Private Chat FSub Check
    if message.chat.type == ChatType.PRIVATE:
        fsub_id = settings.get("fsub_id")
        fsub_link = settings.get("fsub_link")
        
        if fsub_id and fsub_link:
            try:
                await client.get_chat_member(fsub_id, message.from_user.id)
            except UserNotParticipant:
                btn = [[InlineKeyboardButton("📢 Join Channel To Use Bot", url=fsub_link)]]
                await message.reply_text(
                    "⚠️ **Access Denied!**\n\nBot use karne ke liye pehle hamara official channel join karein.",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return False
            except Exception as e:
                print(f"FSub Check Failed: {e}")
                
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
        "`/setfsub <channel_id> <link>` - Set FSub\n"
        "`/setlog <channel_id>` - Set Alert Channel\n"
        "`/auth` - Group me deke authorize karein\n"
        "`/broadcast` (Reply) - Sabko msg bhejein"
    )
    await message.reply_text(text)

@app.on_message(filters.command("setfsub") & filters.user(ADMINS))
async def set_fsub(client, message):
    try:
        _, ch_id, link = message.text.split(" ", 2)
        await db.update_setting("fsub_id", int(ch_id))
        await db.update_setting("fsub_link", link)
        await message.reply_text(f"✅ FSub Set Successfully!")
    except: await message.reply_text("❌ Format: `/setfsub -100xxx https://t.me/...`")

@app.on_message(filters.command("setlog") & filters.user(ADMINS))
async def set_log(client, message):
    try:
        await db.update_setting("log_channel", int(message.command[1]))
        await message.reply_text(f"✅ Log Channel Set!")
    except: await message.reply_text("❌ Format: `/setlog -100xxx`")

@app.on_message(filters.command("auth") & filters.user(ADMINS) & filters.group)
async def auth_group(client, message):
    await db.add_auth_group(message.chat.id)
    await message.reply_text("✅ Group Authorized! Bot ab yahan strictly kaam karega.")

@app.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast_msg(client, message):
    if not message.reply_to_message: return await message.reply_text("⚠️ Message par reply karein.")
    msg = await message.reply_text("🚀 Broadcasting...")
    users = await db.get_all_users()
    success, failed = 0, 0
    async for user in users:
        try:
            await message.reply_to_message.copy(user["_id"])
            success += 1
            await asyncio.sleep(0.1)
        except: failed += 1
    await msg.edit_text(f"✅ **Broadcast Complete!**\n🟢 Success: {success} | 🔴 Failed: {failed}")

# ==========================================
# 🎬 MAIN BOT COMMANDS (WITH WELCOME MENU)
# ==========================================
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    if not await check_access(client, message): return
    
    is_new = await db.add_user(message.from_user.id)
    if is_new:
        settings = await db.get_settings()
        log_id = settings.get("log_channel")
        if log_id:
            try: await client.send_message(log_id, f"🆕 **New User Alert!**\n👤 {message.from_user.mention} | 🆔 `{message.from_user.id}`")
            except: pass

    text = "🔥 **Welcome to Premium Poster Extractor!** 🔥\n\nHigh-Quality Posters, Clean Screenshots, and Logos from TMDB & OTT platforms."
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("ℹ️ About Bot", callback_data="about_bot"), InlineKeyboardButton("❓ Help", callback_data="help_bot")],
        [InlineKeyboardButton("📢 Updates Channel", url=UPDATE_CHANNEL_URL)]
    ])
    await message.reply_photo(photo=WELCOME_IMAGE, caption=text, reply_markup=buttons)

@app.on_callback_query(filters.regex(r"^(about_bot|help_bot|start_menu)$"))
async def home_menus(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    if data == "about_bot":
        text = "ℹ️ **About Bot**\n\nYe bot editors aur channel admins ke liye banaya gaya hai jisse aap TMDB aur OTT platforms se High-Quality Backgrounds (Clean Screenshots), Title Text wale Posters, aur Logos nikal sakte hain."
    elif data == "help_bot":
        text = "❓ **Help & Commands**\n\n🎬 `/p <name>` - Search Movies/Series (eg: `/p War 2019`)\n🟥 `/nf <url>` - Extract Netflix Thumbnail\n\n*(Naye OTT scrapers add hote hi unki commands yahan update ki jayengi!)*"
    else:
        text = "🔥 **Welcome to Premium Poster Extractor!** 🔥\n\nHigh-Quality Posters, Clean Screenshots, and Logos from TMDB & OTT platforms."
        
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Home", callback_data="start_menu")]]) if data != "start_menu" else InlineKeyboardMarkup([
        [InlineKeyboardButton("ℹ️ About Bot", callback_data="about_bot"), InlineKeyboardButton("❓ Help", callback_data="help_bot")],
        [InlineKeyboardButton("📢 Updates Channel", url=UPDATE_CHANNEL_URL)]
    ])
    await callback_query.message.edit_caption(caption=text, reply_markup=buttons)

# ==========================================
# 🔍 SEARCH SYSTEM (ADVANCED YEAR SUPPORT)
# ==========================================
@app.on_message(filters.command("p"))
async def search_media(client: Client, message: Message):
    if not await check_access(client, message): return
    if len(message.command) < 2: return await message.reply_text("Example: `/p War 2019`")
    
    raw_query = message.text.split(" ", 1)[1].strip()
    
    # Year Extraction Logic ("War 2019" -> Query: "War", Year: "2019")
    parts = raw_query.split()
    year = ""
    query = raw_query
    if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 4:
        year = parts[-1]
        query = " ".join(parts[:-1])
    
    msg = await message.reply_text(f"🔍 Searching for '{raw_query}'...")
    
    # Search API Call
    if year:
        # Search movie and TV separately if year is explicitly provided
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
        date = item.get('release_date') or item.get('first_air_date', '')
        r_year = date[:4] if date else "N/A"
        
        # Identify type if from mixed results
        m_type = item.get('media_type')
        if not m_type: m_type = "movie" if "title" in item else "tv"
            
        icon = "🎬" if m_type == "movie" else "📺"
        # format: opt_{movie/tv}_{id} -> opt_m_123 or opt_t_123 (Shortened to save callback limits)
        short_type = "m" if m_type == "movie" else "t"
        buttons.append([InlineKeyboardButton(f"{icon} {title} ({r_year})", callback_data=f"opt_{short_type}_{item.get('id')}")])
    
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_menu")])
    await msg.edit_text(f"🔍 Search: **{raw_query}**\n\n✨ **Select Media:**", reply_markup=InlineKeyboardMarkup(buttons))

# ==========================================
# 📱 DYNAMIC MENUS & SUB-MENUS
# ==========================================
# 1. Main Category Menu
@app.on_callback_query(filters.regex(r"^opt_"))
async def show_main_options(client: Client, callback_query: CallbackQuery):
    # Data: opt_{m/t}_{id}
    data = callback_query.data.split("_")
    s_type, m_id = data[1], data[2]
    type_label = "Movie" if s_type == "m" else "Web Series"
    
    buttons = [
        [InlineKeyboardButton("🌄 Landscape (Horizontal)", callback_data=f"sub_b_{s_type}_{m_id}")],
        [InlineKeyboardButton("🖼 Portrait (Vertical)", callback_data=f"sub_p_{s_type}_{m_id}")],
        [InlineKeyboardButton("🅰 Logos", callback_data=f"img_l_all_{s_type}_{m_id}_0")], # Direct to logos
        [InlineKeyboardButton("❌ Close", callback_data="close_menu")]
    ]
    await callback_query.message.edit_text(f"✨ **{type_label} Selected!**\nChoose aspect ratio:", reply_markup=InlineKeyboardMarkup(buttons))

# 2. Text vs Clean Sub-Menu
@app.on_callback_query(filters.regex(r"^sub_"))
async def show_sub_options(client: Client, callback_query: CallbackQuery):
    # Data: sub_{b/p}_{s_type}_{m_id} (b=backdrops/landscape, p=posters/portrait)
    data = callback_query.data.split("_")
    cat, s_type, m_id = data[1], data[2], data[3]
    cat_label = "Landscape" if cat == "b" else "Portrait"
    
    buttons = [
        [InlineKeyboardButton("📝 Posters (With Text/Language)", callback_data=f"img_{cat}_txt_{s_type}_{m_id}_0")],
        [InlineKeyboardButton("🖼 Screenshots (Clean/Without Text)", callback_data=f"img_{cat}_cln_{s_type}_{m_id}_0")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"opt_{s_type}_{m_id}")]
    ]
    await callback_query.message.edit_text(f"**{cat_label} Options:**\nText wali image chahiye ya clean background?", reply_markup=InlineKeyboardMarkup(buttons))

# ==========================================
# 🖼 IMAGE VIEWER (SMART FILTERING)
# ==========================================
@app.on_callback_query(filters.regex(r"^img_"))
async def paginate_images(client: Client, callback_query: CallbackQuery):
    # Data: img_{cat}_{flt}_{s_type}_{m_id}_{index}
    data = callback_query.data.split("_")
    cat, flt, s_type, m_id, index = data[1], data[2], data[3], data[4], int(data[5])
    
    m_type = "movie" if s_type == "m" else "tv"
    
    movie_info = requests.get(f"{TMDB_BASE_URL}/{m_type}/{m_id}").json()
    name = movie_info.get("title") or movie_info.get("name", "Unknown")
    
    res = requests.get(f"{TMDB_BASE_URL}/{m_type}/{m_id}/images").json()
    
    # Map category codes
    cat_key = "backdrops" if cat == "b" else "posters" if cat == "p" else "logos"
    raw_images = res.get(cat_key, [])
    
    # SMART FILTERING LOGIC
    if flt == "txt":
        # With Text (Language is present and not 'xx')
        images_list = [img for img in raw_images if img.get('iso_639_1') is not None and img.get('iso_639_1') != "xx"]
    elif flt == "cln":
        # Screenshots / Clean (Language is None or 'xx')
        images_list = [img for img in raw_images if img.get('iso_639_1') is None or img.get('iso_639_1') == "xx"]
    else:
        images_list = raw_images # For Logos ('all')
        
    if not images_list:
        return await callback_query.answer("❌ Is criteria me koi image nahi mili!", show_alert=True)
        
    if index >= len(images_list) or index < 0: index = 0
    img_data = images_list[index]
    full_image_url = f"{TMDB_IMAGE_BASE}{img_data['file_path']}"
    
    # Formatting
    lang = img_data.get('iso_639_1')
    lang_display = lang if lang and lang != 'xx' else "N/A (Clean)"
    cat_display = "Landscape" if cat == "b" else "Portrait" if cat == "p" else "Logo"
    
    caption_text = (
        f"🔍 **Search:** {name}\n\n"
        f"• **Category:** {cat_display}\n"
        f"• **Language:** {lang_display}\n"
        f"• **Size:** {img_data.get('width')}x{img_data.get('height')}\n"
        f"• **Image:** [Link (JPG)]({full_image_url})\n\n"
        f"🚀 **Powered By** {POWERED_BY}"
    )
    cb_prefix = f"img_{cat}_{flt}_{s_type}_{m_id}"

    # Smooth Navigation & Back Buttons
    nav_buttons = []
    if index > 0: nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{cb_prefix}_{index-1}"))
    else: nav_buttons.append(InlineKeyboardButton("⛔", callback_data="ignore"))
        
    nav_buttons.append(InlineKeyboardButton(f"{index + 1}/{len(images_list)}", callback_data="ignore"))
    
    if index < len(images_list) - 1: nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{cb_prefix}_{index+1}"))
    else: nav_buttons.append(InlineKeyboardButton("⛔", callback_data="ignore"))
    
    # Smart Back Button logic
    back_data = f"opt_{s_type}_{m_id}" if cat == "l" else f"sub_{cat}_{s_type}_{m_id}"
        
    markup = InlineKeyboardMarkup([
        nav_buttons,
        [InlineKeyboardButton("🔙 Back", callback_data=back_data)],
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

# ==========================================
# 🛑 UTILITY (CLOSE, IGNORE) & OTT MODULE INTEGRATION
# ==========================================
@app.on_callback_query(filters.regex("close_menu"))
async def close_menu(client, callback_query):
    await callback_query.message.delete()

@app.on_callback_query(filters.regex("ignore"))
async def ignore_btn(client, callback_query):
    await callback_query.answer()

# NOTE: Future OTT Integration
# Agar aap `ott/prime.py` banate hain, toh bas usko upar import karein 
# Aur yahan /prime ka command ekdum Netflix (/nf) ki tarah paste kar dein. Code already uske liye ready hai!

if __name__ == "__main__":
    app.run()
