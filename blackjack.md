# Agent B21

## Overview
Web-based blackjack advisor with two modes: Regular (interactive play with AI guidance) and Auto Play (AI plays autonomously). Uses Monte Carlo simulation on a finite 6-deck shoe to provide EV-based recommendations, card counting, and dynamic bet sizing. Includes user authentication, informational pages, and a dashboard.

## Recent Changes
- 2026-03-04: Added login/register system with SQLite + werkzeug password hashing, session-based auth, dashboard, blackjack rules page, Hi-Lo card counting page, navbar on all pages, protected game routes
- 2026-02-16: Added home page with mode selection, session settings, bankroll management, auto-play mode, session stats, and polished UI
- 2026-02-16: Converted CLI app to web app with FastAPI backend and modern frontend
- 2026-02-16: Initial build — full CLI app with Shoe, OddsEngine, hand utilities, dealer policy, and interactive game flow

## Project Architecture

### Backend
- **engine.py** — Game logic, Monte Carlo simulation, state management
  - `Shoe`: 6-deck shoe with Hi-Lo card counting (running/true count)
  - `OddsEngine`: Monte Carlo EV/probability simulation (configurable sims)
  - `HandState`: Individual hand state with cards, status, stake
  - `GameState`: Full game session with bankroll, betting, stats, auto-play
  - `compute_bet()`: Dynamic bet sizing based on true count ramp
  - Basic strategy fallback for simulation decisions
  - Dealer H17 policy

- **auth.py** — Authentication module
  - SQLite database (users.db) auto-created on startup
  - `register_user()`: Create account with werkzeug password hashing
  - `login_user()`: Verify credentials against hashed password
  - `init_db()`: Auto-creates users table on import

- **main.py** — FastAPI web server with session middleware
  - Auth routes: `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`
  - Page routes: `/login`, `/register`, `/dashboard`, `/play`, `/game`, `/rules`, `/hilo`
  - Game API: `/api/start_session`, `/api/new_hand`, `/api/action`, `/api/recommend`, `/api/auto_step`, `/api/auto_control`, `/api/reset_shoe`, `/api/state`
  - Protected routes: `/dashboard`, `/play`, `/game`, `/api/start_session` require login
  - Public routes: `/login`, `/register`, `/rules`, `/hilo`
  - `/` redirects to `/dashboard` if logged in, `/login` if not

### Frontend
- **static/login.html** — Login page
- **static/register.html** — Registration page
- **static/dashboard.html** — User dashboard with links to Play, Rules, Hi-Lo
- **static/home.html** — Play page with mode selection and settings (was original home)
- **static/game.html** — Game page with cards, controls, panels
- **static/rules.html** — Blackjack rules informational page
- **static/hilo.html** — Hi-Lo card counting explanation page
- **static/nav.js** — Dynamic navbar (shows login/register or dashboard/logout based on auth)
- **static/app.js** — Game frontend logic, API calls, rendering, auto-play loop
- **static/styles.css** — Dark theme with GitHub-inspired colors

## Dependencies
- FastAPI + Uvicorn (web server)
- Werkzeug (password hashing)
- itsdangerous (session cookies via Starlette SessionMiddleware)
- python-multipart (form handling)
- SQLite3 (built-in, user storage)

## Rules & Configuration (constants in engine.py)
- NUM_DECKS = 6
- DEALER_HITS_SOFT_17 = True
- MAX_SPLITS = 3
- SPLIT_ACES_ONE_CARD_ONLY = True
- DOUBLE_AFTER_SPLIT = True
- RESPLIT_ACES = False
- DEFAULT_SIMS = 5,000

## Betting Model (Stake-at-Risk)
- Bet deducted from bankroll when placed
- Win: bankroll += 2 * stake (return stake + profit)
- Push: bankroll += stake (return stake)
- Loss: bankroll += 0 (stake already deducted)
- Double/Split require full additional stake from bankroll

## True Count Bet Ramp
- TC <= 0: 1 unit
- TC 1: 2 units
- TC 2: 4 units
- TC 3+: 6 units
- Capped at max_units setting

## How to Run
- Workflow "Agent B21" runs `python main.py`
- Web app at http://0.0.0.0:5000
- Visit `/` to get started (redirects to login or dashboard)
- Register an account, then access the game via Dashboard > Play Blackjack

## User Preferences
- Uses FastAPI + standard library for engine
- Concise, friendly UI output
- Math behind the scenes; show only key numbers
- Dark theme with card table aesthetic
