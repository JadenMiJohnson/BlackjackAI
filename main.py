"""
Blackjack Copilot — Web UI
Run: python main.py
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from engine import GameState

app = FastAPI()

game_store: dict[str, GameState] = {}

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html",
                        headers={"Cache-Control": "no-cache"})


@app.post("/api/new_game")
async def new_game():
    gs = GameState()
    game_store[gs.game_id] = gs
    state = gs.deal_new_hand()
    return JSONResponse(state)


@app.post("/api/new_hand")
async def new_hand(request: Request):
    body = await request.json()
    gid = body.get("game_id")
    gs = game_store.get(gid)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    state = gs.deal_new_hand()
    return JSONResponse(state)


@app.post("/api/reset_shoe")
async def reset_shoe(request: Request):
    body = await request.json()
    gid = body.get("game_id")
    gs = game_store.get(gid)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    state = gs.reset_shoe()
    return JSONResponse(state)


@app.post("/api/action")
async def action(request: Request):
    body = await request.json()
    gid = body.get("game_id")
    act = body.get("action", "").lower()
    gs = game_store.get(gid)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    if act not in ("hit", "stand", "double", "split"):
        return JSONResponse({"error": "Invalid action"}, status_code=400)
    state = gs.apply_action(act)
    return JSONResponse(state)


@app.post("/api/recommend")
async def recommend(request: Request):
    body = await request.json()
    gid = body.get("game_id")
    gs = game_store.get(gid)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    rec = gs._get_recommendation()
    return JSONResponse({"recommendation": rec})


@app.get("/api/state")
async def get_state(game_id: str):
    gs = game_store.get(game_id)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    return JSONResponse(gs.get_state())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
