import requests

# Complete list of supported OTT platforms
OTT_PLATFORMS = [
    'aaonxt', 'addatimes', 'aha', 'airtel', 'amz', 'appletv', 'atrangii', 'bms', 
    'chaupal', 'crunchyroll', 'dangal', 'eros', 'hoichoi', 'hulu', 'hungama', 
    'iqyi', 'jojo', 'lionsgate', 'mubi', 'mxplayer', 'nf', 'playflix', 'plextv', 
    'sainaplay', 'shemaroo', 'sonyliv', 'sunnxt', 'tataplay', 'ticketnew', 'tubi', 
    'ultra', 'ultrajhakaas', 'viki', 'viu', 'vivamax', 'wetv', 'youku', 'yt', 'zee5', 'prime'
]

def scrape_ott(platform, url):
    """
    Centralized OTT Scraper using the master API.
    Expected JSON: {"title": "...", "landscape": "...", "portrait": "...", "cover": "..."}
    """
    api_url = f"https://as-scraper-api.onrender.com/posters/{platform}?url={url}&key=okworld"
    try:
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"OTT API Error ({platform}): {e}")
    
    return None
