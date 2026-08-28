import requests
from bs4 import BeautifulSoup

def get_netflix_poster(url):
    """
    Netflix URL se main thumbnail (og:image) extract karta hai.
    """
    # Strong User-Agent takki Netflix bot samajh kar block na kare
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Netflix apne main posters og:image tag me rakhta hai
            meta_image = soup.find("meta", property="og:image")
            
            if meta_image and meta_image.get("content"):
                return meta_image["content"]
                
    except Exception as e:
        print(f"Netflix Scrape Error: {e}")
        
    return None
