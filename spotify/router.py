from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from spotify.service import SpotifyService

router = APIRouter(prefix="/spotify", tags=["spotify"])
service = SpotifyService()


@router.get("/login")
async def login():
    """Redirect to Spotify authorization page"""
    auth_url = service.get_auth_url()
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(request: Request):
    """Handle Spotify callback with authorization code"""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        await service.exchange_code(code)
        return {"status": "Successfully authenticated with Spotify!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/now-playing")
async def now_playing():
    """Get currently playing track"""
    try:
        return await service.get_now_playing()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
