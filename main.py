import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import requests
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db import db

# Credentials
BOT_TOKEN = "8603433381:AAFXNTkde8LbIzYO66Fajgxpde_DxDihops"
API_ID = 32541562
API_HASH = "e37e4432298d5a5eb4a6e32c18804283"

TMDB_BASE_URL = "https://tmdbapi.the-zake.workers.dev/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"

app = Client("PosterScraperBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await db.add_user(message.from_user.id)
    text = "Hello! Main Advanced Poster Scraper bot hoon. 🍿\n\n🎬 `/p {movie name}` - TMDB search with buttons."
    await message.reply_text(text)

# --- TMDB SEARCH ---
@app.on_message(filters.command("p"))
async def search_tmdb(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Movie ka naam dein. Example: `/p Inception`")
    
    query = message.text.split(" ", 1)[1].strip()
    msg = await message.reply_text(f"🔍 Searching for '{query}'...")
    
    response = requests.get(f"{TMDB_BASE_URL}/search/movie", params={"query": query}).json()
    results = response.get("results", [])
    
    if not results:
        return await msg.edit_text("Koi movie nahi mili.")

    buttons = []
    # Sirf top 5 results dikhayenge buttons me
    for movie in results[:5]:
        title = movie.get('title', 'Unknown')
        year = movie.get('release_date', 'N/A')[:4]
        movie_id = movie.get('id')
        # Callback data limits to 64 bytes, keeping it short
        buttons.append([InlineKeyboardButton(f"{title} ({year})", callback_data=f"movie_{movie_id}")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    await msg.edit_text("🎬 **Select a Movie:**", reply_markup=reply_markup)

# --- HANDLE MOVIE SELECTION (Categories) ---
@app.on_callback_query(filters.regex(r"^movie_"))
async def select_image_type(client: Client, callback_query: CallbackQuery):
    movie_id = callback_query.data.split("_")[1]
    
    buttons = [
        [InlineKeyboardButton("🖼 Posters", callback_data=f"img_posters_{movie_id}_0")],
        [InlineKeyboardButton("🌄 Landscape (Backdrops)", callback_data=f"img_backdrops_{movie_id}_0")],
        [InlineKeyboardButton("🅰 Logos", callback_data=f"img_logos_{movie_id}_0")]
    ]
    await callback_query.message.edit_text("Kaunsi image chahiye?", reply_markup=InlineKeyboardMarkup(buttons))

# --- HANDLE PAGINATION (Next/Prev) ---
@app.on_callback_query(filters.regex(r"^img_"))
async def show_image(client: Client, callback_query: CallbackQuery):
    _, img_type, movie_id, index = callback_query.data.split("_")
    index = int(index)
    
    # Fetch all images for this movie
    response = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/images").json()
    
    # Map selection to TMDB API keys
    images_list = response.get(img_type, [])
    
    if not images_list:
        return await callback_query.answer("Is category me koi image nahi hai!", show_alert=True)
    
    if index >= len(images_list) or index < 0:
        index = 0 # reset if out of bounds
        
    image_path = images_list[index].get("file_path")
    full_image_url = f"{TMDB_IMAGE_BASE}{image_path}"
    
    # Pagination Buttons
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅ Prev", callback_data=f"img_{img_type}_{movie_id}_{index-1}"))
    if index < len(images_list) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡", callback_data=f"img_{img_type}_{movie_id}_{index+1}"))
        
    markup = InlineKeyboardMarkup([nav_buttons, [InlineKeyboardButton("🔙 Back to Types", callback_data=f"movie_{movie_id}")]])
    
    # Update message with new image (we have to delete and resend to change text to photo)
    await callback_query.message.delete()
    await client.send_photo(
        chat_id=callback_query.message.chat.id,
        photo=full_image_url,
        caption=f"Image {index + 1} of {len(images_list)}",
        reply_markup=markup
    )

if __name__ == "__main__":
    app.run()
