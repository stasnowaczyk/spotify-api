from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from spotify.router import router as spotify_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router with prefix
app.include_router(spotify_router)  # This registers all Spotify endpoints


@app.get("/")
async def root():
    return {"message": "Spotify Now Playing API"}
