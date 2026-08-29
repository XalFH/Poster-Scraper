import requests
from bs4 import BeautifulSoup
import re

def scrape(url):
    """
    Netflix URL se Main Poster, Logos aur Backgrounds (Assets) extract karta hai.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            data = {"title": "Netflix Title", "main_poster": "", "assets": []}
            
            # 1. Extract Title
            title_tag = soup.find('title')
            if title_tag:
                data["title"] = title_tag.text.replace(" | Netflix Official Site", "").replace(" | Netflix", "").strip()
            
            # 2. Extract Main Boxart Poster
            og_img = soup.find("meta", property="og:image")
            if og_img:
                data["main_poster"] = og_img["content"]
                
            # 3. Extract All Hidden Assets (Logos & Backgrounds)
            # Regex se backend API links nikal rahe hain jo Inspect Element me dikhte hain
            raw_urls = re.findall(r'https://occ-[^"\']+\.nflxso\.net/dnm/api/v6/[^"\'\\]+', response.text)
            
            valid_assets = []
            for u in raw_urls:
                clean_url = u.replace('\\u002F', '/')
                # Sirf valid images rakhein aur duplicates hatayein
                if ('.webp' in clean_url or '.jpg' in clean_url or '.png' in clean_url) and clean_url not in valid_assets:
                    valid_assets.append(clean_url)
                    
            # Top 6 raw assets limit karke bhej rahe hain taaki message zyada bada na ho
            data["assets"] = valid_assets[:6]
            
            if data["main_poster"]: 
                return data
                
    except Exception as e:
        print(f"Scrape Error: {e}")
    return None
