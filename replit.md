# Blackjack Copilot

## Overview
Interactive CLI blackjack advisor that uses Monte Carlo simulation on a finite 6-deck shoe to provide real-time recommendations (HIT/STAND/DOUBLE/SPLIT) with computed probabilities and EV.

## Recent Changes
- 2026-02-16: Initial build — full CLI app with Shoe, OddsEngine, hand utilities, dealer policy, and interactive game flow.

## Project Architecture
- **main.py** — Single-file application (Python 3, standard library only)
  - `Shoe` class: tracks card counts, Hi-Lo running/true count, draws
  - `OddsEngine` class: Monte Carlo simulation (50k sims default) for EV and probabilities
  - Hand utilities: totals, soft detection, pair detection
  - Dealer H17 policy
  - Basic strategy fallback for recursive simulation decisions
  - Full CLI flow: new hand → copilot summary → play → dealer resolution → repeat

## Configurable Rules (constants at top of main.py)
- NUM_DECKS = 6
- DEALER_HITS_SOFT_17 = True
- MAX_SPLITS = 3
- SPLIT_ACES_ONE_CARD_ONLY = True
- DOUBLE_AFTER_SPLIT = True
- RESPLIT_ACES = False
- NUM_SIMS = 50,000
- RECURSION_SIMS = 5,000

## How to Run
- Workflow "Blackjack Copilot" runs `python main.py`
- Console-based interactive app

## User Preferences
- Standard library only (no external packages)
- Concise, friendly CLI output
- Math stays behind the scenes; show only key numbers
