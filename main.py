import asyncio
# Fix for Pyrogram on newer Python versions
asyncio.set_event_loop(asyncio.new_event_loop())

import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from db import db
from ott import get_all_ott_posters

# Aapke Credentials
BOT_TOKEN = "8603433381:AAFXNTkde8LbIzYO66Fajgxpde_DxDihops"
API_ID = 32541562
API_HASH = "e37e4432298d5a5eb4a6e32c18804283"
POWERED_BY = "@YourChannel" # Yahan apna username daalein

TMDB_BASE_URL = "https://tmdbapi.the-zake.workers.dev/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"

app = Client("PremiumPosterBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# --- AUTHORIZATION CHECK FUNCTION ---
async def is_authorized(callback_query: CallbackQuery):
    """Check if the user clicking the button is the one who requested it."""
    if callback_query.message.reply_to_message:
        requester_id = callback_query.message.reply_to_message.from_user.id
        if callback_query.from_user.id != requester_id:
            await callback_query.answer("⚠️ This is not for you!", show_alert=True)
            return False
    return True

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await db.add_user(message.from_user.id)
    text = "🔥 **Premium Poster Bot** 🔥\n\n🎬 `/p {movie}` - High-quality posters nikalne ke liye!"
    await message.reply_text(text)

@app.on_message(filters.command("p"))
async def search_movie(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Kripya movie ka naam dein. Example: `/p Alpha`")
    
    query = message.text.split(" ", 1)[1].strip()
    msg = await message.reply_text(f"🔍 Searching for '{query}'...", reply_to_message_id=message.id)
    
    response = requests.get(f"{TMDB_BASE_URL}/search/movie", params={"query": query}).json()
    results = response.get("results", [])
    
    if not results:
        return await msg.edit_text("Sorry, aisi koi movie nahi mili.")

    buttons = []
    for movie in results[:5]:
        title = movie.get('title', 'Unknown')
        year = movie.get('release_date', 'N/A')[:4]
        movie_id = movie.get('id')
        buttons.append([InlineKeyboardButton(f"🎬 {title} ({year})", callback_data=f"opt_{movie_id}_{query}")])
    
    # Add a Close button at the bottom
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_menu")])
    await msg.edit_text(f"🔍 Search: **{query}**\n\n✨ **Select a Movie:**", reply_markup=InlineKeyboardMarkup(buttons))

# --- CATEGORY SELECTION MENU ---
@app.on_callback_query(filters.regex(r"^opt_"))
async def show_options(client: Client, callback_query: CallbackQuery):
    if not await is_authorized(callback_query): return
    
    data = callback_query.data.split("_")
    movie_id = data[1]
    query = data[2] if len(data) > 2 else "Movie"
    
    buttons = [
        [InlineKeyboardButton("🖼 Posters (Portrait)", callback_data=f"img_posters_{movie_id}_0")],
        [InlineKeyboardButton("🌄 Landscape", callback_data=f"img_backdrops_{movie_id}_0")],
        [InlineKeyboardButton("🅰 Logos", callback_data=f"img_logos_{movie_id}_0")],
        [InlineKeyboardButton("🌐 Search OTT Posters", callback_data=f"ott_{movie_id}_0")],
        [InlineKeyboardButton("🔙 Back to Results", callback_data="back_to_search"),
         InlineKeyboardButton("❌ Close", callback_data="close_menu")]
    ]
    await callback_query.message.edit_text(
        f"🎬 **Movie Selected!**\n\nChoose the type of image you want to extract:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- IMAGE VIEWER (PAGINATION) ---
@app.on_callback_query(filters.regex(r"^(img|ott)_"))
async def paginate_images(client: Client, callback_query: CallbackQuery):
    if not await is_authorized(callback_query): return
    
    data = callback_query.data.split("_")
    action = data[0]
    
    # 1. OTT LOGIC
    if action == "ott":
        movie_id, index = data[1], int(data[2])
        movie_info = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}").json()
        movie_name = movie_info.get("title", "")
        
        images_list = get_all_ott_posters(movie_name)
        if not images_list:
            return await callback_query.answer("Sare OTT platforms block kar rahe hain!", show_alert=True)
            
        img_data = images_list[index]
        full_image_url = img_data["url"]
        
        # Format OTT Caption
        caption_text = (
            f"🔍 **Search:** {movie_name}\n\n"
            f"• **Platform:** {img_data['platform']}\n"
            f"• **Image:** [Link (JPG)]({full_image_url})\n\n"
            f"🚀 **Powered By** {POWERED_BY}"
        )
        cb_prefix = f"ott_{movie_id}"
        
    # 2. TMDB LOGIC
    else:
        img_type, movie_id, index = data[1], data[2], int(data[3])
        movie_info = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}").json()
        movie_name = movie_info.get("title", "Unknown")
        year = movie_info.get("release_date", "N/A")[:4]
        
        res = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/images").json()
        images_list = res.get(img_type, [])
        
        if not images_list:
            return await callback_query.answer("Is category me image nahi mili!", show_alert=True)
            
        if index >= len(images_list) or index < 0: index = 0
        
        img_data = images_list[index]
        full_image_url = f"{TMDB_IMAGE_BASE}{img_data['file_path']}"
        lang = img_data.get('iso_639_1', 'N/A') or 'N/A'
        
        # Professional UI Format (Just like screenshot)
        caption_text = (
            f"🔍 **Search:** {movie_name}\n"
            f"🎬 **{movie_name} ({year})**\n\n"
            f"• **Category:** {img_type.capitalize()}\n"
            f"• **Language:** {lang}\n"
            f"• **Size:** {img_data.get('width')}x{img_data.get('height')}\n"
            f"• **Image:** [Link (JPG)]({full_image_url})\n"
            f"🔗 [TMDB Link](https://www.themoviedb.org/movie/{movie_id})\n\n"
            f"🚀 **Powered By** {POWERED_BY}"
        )
        cb_prefix = f"img_{img_type}_{movie_id}"

    # --- BUTTON LAYOUT (Prev | Page/Total | Next) ---
    nav_buttons = []
    
    # Prev Button
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{cb_prefix}_{index-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("⛔", callback_data="ignore"))
        
    # Page Indicator
    nav_buttons.append(InlineKeyboardButton(f"{index + 1}/{len(images_list)}", callback_data="ignore"))
    
    # Next Button
    if index < len(images_list) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{cb_prefix}_{index+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("⛔", callback_data="ignore"))
        
    markup = InlineKeyboardMarkup([
        nav_buttons,
        [InlineKeyboardButton("🔙 Back to Types", callback_data=f"opt_{movie_id}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_menu")]
    ])
    
    # Display logic (Smooth transition)
    try:
        if not callback_query.message.photo:
            await callback_query.message.delete()
            await client.send_photo(
                chat_id=callback_query.message.chat.id,
                photo=full_image_url,
                caption=caption_text,
                reply_markup=markup
            )
        else:
            await client.edit_message_media(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.id,
                media=InputMediaPhoto(media=full_image_url, caption=caption_text),
                reply_markup=markup
            )
    except Exception as e:
        await callback_query.answer("Error loading image!", show_alert=True)

# --- UTILITY BUTTONS (Close / Ignore) ---
@app.on_callback_query(filters.regex("close_menu"))
async def close_menu(client: Client, callback_query: CallbackQuery):
    if not await is_authorized(callback_query): return
    await callback_query.message.delete()

@app.on_callback_query(filters.regex("ignore"))
async def ignore_btn(client: Client, callback_query: CallbackQuery):
    await callback_query.answer()

if __name__ == "__main__":
    app.run()
