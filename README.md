# Spotify Playlist Sorter

A Flask-based web app for creating and managing Spotify playlists. Sort playlists by various criteria, generate new ones using GPT, or analyze and get recommendations.

---

## Features
- **Sort Existing Playlists**: By release date or popularity.
- **Filter by Genre**: Extract tracks based on genre.
- **Generate Playlists via Prompt**: Use GPT to create playlists from a description.
- **Analyze and Recommend**: Analyze a playlist and get 20 recommended tracks to form a new one.

---

## Requirements
- **Python 3.5+**
- **Spotify API Credentials**: Get a Client ID and Secret from [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
- **OpenAI API Key**: Obtain an API key from [OpenAI](https://openai.com/).
- **Python Libraries**: Flask, Spotipy, Requests, OpenAI Python Library.

---

## Installation
1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/playlist_sorter.git
   cd playlist_sorter
   ```

2. **Set up a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install flask spotipy openai requests
   ```

4. *(Optional)* Use a `requirements.txt` file:
   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration
1. Create a `.env` file in the project directory and add your credentials:
   ```env
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
   OPENAI_API_KEY=your_openai_api_key
   ```

2. Ensure `.env` is listed in `.gitignore` to keep your credentials secure.

---

## Running the App
1. **Activate your virtual environment** (if not already activated):
   ```bash
   source venv/bin/activate
   ```

2. **Run the Flask app**:
   ```bash
   python app.py
   ```

3. **Access the app**: Open [http://localhost:5000](http://localhost:5000) in your web browser.

---

## Usage Guide
### From the Home Page:
1. **Sort Playlists**:
   - Choose an existing playlist.
   - Sort by release date, popularity, or filter by genre.

2. **Generate Playlists**:
   - Enter a description (e.g., "relaxing jazz for evenings").
   - GPT creates a new playlist.

3. **Analyze Playlists**:
   - Select a playlist.
   - Analyze and get 20 recommended tracks to create a new playlist.

Follow on-screen instructions. You may need to log into Spotify and authorise the app.

---

