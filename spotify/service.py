import os
import requests
import base64
from dotenv import load_dotenv
import time

load_dotenv()


class SpotifyService:
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
        self.token_url = "https://accounts.spotify.com/api/token"
        self.auth_url = "https://accounts.spotify.com/authorize"
        self.api_base_url = "https://api.spotify.com/v1"
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None

    def get_auth_url(self):
        """Generate Spotify authorization URL"""
        scope = "user-read-currently-playing"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": scope,
            "show_dialog": "true",  # Forces approval prompt every time
        }
        return f"{self.auth_url}?{'&'.join([f'{k}={v}' for k,v in params.items()])}"

    async def exchange_code(self, code: str):
        """Exchange authorization code for tokens"""
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        response = requests.post(self.token_url, headers=headers, data=data)
        response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.refresh_token = token_data["refresh_token"]
        self.token_expires_at = time.time() + token_data["expires_in"]

        return token_data

    async def refresh_access_token(self):
        """Refresh access token using refresh token"""
        if not self.refresh_token:
            raise ValueError("No refresh token available")

        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}

        response = requests.post(self.token_url, headers=headers, data=data)
        response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.token_expires_at = time.time() + token_data["expires_in"]

        # Spotify may return a new refresh token
        if "refresh_token" in token_data:
            self.refresh_token = token_data["refresh_token"]

        return token_data

    async def get_now_playing(self):
        """Get currently playing track"""
        if not self.access_token or time.time() > self.token_expires_at:
            await self.refresh_access_token()

        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(
            f"{self.api_base_url}/me/player/currently-playing", headers=headers
        )

        if response.status_code == 204:
            return {"status": "No track currently playing"}

        response.raise_for_status()
        return response.json()
