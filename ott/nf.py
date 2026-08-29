import requests
from bs4 import BeautifulSoup
import json

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
            
            title_tag = soup.find('title')
            if title_tag:
                data["title"] = title_tag.text.replace(" | Netflix Official Site", "").replace(" | Netflix", "").strip()
            
            twitter_img = soup.find("meta", attrs={"name": "twitter:image"})
            if twitter_img: data["main_poster"] = twitter_img["content"]
            
            og_img = soup.find("meta", property="og:image")
            if og_img:
                data["cover"] = og_img["content"]
                if not data["main_poster"]: data["main_poster"] = og_img["content"]
            
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
            
            if not data["portrait"]: data["portrait"] = data["main_poster"]
            if not data["cover"]: data["cover"] = data["main_poster"]
                
            if data["main_poster"]: return data
    except Exception as e:
        print(f"Scrape Error: {e}")
    return None
