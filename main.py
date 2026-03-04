"""
Blackjack Copilot — Web UI
Run: python main.py
"""

import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from engine import GameState
from auth import register_user, login_user

SESSION_SECRET = os.environ.get("SESSION_SECRET", os.urandom(32).hex())

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

game_store: dict[str, GameState] = {}

app.mount("/static", StaticFiles(directory="static"), name="static")


def is_logged_in(request: Request) -> bool:
    return request.session.get("user_id") is not None


def get_username(request: Request) -> str | None:
    return request.session.get("username")


def require_auth(request: Request):
    if not is_logged_in(request):
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    return None


@app.get("/")
async def landing(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/login")
async def login_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/dashboard", status_code=302)
    return FileResponse("static/login.html", headers={"Cache-Control": "no-cache"})


@app.get("/register")
async def register_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/dashboard", status_code=302)
    return FileResponse("static/register.html", headers={"Cache-Control": "no-cache"})


@app.get("/dashboard")
async def dashboard_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("static/dashboard.html", headers={"Cache-Control": "no-cache"})


@app.get("/play")
async def play_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("static/home.html", headers={"Cache-Control": "no-cache"})


@app.get("/game")
async def game_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("static/game.html", headers={"Cache-Control": "no-cache"})


@app.get("/rules")
async def rules_page():
    return FileResponse("static/rules.html", headers={"Cache-Control": "no-cache"})


@app.get("/hilo")
async def hilo_page():
    return FileResponse("static/hilo.html", headers={"Cache-Control": "no-cache"})


@app.post("/api/auth/register")
async def api_register(request: Request):
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    confirm = body.get("confirm_password", "")

    if password != confirm:
        return JSONResponse({"success": False, "error": "Passwords do not match"})

    result = register_user(username, password)
    if result["success"]:
        login_result = login_user(username, password)
        if login_result["success"]:
            request.session["user_id"] = login_result["user_id"]
            request.session["username"] = login_result["username"]
    return JSONResponse(result)


@app.post("/api/auth/login")
async def api_login(request: Request):
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")

    result = login_user(username, password)
    if result["success"]:
        request.session["user_id"] = result["user_id"]
        request.session["username"] = result["username"]
    return JSONResponse(result)


@app.post("/api/auth/logout")
async def api_logout(request: Request):
    request.session.clear()
    return JSONResponse({"success": True})


@app.get("/api/auth/me")
async def api_me(request: Request):
    if is_logged_in(request):
        return JSONResponse({
            "logged_in": True,
            "username": get_username(request)
        })
    return JSONResponse({"logged_in": False})


@app.post("/api/start_session")
async def start_session(request: Request):
    if not is_logged_in(request):
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
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
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
    body = await request.json()
    gid = body.get("game_id")
    gs = game_store.get(gid)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    state = gs.deal_new_hand()
    return JSONResponse(state)


@app.post("/api/reset_shoe")
async def reset_shoe(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
    body = await request.json()
    gid = body.get("game_id")
    gs = game_store.get(gid)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    state = gs.reset_shoe()
    return JSONResponse(state)


@app.post("/api/action")
async def action(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
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
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
    body = await request.json()
    gid = body.get("game_id")
    gs = game_store.get(gid)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    rec = gs._get_recommendation()
    return JSONResponse({"recommendation": rec})


@app.post("/api/auto_step")
async def auto_step(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
    body = await request.json()
    gid = body.get("game_id")
    gs = game_store.get(gid)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    state = gs.auto_step()
    return JSONResponse(state)


@app.post("/api/auto_control")
async def auto_control(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
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
async def get_state(request: Request, game_id: str):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
    gs = game_store.get(game_id)
    if not gs:
        return JSONResponse({"error": "Game not found"}, status_code=404)
    return JSONResponse(gs.get_state())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
