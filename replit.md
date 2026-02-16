# Blackjack Copilot

## Overview
Web-based blackjack advisor with two modes: Regular (interactive play with AI guidance) and Auto Play (AI plays autonomously). Uses Monte Carlo simulation on a finite 6-deck shoe to provide EV-based recommendations, card counting, and dynamic bet sizing.

## Recent Changes
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

- **main.py** — FastAPI web server
  - `POST /api/start_session` — Create game with mode/settings
  - `POST /api/new_hand` — Deal new hand
  - `POST /api/action` — Player action (hit/stand/double/split)
  - `POST /api/recommend` — Get Monte Carlo recommendation (async)
  - `POST /api/auto_step` — Single AI step for auto-play
  - `POST /api/auto_control` — Start/pause/stop auto-play
  - `POST /api/reset_shoe` — Reset shoe and stats
  - `GET /api/state` — Get current game state
  - `GET /` — Home page
  - `GET /game` — Game page

### Frontend
- **static/home.html** — Landing page with mode selection and settings
- **static/game.html** — Game page with cards, controls, panels
- **static/app.js** — Frontend logic, API calls, rendering, auto-play loop
- **static/styles.css** — Dark theme with GitHub-inspired colors

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
- Workflow "Blackjack Copilot" runs `python main.py`
- Web app at http://0.0.0.0:5000

## User Preferences
- Uses FastAPI + standard library for engine
- Concise, friendly UI output
- Math behind the scenes; show only key numbers
- Dark theme with card table aesthetic
