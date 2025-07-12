from flask import Flask, render_template, request
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from datetime import datetime
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

def map_language_to_industry(language):
    language = language.lower()
    mapping = {
        "english": "hollywood",
        "hindi": "bollywood",
        "telugu": "telugu",
        "tamil": "tamil",
        "malayalam": "malayalam",
        "kannada": "kannada",
        "punjabi": "punjabi"
    }
    return mapping.get(language, language)  # fallback to language itself if not found

# WEATHER API
def get_weather(city, api_key):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        weather = data["weather"][0]["main"]
        temp = data["main"]["temp"]
        return f"{weather}, {temp}°C", weather.lower()
    return "Unknown", print("unknown")

# MOOD LOGIC
def decide_music_category(mood, weather, age):
    if mood == "happy" and ("clouds" in weather):
        return "party"
    elif mood == "sad" or ("rain" in weather):
        return "chill"
    elif mood == "relaxed":
        return "top"
    elif mood == "inspired" or weather in ["snow", "hail"]:
        return "classical"
    elif mood in ["energetic", "nostalgic"] and age < 30:
        return "pop"
    elif mood in ["nostalgic", "energetic"] and age >= 30:
        return "retro"
    elif mood == "romantic":
        return "love"
    elif mood == "devotional":
        return "devotional" 
    else:
        return "trending"



# SPOTIFY
def get_playlist_link(category, language, year_range):
    try:
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

        if not client_id or not client_secret:
            print("⚠️ Spotify credentials not set.")
            return None, "Missing Spotify credentials"

        auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(auth_manager=auth)

        industry = map_language_to_industry(language)

        queries = [
            f"{category} {language} {year_range} songs",
            f"{category} {language} songs",
            f"{industry} {year_range} songs",
            f"{industry} songs",
            f"Trending {language} songs"
        ]

        for i, query in enumerate(queries):
            try:
                results = sp.search(q=query.strip(), type='playlist', limit=1)
                items = results.get("playlists", {}).get("items", [])
                if items:
                    print(f"[🔍 Match Level {i+1}] Query: {query}")
                    playlist_url = items[0]["external_urls"]["spotify"]
                    playlist_id = playlist_url.split("/")[-1].split("?")[0]
                    print(f"[✅ Level {i+1}] Query: {query}")
                    print("🔗", playlist_url)
                    print("🆔", playlist_id)
                    return playlist_url,playlist_id, query
            except Exception as inner_error:
                print(f"⚠️ Error searching for query '{query}': {inner_error}")
                continue  # move on to next query

        print("[❌ No matching playlist found]")
        return None, "No playlist found — playing Trending fallback"

    except Exception as e:
        print(f"🚨 Critical error in get_playlist_link: {e}")
        return None, "Internal error while searching playlist"


def _log_user_session(nickname, query, playlist_url):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": nickname or "Guest",
        "query": query,
        "playlist": playlist_url or "None"
    }
    log_path = "user_history.json"
    try:
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                data = json.load(f)
        else:
            data = []
        data.append(log_entry)
        with open(log_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[⚠️ Log Error] {e}")

@app.route("/history")
def view_history():
    try:
        with open("user_history.json", "r") as f:
            history = json.load(f)
        return render_template("history.html", history=history)
    except Exception as e:
        return f"Error loading history: {e}", 500
    
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nickname = request.form.get("nickname", "Guest")
        city = request.form.get("city", "")
        mood = request.form.get("mood", "").lower()
        age = int(request.form.get("age", 25))
        language = request.form.get("language", "").lower()
        year_range = request.form.get("year_range", "")

        weather_type = get_weather(city, os.getenv("OPENWEATHER_API_KEY"))
        category = decide_music_category(mood, weather_type, age)
        playlist_url,playlist_id,search_used = get_playlist_link(category, language, year_range)
        

        if playlist_url:
            return render_template("index.html",
                                   result=True,
                                    nickname=nickname,
                                    weather=weather_type,
                                    mood=mood,
                                    age=age,
                                    language=language,
                                    playlist_id=playlist_id,
                                    playlist=playlist_url,
                                    search_used=search_used)
        else:
            return render_template("index.html",
                                   result=True,
                                   playlist=None,
                                   playlist_id=playlist_id,
                                   search_used=search_used)

    return render_template("index.html", result=False)

if __name__ == "__main__":
    app.run(debug=True)







