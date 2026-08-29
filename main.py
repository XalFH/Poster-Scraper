import requests
from bs4 import BeautifulSoup
import json
import re

def scrape(url):
    """
    Standard Scraper Function for Dynamic Loader.
    Return dictionary: title, main_poster, portrait, cover
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            data = {"title": "Netflix Title", "main_poster": "", "portrait": "", "cover": ""}
            
            # 1. Title Extract
            title_tag = soup.find('title')
            if title_tag:
                data["title"] = title_tag.text.replace(" | Netflix Official Site", "").replace(" | Netflix", "").strip()
            
            # 2. Cover (Clean Background) Extract
            og_img = soup.find("meta", property="og:image")
            if og_img:
                data["cover"] = og_img["content"]
            
            # 3. Portrait Extract
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag:
                try:
                    json_data = json.loads(script_tag.string)
                    if data["title"] == "Netflix Title": data["title"] = json_data.get("name", data["title"])
                    image_data = json_data.get("image", [])
                    if isinstance(image_data, str): data["portrait"] = image_data
                    elif isinstance(image_data, list) and len(image_data) > 0:
                        data["portrait"] = image_data[1] if len(image_data) > 1 else image_data[0]
                except: pass
            
            # 4. 🌟 MAGIC TRICK: Extract "Boxart with Text/Logo" using specific API Hash 🌟
            # '0Qzqdxw-HG1AiOKLWWPsFOUDA2E' is Netflix's standard hash for StoryArt (Horizontal Poster with Logo)
            html_text = response.text.replace('\\x2F', '/').replace('\\/', '/')
            boxart_matches = re.findall(r'https://occ-[a-zA-Z0-9\-\.]+\.nflxso\.net/dnm/api/v6/0Qzqdxw-HG1AiOKLWWPsFOUDA2E/[a-zA-Z0-9_\-]+\.jpg(?:[a-zA-Z0-9_=\?\-%]*)', html_text)
            
            if boxart_matches:
                data["main_poster"] = boxart_matches[0]
            else:
                twitter_img = soup.find("meta", attrs={"name": "twitter:image"})
                data["main_poster"] = twitter_img["content"] if twitter_img else data["cover"]

            # Fallbacks
            if not data["portrait"]: data["portrait"] = data["main_poster"]
            if not data["cover"]: data["cover"] = data["main_poster"]
                
            if data["main_poster"]: return data
    except Exception as e:
        print(f"Scrape Error: {e}")
    return None
