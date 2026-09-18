# commands.py

OTT_COMMANDS = {
    "nf": "Netflix",
    "prime": "Amazon Prime",
    "bms": "BookMyShow",
    "zee5": "ZEE5",
    "sonyliv": "SonyLIV",
    "hulu": "Hulu",
    "crunchyroll": "Crunchyroll",
    "mxplayer": "MX Player",
    "hoichoi": "Hoichoi",
    "aha": "Aha Video",
    "jojo": "Jojo",
    "airtel": "Airtel Xstream",
    "amz": "Amazon MiniTV",
    "appletv": "Apple TV+",
    "atrangii": "Atrangii",
    "chaupal": "Chaupal",
    "dangal": "Dangal Play",
    "eros": "Eros Now",
    "hungama": "Hungama Play",
    "iqyi": "iQIYI",
    "lionsgate": "Lionsgate Play",
    "mubi": "MUBI",
    "playflix": "Playflix",
    "plextv": "Plex TV",
    "sainaplay": "Saina Play",
    "shemaroo": "ShemarooMe",
    "sunnxt": "Sun NXT",
    "tataplay": "Tata Play",
    "ticketnew": "TicketNew",
    "tubi": "Tubi TV",
    "ultra": "Ultra",
    "ultrajhakaas": "Ultra Jhakaas",
    "viki": "Rakuten Viki",
    "viu": "Viu",
    "vivamax": "Vivamax",
    "wetv": "WeTV",
    "youku": "Youku",
    "yt": "YouTube",
    "aaonxt": "AAO NXT",
    "addatimes": "Addatimes",
    "jiocinema": "JioCinema",
    "discovery": "Discovery+",
    "paramount": "Paramount+",
    "altbalaji": "ALTT"
}

def get_help_text():
    """Generates a beautiful, compact UI string for the Help Menu to fit Telegram's caption limits."""
    text = "🎯 **Supported OTT Platforms**\n"
    text += "💡 **Usage:** `/<command> <url>`\n\n"
    
    # Format compactly: `/cmd` (Name)
    formatted_cmds = []
    for cmd in sorted(OTT_COMMANDS.keys()):
        name = OTT_COMMANDS[cmd]
        formatted_cmds.append(f"`/{cmd}` ({name})")
        
    # Join with a separator for a clean grid-like look
    text += " • ".join(formatted_cmds)
    
    text += "\n\n✨ *...and many more being added soon!*"
    return text
