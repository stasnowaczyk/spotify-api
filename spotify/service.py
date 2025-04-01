import os
import requests
import base64
from dotenv import load_dotenv
import time
import json

load_dotenv()


class SpotifyService:
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
        self.token_url = "https://accounts.spotify.com/api/token"
        self.auth_url = "https://accounts.spotify.com/authorize"
        self.api_base_url = "https://api.spotify.com/v1"
        self.token_file = "spotify_tokens.json"  # File to store tokens
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None

        # Load existing tokens if available
        self._load_tokens()

    def _save_tokens(self):
        """Save tokens to file for persistence"""
        with open(self.token_file, "w") as f:
            json.dump(
                {
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "token_expires_at": self.token_expires_at,
                },
                f,
            )

    def _load_tokens(self):
        """Load tokens from file"""
        try:
            with open(self.token_file, "r") as f:
                tokens = json.load(f)
                self.access_token = tokens.get("access_token")
                self.refresh_token = tokens.get("refresh_token")
                self.token_expires_at = tokens.get("token_expires_at")
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def get_auth_url(self):
        """Generate Spotify authorization URL with offline access"""
        scope = "user-read-currently-playing"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": scope,
            "access_type": "offline",  # REQUIRED for refresh token
            "show_dialog": "true",
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
        self.refresh_token = token_data.get(
            "refresh_token", self.refresh_token
        )  # Keep existing if not provided
        self.token_expires_at = time.time() + token_data["expires_in"]
        self._save_tokens()

        return token_data

    async def refresh_access_token(self):
        """Refresh access token using refresh token"""
        print("Refreshing access token")
        if not self.refresh_token:
            raise ValueError("No refresh token available. Please re-authenticate.")

        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}

        try:
            response = requests.post(self.token_url, headers=headers, data=data)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.token_expires_at = time.time() + token_data["expires_in"]

            # Spotify may return a new refresh token
            if "refresh_token" in token_data:
                self.refresh_token = token_data["refresh_token"]

            self._save_tokens()
            return token_data

        except requests.exceptions.RequestException as e:
            print(f"Failed to refresh token: {e}")
            raise

    async def get_now_playing(self):
        """Get currently playing track with token management"""

        # If no tokens at all
        if not self.access_token and not self.refresh_token:
            raise ValueError(
                "No authentication tokens available. Please authenticate first."
            )

        # If token expired or about to expire (5 second buffer)
        if not self.access_token or time.time() > (self.token_expires_at - 5):
            try:
                await self.refresh_access_token()
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return {"error": "Authentication required", "status_code": 401}

        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            response = requests.get(
                f"{self.api_base_url}/me/player/currently-playing", headers=headers
            )

            if response.status_code == 204:
                return {"status": "No track currently playing"}

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return {
                "error": str(e),
                "status_code": response.status_code if response else 500,
            }
