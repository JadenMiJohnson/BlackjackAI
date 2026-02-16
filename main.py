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
async def home():
    return FileResponse("static/home.html",
                        headers={"Cache-Control": "no-cache"})


@app.get("/game")
async def game_page():
    return FileResponse("static/game.html",
                        headers={"Cache-Control": "no-cache"})


@app.post("/api/start_session")
async def start_session(request: Request):
    body = await request.json()
    mode = body.get("mode", "regular")
    gs = GameState(
        mode=mode,
        starting_bankroll=body.get("starting_bankroll", 1000),
        min_bet=body.get("min_bet", 10),
        max_units=body.get("max_units", 8),
        n_sims=body.get("n_sims", 5000),
        delay_ms=body.get("delay_ms", 600),
        stop_after_hands=body.get("stop_after_hands", 50),
        stop_on_bankrupt=body.get("stop_on_bankrupt", True),
    )
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


@app.post("/api/auto_step")
async def auto_step(request: Request):
    body = await request.json()
    gid = body.get("game_id")
    gs = game_store.get(gid)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    state = gs.auto_step()
    return JSONResponse(state)


@app.post("/api/auto_control")
async def auto_control(request: Request):
    body = await request.json()
    gid = body.get("game_id")
    action = body.get("control", "")
    gs = game_store.get(gid)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    if action == "start":
        gs.autoplay_active = True
        gs.session_stopped = False
        gs.stop_reason = None
    elif action == "pause":
        gs.autoplay_active = False
    elif action == "stop":
        gs.autoplay_active = False
        gs.session_stopped = True
        gs.stop_reason = "Stopped by user"
    return JSONResponse(gs.get_state())


@app.get("/api/state")
async def get_state(game_id: str):
    gs = game_store.get(game_id)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    return JSONResponse(gs.get_state())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
