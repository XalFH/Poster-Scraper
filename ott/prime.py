import requests
from bs4 import BeautifulSoup
import re

def scrape(url):
    """
    Amazon Prime Video Scraper.
    Return dictionary: title, main_poster, portrait, cover
    """
    # Prime bot-protection bypass karne ke liye strong User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            data = {"title": "Prime Video Title", "main_poster": "", "portrait": "", "cover": ""}
            
            # 1. Title Extract (Clean Format)
            title_tag = soup.find('title')
            if title_tag:
                # Prime ke titles usually "Watch [Movie] | Prime Video" hote hain, usko clean karna:
                title = title_tag.text.replace("Watch ", "").split(" |")[0].split(" - ")[0].strip()
                data["title"] = title
            else:
                og_title = soup.find("meta", property="og:title")
                if og_title: data["title"] = og_title["content"].replace("Watch ", "").strip()
            
            # 2. Extract standard Meta Images
            twitter_img = soup.find("meta", attrs={"name": "twitter:image"})
            og_img = soup.find("meta", property="og:image")
            
            if twitter_img: data["main_poster"] = twitter_img["content"]
            if og_img: data["cover"] = og_img["content"]
            
            # 3. 🌟 MAGIC TRICK: Amazon Media Server Regex 🌟
            # Prime hamesha 'pv-target-images' folder me original high-res posters rakhta hai
            html_text = response.text
            prime_images = re.findall(r'https://m\.media-amazon\.com/images/S/pv-target-images/[a-zA-Z0-9_]+\.jpg', html_text)
            
            if prime_images:
                # Duplicate images hata kar unique list banana
                unique_images = list(set(prime_images))
                
                # Agar meta tags se image nahi mili, toh regex wali pehli image use karo
                if not data["main_poster"]: data["main_poster"] = unique_images[0]
                
                # Agar multiple high-res images mili hain, toh portrait/cover me set kar do
                if len(unique_images) > 1: data["portrait"] = unique_images[1]
                if len(unique_images) > 2: data["cover"] = unique_images[2]
            
            # Fallbacks (Agar portrait ya cover blank reh jaye)
            if not data["main_poster"]: data["main_poster"] = data["cover"]
            if not data["portrait"]: data["portrait"] = data["main_poster"]
            if not data["cover"]: data["cover"] = data["main_poster"]
                
            if data["main_poster"]: 
                return data
                
    except Exception as e:
        print(f"Prime Scrape Error: {e}")
        
    return None
