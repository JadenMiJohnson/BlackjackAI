#!/usr/bin/env python3
"""
Blackjack Copilot — Interactive CLI advisor for blackjack hands.

Uses Monte Carlo simulation on a finite 6-deck shoe to compute:
  - EV and win/push/lose probabilities for every legal action
  - Hi-Lo running count, true count, and decks remaining
  - A clear recommendation with a short numeric explanation

Subsequent decisions in simulation use a basic-strategy fallback policy
(documented below) for performance.  All simulations draw from the finite
shoe without replacement.

Standard library only.  No external packages required.
"""

import random
import time
import sys

# ─────────────────────────── Configurable Rule Flags ──────────────────────────
NUM_DECKS = 6
DEALER_HITS_SOFT_17 = True
MAX_SPLITS = 3                      # up to 4 total hands
SPLIT_ACES_ONE_CARD_ONLY = True
DOUBLE_AFTER_SPLIT = True
RESPLIT_ACES = False
DOUBLE_ONLY_ON_FIRST_TWO = True

NUM_SIMS = 50_000
SEED_BASE = 42

# ─────────────────────────── Card Constants ───────────────────────────────────
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11
}
HILO = {
    '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
    '7': 0, '8': 0, '9': 0,
    '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
}


def parse_rank(s):
    s = s.strip()
    up = s.upper()
    if up == 'T' or s == '10':
        return '10'
    if len(s) == 1:
        c = up
        for r in RANKS:
            if r == c:
                return r
    return None


# ─────────────────────────── Shoe Class ───────────────────────────────────────
class Shoe:
    def __init__(self, num_decks=NUM_DECKS):
        self.num_decks = num_decks
        self.counts = {}
        for r in RANKS:
            self.counts[r] = 4 * num_decks
        self.running_count = 0

    def copy(self):
        s = Shoe.__new__(Shoe)
        s.num_decks = self.num_decks
        s.counts = dict(self.counts)
        s.running_count = self.running_count
        return s

    @property
    def cards_remaining(self):
        return sum(self.counts.values())

    @property
    def decks_remaining(self):
        return self.cards_remaining / 52.0

    @property
    def true_count(self):
        dr = max(self.decks_remaining, 0.25)
        return self.running_count / dr

    def validate_available(self, rank):
        return self.counts.get(rank, 0) > 0

    def remove_known(self, rank):
        if self.counts.get(rank, 0) <= 0:
            raise ValueError(f"No '{rank}' left in shoe")
        self.counts[rank] -= 1
        self.running_count += HILO[rank]

    def draw_random(self, rng):
        total = self.cards_remaining
        if total <= 0:
            raise ValueError("Shoe is empty")
        idx = rng.randint(0, total - 1)
        cumulative = 0
        for r in RANKS:
            cumulative += self.counts[r]
            if idx < cumulative:
                self.counts[r] -= 1
                self.running_count += HILO[r]
                return r
        raise RuntimeError("draw_random failed")


# ─────────────────────────── Hand Utilities ───────────────────────────────────
def hand_total(cards):
    total = 0
    aces = 0
    for c in cards:
        v = RANK_VALUES[c]
        if c == 'A':
            aces += 1
        total += v
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    soft = aces > 0 and total <= 21
    return total, soft


def is_pair(cards):
    if len(cards) != 2:
        return False
    return cards[0] == cards[1]


def compare_hands(player_total, dealer_total):
    if player_total > 21:
        return -1
    if dealer_total > 21:
        return 1
    if player_total > dealer_total:
        return 1
    if player_total == dealer_total:
        return 0
    return -1


# ─────────────────────────── Dealer Policy ────────────────────────────────────
def play_dealer_h17(shoe, dealer_cards, rng):
    cards = list(dealer_cards)
    while True:
        t, soft = hand_total(cards)
        if t > 21:
            break
        if t < 17:
            cards.append(shoe.draw_random(rng))
            continue
        if t == 17 and soft and DEALER_HITS_SOFT_17:
            cards.append(shoe.draw_random(rng))
            continue
        break
    return cards


# ──────────── Basic-Strategy Fallback (used inside simulations) ───────────────
# This is a well-known approximate strategy used as the decision policy for
# subsequent player actions inside Monte Carlo rollouts.  The top-level
# decision the user sees is always driven by full simulation comparison.

def basic_strategy_action(player_cards, dealer_up, can_double, can_split):
    t, soft = hand_total(player_cards)
    if can_split and is_pair(player_cards):
        r = player_cards[0]
        v = RANK_VALUES[r]
        if r == 'A':
            return 'SPLIT'
        if v == 8:
            return 'SPLIT'
        dv = RANK_VALUES[dealer_up]
        if v in (2, 3, 7) and dv <= 7:
            return 'SPLIT'
        if v == 6 and dv <= 6:
            return 'SPLIT'
        if v == 4 and dv in (5, 6):
            return 'SPLIT'
        if v == 9 and dv not in (7, 10, 11):
            return 'SPLIT'
    if soft:
        if t >= 19:
            return 'STAND'
        dv = RANK_VALUES[dealer_up]
        if t == 18:
            if can_double and dv in (3, 4, 5, 6):
                return 'DOUBLE'
            if dv >= 9:
                return 'HIT'
            return 'STAND'
        if t == 17:
            if can_double and dv in (3, 4, 5, 6):
                return 'DOUBLE'
            return 'HIT'
        if t in (15, 16):
            if can_double and dv in (4, 5, 6):
                return 'DOUBLE'
            return 'HIT'
        if t in (13, 14):
            if can_double and dv in (5, 6):
                return 'DOUBLE'
            return 'HIT'
        return 'HIT'
    else:
        if t >= 17:
            return 'STAND'
        dv = RANK_VALUES[dealer_up]
        if t >= 13 and dv <= 6:
            return 'STAND'
        if t >= 13:
            return 'HIT'
        if t == 12 and dv in (4, 5, 6):
            return 'STAND'
        if t == 12:
            return 'HIT'
        if t == 11:
            return 'DOUBLE' if can_double else 'HIT'
        if t == 10:
            return 'DOUBLE' if (can_double and dv <= 9) else 'HIT'
        if t == 9 and can_double and dv in (3, 4, 5, 6):
            return 'DOUBLE'
        return 'HIT'


# ─────────────────────── Simulation Helpers ───────────────────────────────────

def sim_play_hand_bs(shoe, player_cards, dealer_up, rng,
                     is_split_hand=False, split_depth=0, is_aces=False):
    """
    Play out a player hand using basic-strategy fallback.
    Returns (final_cards, was_doubled).
    Respects split rules: aces one-card-only, double-after-split, resplit.
    """
    cards = list(player_cards)

    if is_aces and SPLIT_ACES_ONE_CARD_ONLY:
        return cards, False

    while True:
        t, _ = hand_total(cards)
        if t >= 21:
            break
        can_double = (len(cards) == 2) and DOUBLE_ONLY_ON_FIRST_TWO
        if is_split_hand and not DOUBLE_AFTER_SPLIT:
            can_double = False
        can_split = (is_pair(cards) and split_depth < MAX_SPLITS
                     and (not is_aces or RESPLIT_ACES))
        action = basic_strategy_action(cards, dealer_up, can_double, can_split)
        if action == 'DOUBLE':
            cards.append(shoe.draw_random(rng))
            return cards, True
        elif action == 'HIT':
            cards.append(shoe.draw_random(rng))
        elif action == 'SPLIT':
            break
        else:
            break
    return cards, False


def sim_play_split_hands(shoe, split_rank, dealer_up, rng, split_depth=1):
    """
    Recursively handle split hands.  Returns list of (player_total, stake)
    where stake is 1 (normal) or 2 (doubled).
    """
    is_aces = (split_rank == 'A')
    results = []
    for _ in range(2):
        new_card = shoe.draw_random(rng)
        sub_cards = [split_rank, new_card]

        if (is_pair(sub_cards) and split_depth < MAX_SPLITS
                and (not is_aces or RESPLIT_ACES)):
            action = basic_strategy_action(sub_cards, dealer_up,
                                           can_double=False, can_split=True)
            if action == 'SPLIT':
                sub_results = sim_play_split_hands(
                    shoe, split_rank, dealer_up, rng, split_depth + 1)
                results.extend(sub_results)
                continue

        final, doubled = sim_play_hand_bs(
            shoe, sub_cards, dealer_up, rng,
            is_split_hand=True, split_depth=split_depth, is_aces=is_aces)
        pt, _ = hand_total(final)
        stake = 2 if doubled else 1
        results.append((pt, stake))

    return results


def sim_stand(shoe, player_cards, dealer_up, dealer_hole, rng):
    pt, _ = hand_total(player_cards)
    dealer_cards = play_dealer_h17(shoe, [dealer_up, dealer_hole], rng)
    dt, _ = hand_total(dealer_cards)
    return compare_hands(pt, dt)


def sim_hit(shoe, player_cards, dealer_up, dealer_hole, rng):
    card = shoe.draw_random(rng)
    new_hand = list(player_cards) + [card]
    t, _ = hand_total(new_hand)
    if t > 21:
        return -1
    final, doubled = sim_play_hand_bs(shoe, new_hand, dealer_up, rng)
    pt, _ = hand_total(final)
    if pt > 21:
        return -1
    dealer_cards = play_dealer_h17(shoe, [dealer_up, dealer_hole], rng)
    dt, _ = hand_total(dealer_cards)
    r = compare_hands(pt, dt)
    return r * (2 if doubled else 1)


def sim_double(shoe, player_cards, dealer_up, dealer_hole, rng):
    card = shoe.draw_random(rng)
    new_hand = list(player_cards) + [card]
    pt, _ = hand_total(new_hand)
    if pt > 21:
        return -2
    dealer_cards = play_dealer_h17(shoe, [dealer_up, dealer_hole], rng)
    dt, _ = hand_total(dealer_cards)
    return compare_hands(pt, dt) * 2


def sim_split(shoe, player_cards, dealer_up, dealer_hole, rng):
    split_rank = player_cards[0]
    hand_results = sim_play_split_hands(shoe, split_rank, dealer_up, rng, split_depth=1)
    dealer_cards = play_dealer_h17(shoe, [dealer_up, dealer_hole], rng)
    dt, _ = hand_total(dealer_cards)
    total_ev = 0
    for pt, stake in hand_results:
        if pt > 21:
            total_ev -= stake
        else:
            r = compare_hands(pt, dt)
            total_ev += r * stake
    return total_ev


# ─────────────────────── OddsEngine ───────────────────────────────────────────
class OddsEngine:
    def __init__(self, n_sims=NUM_SIMS, seed=SEED_BASE):
        self.n_sims = n_sims
        self.seed = seed

    def simulate_action(self, shoe, player_cards, dealer_up, action, n_sims=None):
        if n_sims is None:
            n_sims = self.n_sims
        rng = random.Random(self.seed)
        wins = 0
        pushes = 0
        losses = 0
        total_ev = 0.0
        for i in range(n_sims):
            rng.seed(self.seed + i * 13 + hash(action) % 9973)
            sim_shoe = shoe.copy()
            hole = sim_shoe.draw_random(rng)
            if action == 'STAND':
                result = sim_stand(sim_shoe, player_cards, dealer_up, hole, rng)
            elif action == 'HIT':
                result = sim_hit(sim_shoe, player_cards, dealer_up, hole, rng)
            elif action == 'DOUBLE':
                result = sim_double(sim_shoe, player_cards, dealer_up, hole, rng)
            elif action == 'SPLIT':
                result = sim_split(sim_shoe, player_cards, dealer_up, hole, rng)
            else:
                result = 0
            total_ev += result
            if result > 0:
                wins += 1
            elif result == 0:
                pushes += 1
            else:
                losses += 1
        ev = total_ev / n_sims
        pw = wins / n_sims
        pp = pushes / n_sims
        pl = losses / n_sims
        return ev, pw, pp, pl

    def compute_bust_prob(self, shoe, player_cards, n_sims=None):
        if n_sims is None:
            n_sims = min(self.n_sims, 20000)
        rng = random.Random(self.seed + 7)
        busts = 0
        for i in range(n_sims):
            rng.seed(self.seed + 7 + i)
            sim_shoe = shoe.copy()
            card = sim_shoe.draw_random(rng)
            t, _ = hand_total(list(player_cards) + [card])
            if t > 21:
                busts += 1
        return busts / n_sims

    def compute_dealer_bust_prob(self, shoe, dealer_up, n_sims=None):
        if n_sims is None:
            n_sims = min(self.n_sims, 20000)
        rng = random.Random(self.seed + 11)
        busts = 0
        for i in range(n_sims):
            rng.seed(self.seed + 11 + i)
            sim_shoe = shoe.copy()
            hole = sim_shoe.draw_random(rng)
            dealer_cards = play_dealer_h17(sim_shoe, [dealer_up, hole], rng)
            t, _ = hand_total(dealer_cards)
            if t > 21:
                busts += 1
        return busts / n_sims

    def full_analysis(self, shoe, player_cards, dealer_up,
                      can_double=True, can_split=False, n_sims=None):
        if n_sims is None:
            n_sims = self.n_sims
        actions = ['HIT', 'STAND']
        if can_double:
            actions.append('DOUBLE')
        if can_split:
            actions.append('SPLIT')
        results = {}
        for action in actions:
            ev, pw, pp, pl = self.simulate_action(
                shoe, player_cards, dealer_up, action, n_sims)
            results[action] = {'ev': ev, 'p_win': pw, 'p_push': pp, 'p_lose': pl}
        bust_prob = self.compute_bust_prob(shoe, player_cards, min(n_sims, 20000))
        dealer_bust = self.compute_dealer_bust_prob(shoe, dealer_up, min(n_sims, 20000))
        best_action = max(results, key=lambda a: results[a]['ev'])
        evs_sorted = sorted(results.items(), key=lambda x: -x[1]['ev'])
        ev_gap = 0.0
        if len(evs_sorted) >= 2:
            ev_gap = evs_sorted[0][1]['ev'] - evs_sorted[1][1]['ev']
        return {
            'actions': results,
            'best': best_action,
            'bust_if_hit': bust_prob,
            'dealer_bust': dealer_bust,
            'ev_gap': ev_gap
        }


# ─────────────────────────── Display Helpers ──────────────────────────────────
def card_display(cards):
    return ' '.join(cards)

def format_pct(v):
    return f"{v*100:.1f}%"

def format_ev(v):
    return f"{v:+.4f}"

def print_copilot(shoe, player_cards, dealer_up, analysis, elapsed, hand_label=None):
    print()
    print("=" * 60)
    label = "COPILOT SUMMARY"
    if hand_label:
        label += f" — {hand_label}"
    print(f"  {label}")
    print("=" * 60)
    t, soft = hand_total(player_cards)
    soft_str = " (soft)" if soft else ""
    print(f"  Dealer up-card : {dealer_up}")
    print(f"  Your hand      : {card_display(player_cards)}  =  {t}{soft_str}")
    print(f"  Running count  : {shoe.running_count:+d}")
    print(f"  Decks remaining: {shoe.decks_remaining:.2f}")
    print(f"  True count     : {shoe.true_count:+.1f}")
    print()
    has_split = 'SPLIT' in analysis['actions']
    has_double = 'DOUBLE' in analysis['actions']
    print(f"  {'Action':<8} {'Win':>7} {'Push':>7} {'Lose':>7} {'EV':>9}")
    print(f"  {'-'*8} {'-'*7} {'-'*7} {'-'*7} {'-'*9}")
    best = analysis['best']
    for action in ('HIT', 'STAND', 'DOUBLE', 'SPLIT'):
        if action not in analysis['actions']:
            continue
        d = analysis['actions'][action]
        marker = " <--" if action == best else ""
        print(f"  {action:<8} {format_pct(d['p_win']):>7} {format_pct(d['p_push']):>7} "
              f"{format_pct(d['p_lose']):>7} {format_ev(d['ev']):>9}{marker}")
    if has_split or has_double:
        notes = []
        if has_double:
            notes.append("DOUBLE EV reflects 2x stake")
        if has_split:
            notes.append("SPLIT shows net outcome across hands")
        print(f"  ({'; '.join(notes)})")
    print()
    best_ev = analysis['actions'][best]['ev']
    bust_str = format_pct(analysis['bust_if_hit'])
    db_str = format_pct(analysis['dealer_bust'])
    gap_str = format_ev(analysis['ev_gap'])
    print(f"  >> Recommendation: {best}")
    parts = [f"EV={format_ev(best_ev)}"]
    parts.append(f"bust risk if hit={bust_str}")
    parts.append(f"dealer bust={db_str}")
    if analysis['ev_gap'] > 0:
        parts.append(f"EV edge over next best={gap_str}")
    print(f"     Why: {', '.join(parts)}")
    print(f"  (computed in {elapsed:.1f}s, seed={SEED_BASE})")
    print("=" * 60)
    print()


# ─────────────────────────── CLI Functions ────────────────────────────────────
def prompt_card(shoe, prompt_text):
    while True:
        raw = input(prompt_text).strip()
        if not raw:
            continue
        rank = parse_rank(raw)
        if rank is None:
            print(f"  Invalid card '{raw}'. Use A,K,Q,J,T/10,9,8,...,2")
            continue
        if not shoe.validate_available(rank):
            print(f"  No '{rank}' left in the shoe. Try again.")
            continue
        shoe.remove_known(rank)
        return rank


def prompt_action(legal_actions):
    mapping = {}
    for a in legal_actions:
        mapping[a[0].upper()] = a
        mapping[a.upper()] = a
    options = '/'.join(legal_actions)
    while True:
        raw = input(f"  Your action ({options}): ").strip().upper()
        if raw in mapping:
            return mapping[raw]
        print(f"  Invalid. Choose one of: {options}")


def resolve_dealer(shoe, dealer_up):
    print("\n  -- Dealer's turn --")
    hole = prompt_card(shoe, "  Enter dealer hole card: ")
    dealer_cards = [dealer_up, hole]
    dt, dsoft = hand_total(dealer_cards)
    print(f"  Dealer has: {card_display(dealer_cards)} = {dt}"
          f"{' (soft)' if dsoft else ''}")
    while True:
        dt, dsoft = hand_total(dealer_cards)
        if dt > 21:
            print(f"  Dealer busts with {dt}!")
            break
        must_hit = dt < 17 or (dt == 17 and dsoft and DEALER_HITS_SOFT_17)
        if not must_hit:
            print(f"  Dealer stands on {dt}.")
            break
        print(f"  Dealer must hit ({dt}{' soft' if dsoft else ''}).")
        c = prompt_card(shoe, "  Enter dealer's next card: ")
        dealer_cards.append(c)
        dt, dsoft = hand_total(dealer_cards)
        print(f"  Dealer has: {card_display(dealer_cards)} = {dt}"
              f"{' (soft)' if dsoft else ''}")
    return dealer_cards


def play_single_hand(shoe, player_cards, dealer_up, engine, hand_label=None,
                     is_split_hand=False, split_aces=False):
    """
    Play out one player hand interactively.
    Returns (final_cards, was_doubled).
    """
    doubled = False

    if split_aces and SPLIT_ACES_ONE_CARD_ONLY:
        t, s = hand_total(player_cards)
        print(f"  {hand_label or 'Hand'}: {card_display(player_cards)}"
              f" = {t}{' (soft)' if s else ''}")
        print("  (Split aces — one card only, must stand)")
        return player_cards, False

    while True:
        t, soft = hand_total(player_cards)
        if t > 21:
            print(f"  Bust! {card_display(player_cards)} = {t}")
            return player_cards, doubled
        if t == 21:
            print(f"  {card_display(player_cards)} = 21!")
            return player_cards, doubled

        can_double = (len(player_cards) == 2) and DOUBLE_ONLY_ON_FIRST_TWO
        if is_split_hand and not DOUBLE_AFTER_SPLIT:
            can_double = False
        can_split_now = False

        start = time.time()
        analysis = engine.full_analysis(shoe, player_cards, dealer_up,
                                        can_double=can_double,
                                        can_split=can_split_now)
        elapsed = time.time() - start
        print_copilot(shoe, player_cards, dealer_up, analysis, elapsed, hand_label)

        legal = ['HIT', 'STAND']
        if can_double:
            legal.append('DOUBLE')

        action = prompt_action(legal)

        if action == 'STAND':
            return player_cards, doubled
        elif action == 'HIT':
            c = prompt_card(shoe, "  Enter your next card: ")
            player_cards = list(player_cards) + [c]
        elif action == 'DOUBLE':
            c = prompt_card(shoe, "  Enter your double-down card: ")
            player_cards = list(player_cards) + [c]
            doubled = True
            t, _ = hand_total(player_cards)
            if t > 21:
                print(f"  Bust on double! {card_display(player_cards)} = {t}")
            else:
                print(f"  Doubled: {card_display(player_cards)} = {t} (must stand)")
            return player_cards, doubled

    return player_cards, doubled


def outcome_str(result):
    if result > 0:
        return "WIN"
    elif result == 0:
        return "PUSH"
    else:
        return "LOSE"


def run_hand(shoe, engine):
    print("\n" + "─" * 60)
    print("  NEW HAND")
    print("─" * 60)

    dealer_up = prompt_card(shoe, "  Dealer up-card: ")
    c1 = prompt_card(shoe, "  Your first card: ")
    c2 = prompt_card(shoe, "  Your second card: ")
    player_cards = [c1, c2]

    can_double = DOUBLE_ONLY_ON_FIRST_TWO and (len(player_cards) == 2)
    can_split = is_pair(player_cards)

    start = time.time()
    analysis = engine.full_analysis(shoe, player_cards, dealer_up,
                                    can_double=can_double,
                                    can_split=can_split)
    elapsed = time.time() - start
    print_copilot(shoe, player_cards, dealer_up, analysis, elapsed)

    legal = ['HIT', 'STAND']
    if can_double:
        legal.append('DOUBLE')
    if can_split:
        legal.append('SPLIT')

    action = prompt_action(legal)

    if action == 'SPLIT':
        handle_split(shoe, player_cards, dealer_up, engine)
    elif action == 'STAND':
        dealer_cards = resolve_dealer(shoe, dealer_up)
        dt, _ = hand_total(dealer_cards)
        pt, _ = hand_total(player_cards)
        r = compare_hands(pt, dt)
        print(f"\n  Result: {card_display(player_cards)} ({pt}) vs Dealer ({dt})"
              f" → {outcome_str(r)} ({r:+d} units)")
    elif action == 'HIT':
        c = prompt_card(shoe, "  Enter your next card: ")
        player_cards = list(player_cards) + [c]
        final_cards, doubled = play_single_hand(
            shoe, player_cards, dealer_up, engine)
        pt, _ = hand_total(final_cards)
        if pt > 21:
            stake = 2 if doubled else 1
            print(f"\n  Result: BUST → LOSE ({-stake:+d} units)")
        else:
            dealer_cards = resolve_dealer(shoe, dealer_up)
            dt, _ = hand_total(dealer_cards)
            r = compare_hands(pt, dt)
            stake = 2 if doubled else 1
            net = r * stake
            print(f"\n  Result: {card_display(final_cards)} ({pt}) vs Dealer ({dt})"
                  f" → {outcome_str(r)} ({net:+d} units)")
    elif action == 'DOUBLE':
        c = prompt_card(shoe, "  Enter your double-down card: ")
        player_cards = list(player_cards) + [c]
        pt, _ = hand_total(player_cards)
        if pt > 21:
            print(f"  Bust on double! {card_display(player_cards)} = {pt}")
            print(f"\n  Result: BUST → LOSE (-2 units)")
        else:
            print(f"  Doubled: {card_display(player_cards)} = {pt} (must stand)")
            dealer_cards = resolve_dealer(shoe, dealer_up)
            dt, _ = hand_total(dealer_cards)
            r = compare_hands(pt, dt)
            net = r * 2
            print(f"\n  Result: {card_display(player_cards)} ({pt}) vs Dealer ({dt})"
                  f" → {outcome_str(r)} ({net:+d} units)")


def handle_split(shoe, player_cards, dealer_up, engine):
    """Handle interactive split play, including support for resplits.
    Each pending entry tracks (cards, label_num, split_depth, hand_is_aces).
    split_depth starts at 1 for the first split; MAX_SPLITS limits further splits.
    """
    split_rank = player_cards[0]
    orig_aces = (split_rank == 'A')

    print(f"\n  Splitting {split_rank}/{split_rank}...")
    c1 = prompt_card(shoe, "  Card dealt to Hand 1: ")
    c2 = prompt_card(shoe, "  Card dealt to Hand 2: ")
    pending = [
        ([split_rank, c1], 1, 1, orig_aces),
        ([split_rank, c2], 2, 1, orig_aces),
    ]

    hand_number = 2
    completed_hands = []

    while pending:
        cards, label_num, depth, hand_aces = pending.pop(0)
        label = f"Hand {label_num}"

        pair_rank = cards[0] if is_pair(cards) else None
        this_is_aces = (pair_rank == 'A') if pair_rank else False
        can_resplit = (pair_rank is not None
                       and depth < MAX_SPLITS
                       and (not this_is_aces or RESPLIT_ACES))
        if can_resplit:
            t, s = hand_total(cards)
            print(f"\n  {label}: {card_display(cards)} = {t}{' (soft)' if s else ''}")
            print(f"  Another pair! You may resplit.")
            choice = input(f"  Resplit {label}? (Y/N): ").strip().upper()
            if choice in ('Y', 'YES'):
                hand_number += 1
                hn_a = hand_number
                hand_number += 1
                hn_b = hand_number
                print(f"  Resplitting {label}...")
                ca = prompt_card(shoe, f"  Card dealt to Hand {hn_a}: ")
                cb = prompt_card(shoe, f"  Card dealt to Hand {hn_b}: ")
                pending.insert(0, ([pair_rank, ca], hn_a, depth + 1, this_is_aces))
                pending.insert(1, ([pair_rank, cb], hn_b, depth + 1, this_is_aces))
                continue

        final, doubled = play_single_hand(
            shoe, cards, dealer_up, engine,
            hand_label=label, is_split_hand=True, split_aces=hand_aces)
        completed_hands.append((final, doubled, label))

    dealer_cards = resolve_dealer(shoe, dealer_up)
    dt, _ = hand_total(dealer_cards)

    print("\n  ── RESULTS ──")
    for hcards, hdbl, hlabel in completed_hands:
        pt, _ = hand_total(hcards)
        if pt > 21:
            r = -1
        else:
            r = compare_hands(pt, dt)
        stake = 2 if hdbl else 1
        net = r * stake
        print(f"  {hlabel}: {card_display(hcards)} = {pt}  vs  Dealer {dt}"
              f"  → {outcome_str(r)} ({net:+d} units)")


def print_welcome():
    print("""
╔══════════════════════════════════════════════════════════╗
║            BLACKJACK COPILOT  v1.0                      ║
║          Your real-time blackjack advisor                ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  How to use:                                             ║
║  1. Enter cards as they appear on the table              ║
║     A = Ace, K/Q/J = face cards, T or 10 = ten           ║
║     2-9 = number cards (lowercase ok)                    ║
║                                                          ║
║  2. The copilot will show you:                           ║
║     - Win/Push/Lose odds for each action                 ║
║     - Expected value (EV) for Hit, Stand, Double, Split  ║
║     - A clear recommendation with reasoning              ║
║     - Running count and true count (Hi-Lo)               ║
║                                                          ║
║  3. After each hand: keep the shoe, reset, or quit       ║
║                                                          ║
║  Rules: 6-deck shoe, dealer hits soft 17 (H17)           ║
║  Simulations: 50,000 per decision                        ║
╚══════════════════════════════════════════════════════════╝
""")


def main():
    print_welcome()
    shoe = Shoe()
    engine = OddsEngine(n_sims=NUM_SIMS, seed=SEED_BASE)

    while True:
        print(f"\n  Shoe: {shoe.cards_remaining} cards, "
              f"RC={shoe.running_count:+d}, TC={shoe.true_count:+.1f}")
        run_hand(shoe, engine)
        print()
        print("  What next?")
        print("  [N] New hand (keep shoe)")
        print("  [R] Reset shoe (fresh 6 decks)")
        print("  [Q] Quit")
        while True:
            choice = input("  > ").strip().upper()
            if choice in ('N', 'R', 'Q'):
                break
            print("  Enter N, R, or Q")
        if choice == 'Q':
            print("\n  Thanks for playing! Good luck at the tables.\n")
            break
        elif choice == 'R':
            shoe = Shoe()
            print("  Shoe reset to 6 fresh decks.")


if __name__ == '__main__':
    main()
