import requests
from bs4 import BeautifulSoup
import json

def get_netflix_data(url):
    """
    Netflix URL se Title, Poster, Portrait aur Cover extract karta hai.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Data store karne ke liye dictionary
            data = {
                "title": "Netflix Title",
                "main_poster": "",
                "portrait": "",
                "cover": ""
            }
            
            # Netflix usually ek JSON-LD script tag rakhta hai jisme saari details hoti hain
            script_tag = soup.find('script', type='application/ld+json')
            
            if script_tag:
                try:
                    json_data = json.loads(script_tag.string)
                    data["title"] = json_data.get("name", "Netflix Title")
                    
                    # Image extract karna
                    image_data = json_data.get("image", "")
                    if isinstance(image_data, str):
                        data["main_poster"] = data["portrait"] = data["cover"] = image_data
                    elif isinstance(image_data, list) and len(image_data) > 0:
                        data["main_poster"] = image_data[0]
                        data["portrait"] = image_data[0] if len(image_data) == 1 else image_data[1]
                        data["cover"] = image_data[-1]
                except Exception as e:
                    print(f"JSON Parsing error: {e}")
            
            # Agar JSON se link nahi mila, toh Meta tags use karenge (Fallback)
            if not data["main_poster"]:
                meta_image = soup.find("meta", property="og:image")
                if meta_image:
                    data["main_poster"] = data["portrait"] = data["cover"] = meta_image["content"]
            
            # Fallback for Title
            if data["title"] == "Netflix Title":
                meta_title = soup.find("meta", property="og:title")
                if meta_title:
                    data["title"] = meta_title["content"]

            if data["main_poster"]:
                return data
                
    except Exception as e:
        print(f"Netflix Scrape Error: {e}")
        
    return None
