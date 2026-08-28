import os
import requests
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.types import Message
from db import db

# Aapki di hui credentials
BOT_TOKEN = "8603433381:AAFXNTkde8LbIzYO66Fajgxpde_DxDihops"
API_ID = 32541562
API_HASH = "e37e4432298d5a5eb4a6e32c18804283"
ADMINS = [2021145517]

# API Endpoints
TMDB_BASE_URL = "https://tmdbapi.the-zake.workers.dev/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"

# Pyrogram Client Setup
app = Client(
    "PosterScraperBot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    # User ko database me save karega
    await db.add_user(message.from_user.id)
    
    text = (
        "Hello! Main ek Poster Scraper bot hoon. 🍿\n\n"
        "**Commands:**\n"
        "🎬 `/p {movie name}` - TMDB se poster laane ke liye.\n"
        "🟥 `/nf {netflix url}` - Netflix link se thumbnail nikalne ke liye."
    )
    await message.reply_text(text)

@app.on_message(filters.command("nf"))
async def scrape_netflix(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Kripya valid URL dein.\nExample: `/nf https://www.netflix.com/title/...`")
    
    url = message.text.split(" ", 1)[1].strip()
    msg = await message.reply_text("Netflix link scrape kar raha hoon... ⏳")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            meta_image = soup.find("meta", property="og:image")
            
            if meta_image and meta_image["content"]:
                image_url = meta_image["content"]
                await message.reply_photo(photo=image_url, caption="🍿 Ye raha aapka Netflix Thumbnail!")
                await msg.delete()
            else:
                await msg.edit_text("Sorry, is URL se koi image nahi mil payi.")
        else:
            await msg.edit_text("Error: Website tak pahunch nahi paya.")
    except Exception as e:
        await msg.edit_text(f"Ek error aagaya: {str(e)}")

@app.on_message(filters.command("p"))
async def fetch_tmdb_poster(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Kripya movie ka naam dein.\nExample: `/p Inception`")
    
    movie_name = message.text.split(" ", 1)[1].strip()
    msg = await message.reply_text(f"'{movie_name}' ka poster dhundh raha hoon... 🔍")
    
    try:
        search_url = f"{TMDB_BASE_URL}/search/movie"
        params = {"query": movie_name}
        
        response = requests.get(search_url, params=params)
        data = response.json()
        
        if data.get("results") and len(data["results"]) > 0:
            first_result = data["results"][0]
            poster_path = first_result.get("poster_path")
            
            if poster_path:
                full_image_url = f"{TMDB_IMAGE_BASE}{poster_path}"
                caption = f"🎬 **{first_result.get('title', 'Unknown')}**\n📅 Release: {first_result.get('release_date', 'N/A')}"
                await message.reply_photo(photo=full_image_url, caption=caption)
                await msg.delete()
            else:
                await msg.edit_text("Is movie ka koi poster TMDB par available nahi hai.")
        else:
            await msg.edit_text("Sorry, aisi koi movie nahi mili.")
    except Exception as e:
        await msg.edit_text(f"Ek error aagaya: {str(e)}")

if __name__ == "__main__":
    print("Bot is successfully running...")
    app.run()
