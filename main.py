from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = FastAPI()

# Spotify constants
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = "http://localhost:8000/callback" 
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"

# Define the scopes your app needs
SCOPES = "user-read-private user-read-email"

@app.get("/login")
def login():
    """
    Step 1: Redirect the user to the Spotify authorization page.
    The user logs in and grants permissions to your app.
    """
    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SCOPES
    }
    # Build the URL with query parameters
    query_params = "&".join([f"{key}={value}" for key, value in params.items()])
    auth_url = f"{SPOTIFY_AUTH_URL}?{query_params}"
    # Redirect the user to Spotify's authorization page
    return RedirectResponse(auth_url)

@app.get("/callback")
def callback(request: Request):
    """
    Step 2: Spotify redirects back here with an authorization code.
    We exchange that code for an access token (and possibly a refresh token).
    """
    # Retrieve 'code' from the query parameters
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error": "Authorization code not found"}, status_code=400)

    # Prepare data for token exchange
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }

    # Request access token from Spotify
    response = requests.post(SPOTIFY_TOKEN_URL, data=token_data)
    token_info = response.json()

    # Check if the token was successfully received
    if "access_token" not in token_info:
        return JSONResponse({"error": "Failed to get access token"}, status_code=400)

    # In production, you might store tokens in a database or session.
    # For demonstration, we return them directly.
    return JSONResponse(token_info)

@app.get("/profile")
def get_profile(access_token: str):
    """
    Step 3: Use the access token to call the Spotify Web API and retrieve the user's profile.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{SPOTIFY_API_BASE_URL}/me", headers=headers)
    return response.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
