import requests
from bs4 import BeautifulSoup

# Ek basic web scraper jo search karke og:image nikalne ki koshish karta hai
def scrape_ott_poster(movie_name, platform):
    """
    movie_name: Movie ka naam (e.g., 'Alpha')
    platform: OTT ka naam (e.g., 'netflix', 'hotstar', 'zee5', 'prime')
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # Example queries based on platform
    queries = {
        "netflix": f"https://www.netflix.com/search?q={movie_name}",
        "prime": f"https://www.primevideo.com/search/ref=atv_sr_sug_1?phrase={movie_name}",
        "zee5": f"https://www.zee5.com/search?q={movie_name}",
        "hotstar": f"https://www.hotstar.com/in/explore?search_query={movie_name}"
    }
    
    url = queries.get(platform)
    if not url:
        return None

    try:
        # Note: Ye ek basic scraping hai. Real OTTs par DRM/Cloudflare hota hai.
        # Aap yahan apni custom OTT APIs integrate kar sakte hain.
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, 'html.parser')
            meta_img = soup.find("meta", property="og:image")
            if meta_img and meta_img.get("content"):
                return meta_img["content"]
    except Exception as e:
        print(f"{platform} Scraping Error: {e}")
    
    return None

def get_all_ott_posters(movie_name):
    """Sare platforms se posters collect karta hai"""
    platforms = ["netflix", "prime", "hotstar", "zee5"]
    results = []
    
    for plt in platforms:
        img = scrape_ott_poster(movie_name, plt)
        if img:
            results.append({"platform": plt.capitalize(), "url": img})
            
    return results
