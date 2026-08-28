import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from db import db
from ott import get_all_ott_posters  # OTT module import kiya

# Aapke Credentials
BOT_TOKEN = "8603433381:AAFXNTkde8LbIzYO66Fajgxpde_DxDihops"
API_ID = 32541562
API_HASH = "e37e4432298d5a5eb4a6e32c18804283"

TMDB_BASE_URL = "https://tmdbapi.the-zake.workers.dev/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"

app = Client("PremiumPosterBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await db.add_user(message.from_user.id)
    text = "🔥 **Premium Poster & OTT Scraper Bot** 🔥\n\n🎬 `/p {movie}` - TMDB & OTT se high-quality posters nikalne ke liye!"
    await message.reply_text(text)

@app.on_message(filters.command("p"))
async def search_movie(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Kripya movie ka naam dein. Example: `/p Alpha`")
    
    query = message.text.split(" ", 1)[1].strip()
    msg = await message.reply_text(f"🔍 '{query}' ko saare platforms par dhundh raha hoon...")
    
    # TMDB Search
    response = requests.get(f"{TMDB_BASE_URL}/search/movie", params={"query": query}).json()
    results = response.get("results", [])
    
    if not results:
        return await msg.edit_text("Sorry, aisi koi movie nahi mili.")

    buttons = []
    for movie in results[:5]:  # Top 5 results
        title = movie.get('title', 'Unknown')
        year = movie.get('release_date', 'N/A')[:4]
        movie_id = movie.get('id')
        
        buttons.append([InlineKeyboardButton(f"🎬 {title} ({year})", callback_data=f"opt_{movie_id}")])
    
    await msg.edit_text("✨ **Apni movie select karein:**", reply_markup=InlineKeyboardMarkup(buttons))

# --- OPTION SELECTION (OTT vs TMDB) ---
@app.on_callback_query(filters.regex(r"^opt_"))
async def show_options(client: Client, callback_query: CallbackQuery):
    movie_id = callback_query.data.split("_")[1]
    
    # Premium Menu
    buttons = [
        [InlineKeyboardButton("🔥 OTT Posters (Netflix, Prime, etc)", callback_data=f"ott_{movie_id}_0")],
        [InlineKeyboardButton("🖼 TMDB Posters", callback_data=f"img_posters_{movie_id}_0")],
        [InlineKeyboardButton("🌄 Landscape", callback_data=f"img_backdrops_{movie_id}_0")],
        [InlineKeyboardButton("🅰 Logos", callback_data=f"img_logos_{movie_id}_0")]
    ]
    await callback_query.message.edit_text("🌟 **Kya dekhna chahte hain?**", reply_markup=InlineKeyboardMarkup(buttons))

# --- SMOOTH PAGINATION LOGIC (Both OTT and TMDB) ---
@app.on_callback_query(filters.regex(r"^(img|ott)_"))
async def paginate_images(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    action = data[0]  # 'img' ya 'ott'
    
    # Agar action 'ott' hai
    if action == "ott":
        movie_id = data[1]
        index = int(data[2])
        
        # Movie ka naam TMDB se pehle nikalte hain OTT search ke liye
        movie_info = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}").json()
        movie_name = movie_info.get("title", "")
        
        # OTT module call
        images_list = get_all_ott_posters(movie_name)
        if not images_list:
            return await callback_query.answer("Sare OTT platforms block kar rahe hain ya poster nahi mila!", show_alert=True)
            
        full_image_url = images_list[index]["url"]
        caption_text = f"🔥 **Platform:** {images_list[index]['platform']}\n(Image {index + 1}/{len(images_list)})"
        
        # Setup callback prefixes for next/prev
        cb_prefix = f"ott_{movie_id}"
        
    # Agar action 'img' (TMDB) hai
    else:
        img_type = data[1]
        movie_id = data[2]
        index = int(data[3])
        
        res = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/images").json()
        images_list = res.get(img_type, [])
        
        if not images_list:
            return await callback_query.answer("Is category me image available nahi hai!", show_alert=True)
            
        full_image_url = f"{TMDB_IMAGE_BASE}{images_list[index]['file_path']}"
        caption_text = f"✨ **Type:** {img_type.capitalize()}\n(Image {index + 1}/{len(images_list)})"
        cb_prefix = f"img_{img_type}_{movie_id}"

    # Index limit check
    if index >= len(images_list) or index < 0:
        index = 0
        
    # Buttons for Next/Prev
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅ Prev", callback_data=f"{cb_prefix}_{index-1}"))
    if index < len(images_list) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡", callback_data=f"{cb_prefix}_{index+1}"))
        
    markup = InlineKeyboardMarkup([nav_buttons, [InlineKeyboardButton("🔙 Back", callback_data=f"opt_{movie_id}")]])
    
    # 🌟 MAGIC HAPPENS HERE: SMOOTH REFRESH 🌟
    # Agar existing message Text hai (Menu wala), toh nayi photo bhejni padegi
    if not callback_query.message.photo:
        await callback_query.message.delete()
        await client.send_photo(
            chat_id=callback_query.message.chat.id,
            photo=full_image_url,
            caption=caption_text,
            reply_markup=markup
        )
    # Agar message pehle se Photo hai (Matlab user ne Next/Prev dabaya hai), toh Media edit karenge!
    else:
        await client.edit_message_media(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.id,
            media=InputMediaPhoto(media=full_image_url, caption=caption_text),
            reply_markup=markup
        )

if __name__ == "__main__":
    app.run()
