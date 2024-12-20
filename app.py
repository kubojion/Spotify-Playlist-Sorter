import os
import json
import openai
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import re
from flask import Flask, request, redirect, url_for, render_template


# ---------------------------
# Configuration
# ---------------------------
SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"  # e.g. "http://localhost:8888/callback"
OPENAI_API_KEY = ""

openai.api_key = OPENAI_API_KEY



scope = "playlist-read-private playlist-modify-private playlist-modify-public"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=scope
))

#############################################
# Helper Functions
#############################################

def get_user_playlists():
    playlists = []
    results = sp.current_user_playlists(limit=50)
    playlists.extend(results["items"])
    while results["next"]:
        results = sp.next(results)
        playlists.extend(results["items"])
    return playlists

def get_playlist_tracks(playlist_id):
    tracks = []
    results = sp.playlist_items(playlist_id, limit=100)
    tracks.extend(results["items"])
    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])

    track_data = []
    artist_genre_cache = {}
    for item in tracks:
        if item and 'track' in item:
            t = item['track']
            if t and t.get('id'):
                track_id = t['id']
                full_track = sp.track(track_id)
                popularity = full_track.get('popularity', 0)
                release_date = full_track['album'].get('release_date', '')

                artist_id = full_track['artists'][0]['id']
                if artist_id not in artist_genre_cache:
                    artist_info = sp.artist(artist_id)
                    artist_genres = artist_info.get('genres', [])
                    artist_genre_cache[artist_id] = artist_genres
                else:
                    artist_genres = artist_genre_cache[artist_id]

                track_data.append({
                    'id': track_id,
                    'name': full_track['name'],
                    'artist': full_track['artists'][0]['name'],
                    'popularity': popularity,
                    'release_date': release_date,
                    'genres': artist_genres
                })
    return track_data

def create_playlist(name, description="Created by sorter"):
    user = sp.current_user()
    user_id = user["id"]
    playlist = sp.user_playlist_create(user_id, name, public=False, description=description)
    return playlist["id"]

def add_tracks_to_playlist(playlist_id, track_ids):
    for i in range(0, len(track_ids), 100):
        chunk = track_ids[i:i+100]
        sp.playlist_add_items(playlist_id, chunk)

def extract_top_genres(track_data):
    from collections import Counter
    all_genres = []
    for t in track_data:
        all_genres.extend(t['genres'])
    genre_counts = Counter(all_genres)
    top_10 = genre_counts.most_common(10)
    return top_10

def sort_by_release_date(track_data):
    from datetime import datetime
    def parse_date(d):
        parts = d.split('-')
        if len(parts) == 1:
            return datetime.strptime(d, "%Y")
        elif len(parts) == 2:
            return datetime.strptime(d, "%Y-%m")
        else:
            return datetime.strptime(d, "%Y-%m-%d")

    track_data = [t for t in track_data if t['release_date']]
    track_data.sort(key=lambda x: parse_date(x['release_date']))
    return [t['id'] for t in track_data]

def sort_by_popularity(track_data):
    track_data.sort(key=lambda x: x['popularity'])
    return [t['id'] for t in track_data]

def filter_by_genre(track_data, chosen_list):
    filtered = [t['id'] for t in track_data if any(g.lower() in chosen_list for g in t['genres'])]
    return filtered

def search_track_uri(song_name, artists):
    query = f"{song_name} {', '.join(artists)}"
    results = sp.search(q=query, limit=1, type='track')
    items = results.get('tracks', {}).get('items', [])
    if items:
        return items[0]['uri']
    return None

def ask_gpt_for_playlist(num_songs, description):
    # Use the function-calling method as before
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=1,
        messages=[
            {
                "role": "system",
                "content": "You are MusicGPT, the world's best music recommendation AI. You will recommend songs based on a user's description."
            },
            {
                "role": "user",
                "content": f"Create a playlist with {num_songs} songs that fits the following description: '''{description}'''. Come up with a creative and unique name for the playlist."
            },
        ],
        functions=[
            {
                "name": "create_playlist",
                "description": "Creates a spotify playlist based on a list of songs",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "playlist_name": {
                            "type": "string",
                            "description": "Name of playlist"
                        },
                        "playlist_description": {
                            "type": "string",
                            "description": "Description for the playlist. Include that this playlist was generated by AI."
                        },
                        "songs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "songname": {
                                        "type": "string",
                                        "description": "Name of the song"
                                    },
                                    "artists": {
                                        "type": "array",
                                        "description": "List of all artists",
                                        "items": {
                                            "type": "string",
                                            "description": "Name of an artist of the song"
                                        }
                                    }
                                },
                                "required": ["songname", "artists"]
                            }
                        }
                    },
                    "required": ["songs", "playlist_name"]
                }
            }
        ]
    )

    arguments = json.loads(response["choices"][0]["message"]["function_call"]["arguments"])
    playlist_name = "AI - " + arguments["playlist_name"]
    playlist_description = arguments.get("playlist_description", "Generated by AI")
    recommended_songs = arguments["songs"]

    song_uris = []
    for song in recommended_songs:
        uri = search_track_uri(song['songname'], song['artists'])
        if uri:
            song_uris.append(uri)

    return playlist_name, playlist_description, song_uris

def analyze_playlist_and_recommend(track_data):
    brief_data = [
        {"id": t["id"], "name": t["name"], "artist": t["artist"], "genres": t["genres"], "popularity": t["popularity"]}
        for t in track_data
    ]

    prompt = (
        "You are an assistant that makes music recommendations. "
        "Below is a list of tracks (with name, artist, genres, and popularity) from a user's playlist:\n"
        f"{json.dumps(brief_data, indent=2)}\n\n"
        "Based on these tracks, recommend 20 songs. Return them in the same function_call format as before."
    )

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are MusicGPT, the best music recommendation AI."},
            {"role": "user", "content": prompt},
        ],
        functions=[
            {
                "name": "create_playlist",
                "description": "Creates a spotify playlist based on a list of songs",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "playlist_name": {
                            "type": "string",
                            "description": "Name of playlist"
                        },
                        "playlist_description": {
                            "type": "string",
                            "description": "Description for the playlist. Include that this playlist was generated by AI."
                        },
                        "songs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "songname": {
                                        "type": "string",
                                        "description": "Name of the song"
                                    },
                                    "artists": {
                                        "type": "array",
                                        "description": "List of all artists",
                                        "items": {
                                            "type": "string",
                                            "description": "Name of an artist"
                                        }
                                    }
                                },
                                "required": ["songname", "artists"]
                            }
                        }
                    },
                    "required": ["songs", "playlist_name"]
                }
            }
        ]
    )

    arguments = json.loads(response["choices"][0]["message"]["function_call"]["arguments"])
    playlist_name = "AI - " + arguments["playlist_name"]
    playlist_description = arguments.get("playlist_description", "Generated by AI")
    recommended_songs = arguments["songs"]

    song_uris = []
    for song in recommended_songs:
        uri = search_track_uri(song['songname'], song['artists'])
        if uri:
            song_uris.append(uri)

    return playlist_name, playlist_description, song_uris


#############################################
# Flask App
#############################################
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/choose", methods=["POST"])
def choose():
    option = request.form.get("option")
    if option == '1':
        playlists = get_user_playlists()
        return render_template("choose_option.html", playlists=playlists)
    elif option == '2':
        return render_template("option2_form.html")
    elif option == '3':
        playlists = get_user_playlists()
        return render_template("option3_select_playlist.html", playlists=playlists)
    else:
        return "Invalid choice."

@app.route("/option1", methods=["POST"])
def option1():
    playlist_id = request.form.get("playlist_id")
    action = request.form.get("action")
    new_playlist_name = request.form.get("new_playlist_name", "New Playlist")

    track_data = get_playlist_tracks(playlist_id)

    if action == 'release':
        sorted_ids = sort_by_release_date(track_data)
        pid = create_playlist(new_playlist_name, "Sorted by release date")
        add_tracks_to_playlist(pid, sorted_ids)
        return render_template("success.html", message=f"New playlist created: {new_playlist_name}")
    elif action == 'popularity':
        sorted_ids = sort_by_popularity(track_data)
        pid = create_playlist(new_playlist_name, "Sorted by popularity")
        add_tracks_to_playlist(pid, sorted_ids)
        return render_template("success.html", message=f"New playlist created: {new_playlist_name}")
    elif action == 'genre':
        top_genres = extract_top_genres(track_data)
        return render_template("option1_genre.html", top_genres=top_genres, playlist_id=playlist_id, new_playlist_name=new_playlist_name)
    else:
        return "Invalid action."

@app.route("/option1genre", methods=["POST"])
def option1genre():
    playlist_id = request.form.get("playlist_id")
    new_playlist_name = request.form.get("new_playlist_name", "Genre Filtered Playlist")
    chosen_genres = request.form.get("genres", "")
    chosen_list = [g.strip().lower() for g in chosen_genres.split(',') if g.strip()]

    track_data = get_playlist_tracks(playlist_id)
    filtered_ids = filter_by_genre(track_data, chosen_list)
    pid = create_playlist(new_playlist_name, "Filtered by Genre")
    add_tracks_to_playlist(pid, filtered_ids)
    return render_template("success.html", message=f"New playlist created: {new_playlist_name}")

@app.route("/option2", methods=["POST"])
def option2():
    num_songs = request.form.get("num_songs", "10")
    description = request.form.get("description", "")
    new_playlist_name = request.form.get("new_playlist_name", "AI Playlist")

    try:
        num_songs = int(num_songs)
        if num_songs > 50:
            num_songs = 50
    except:
        num_songs = 10

    playlist_name, playlist_description, song_uris = ask_gpt_for_playlist(num_songs, description)
    if not song_uris:
        return render_template("success.html", message="No tracks found or returned by GPT")

    if new_playlist_name and new_playlist_name.strip():
        playlist_name = new_playlist_name

    playlist_id = create_playlist(playlist_name, description=playlist_description)
    add_tracks_to_playlist(playlist_id, song_uris)
    return render_template("success.html", message=f"New playlist created: {playlist_name}")

@app.route("/option3", methods=["POST"])
def option3():
    playlist_id = request.form.get("playlist_id")
    new_playlist_name = request.form.get("new_playlist_name", "Recommended Playlist")

    track_data = get_playlist_tracks(playlist_id)
    playlist_name, playlist_description, song_uris = analyze_playlist_and_recommend(track_data)
    if not song_uris:
        return render_template("success.html", message="No recommended tracks found")

    if new_playlist_name and new_playlist_name.strip():
        playlist_name = new_playlist_name

    new_pid = create_playlist(playlist_name, description=playlist_description)
    add_tracks_to_playlist(new_pid, song_uris)
    return render_template("success.html", message=f"New playlist created: {playlist_name}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)