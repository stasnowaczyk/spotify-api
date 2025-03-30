from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from spotify.router import router as spotify_router  # This import is critical

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router with prefix
app.include_router(spotify_router)  # This registers all Spotify endpoints


@app.get("/")
async def root():
    return {"message": "Spotify Now Playing API"}
