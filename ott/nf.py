import requests
from bs4 import BeautifulSoup
import json

def get_netflix_data(url):
    """
    Netflix URL se Title, Boxart (Main Poster), Portrait aur Cover extract karta hai.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            data = {
                "title": "Netflix Title",
                "main_poster": "",
                "portrait": "",
                "cover": ""
            }
            
            # 1. Title Extract Karna (Website ke main title tag se)
            title_tag = soup.find('title')
            if title_tag:
                # Extra Netflix branding hata kar clean title nikalna
                data["title"] = title_tag.text.replace(" | Netflix Official Site", "").replace(" | Netflix", "").strip()
            
            # 2. Main Poster (Boxart with Text) Extract Karna
            # Twitter card me Netflix hamesha Text/Logo wala thumbnail rakhta hai
            twitter_img = soup.find("meta", attrs={"name": "twitter:image"})
            if twitter_img:
                data["main_poster"] = twitter_img["content"]
            
            # 3. Clean Background (Cover) ke liye OG Image
            og_img = soup.find("meta", property="og:image")
            if og_img:
                data["cover"] = og_img["content"]
                # Agar Twitter image nahi mili kisi wajah se, toh OG ko main bana do
                if not data["main_poster"]:
                    data["main_poster"] = og_img["content"]
            
            # 4. JSON-LD se Portrait image nikalne ki koshish
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag:
                try:
                    json_data = json.loads(script_tag.string)
                    # Title ka backup
                    if data["title"] == "Netflix Title":
                        data["title"] = json_data.get("name", data["title"])
                        
                    image_data = json_data.get("image", [])
                    if isinstance(image_data, str):
                        data["portrait"] = image_data
                    elif isinstance(image_data, list) and len(image_data) > 0:
                        # Netflix JSON me multiple images deta hai (Landscape, Portrait)
                        if len(image_data) > 1:
                            data["portrait"] = image_data[1] # Usually 2nd image portrait hoti hai
                        else:
                            data["portrait"] = image_data[0]
                except Exception as e:
                    print(f"JSON Parsing error: {e}")
            
            # Safety Fallbacks (Agar portrait ya cover blank reh jaye)
            if not data["portrait"]: 
                data["portrait"] = data["main_poster"]
            if not data["cover"]: 
                data["cover"] = data["main_poster"]
                
            if data["main_poster"]:
                return data
                
    except Exception as e:
        print(f"Netflix Scrape Error: {e}")
        
    return None
