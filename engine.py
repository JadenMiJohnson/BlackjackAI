"""
Blackjack Copilot Engine — Game logic, Monte Carlo simulation, and state management.

Rules: 6-deck shoe, dealer hits soft 17 (H17), split up to 3 times,
split aces get one card only, double after split allowed, no resplit aces.
Betting: stake-at-risk model (deduct when placed, return on win/push).
"""

import random
import uuid

NUM_DECKS = 6
DEALER_HITS_SOFT_17 = True
MAX_SPLITS = 3
SPLIT_ACES_ONE_CARD_ONLY = True
DOUBLE_AFTER_SPLIT = True
RESPLIT_ACES = False
DOUBLE_ONLY_ON_FIRST_TWO = True

DEFAULT_SIMS = 5_000
SEED_BASE = 42

RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
SUITS = ['spades', 'hearts', 'diamonds', 'clubs']
RANK_VALUES = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11
}
HILO = {
    '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
    '7': 0, '8': 0, '9': 0,
    '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
}


class Shoe:
    def __init__(self, num_decks=NUM_DECKS):
        self.num_decks = num_decks
        self.counts = {r: 4 * num_decks for r in RANKS}
        self.running_count = 0
        self._suit_rng = random.Random(99)

    def copy(self):
        s = Shoe.__new__(Shoe)
        s.num_decks = self.num_decks
        s.counts = dict(self.counts)
        s.running_count = self.running_count
        s._suit_rng = random.Random()
        s._suit_rng.setstate(self._suit_rng.getstate())
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

    def draw_with_suit(self, rng):
        rank = self.draw_random(rng)
        suit = self._suit_rng.choice(SUITS)
        return rank, suit


def hand_total(cards):
    total = 0
    aces = 0
    for c in cards:
        r = c if isinstance(c, str) else c['rank']
        v = RANK_VALUES[r]
        if r == 'A':
            aces += 1
        total += v
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    soft = aces > 0 and total <= 21
    return total, soft


def hand_total_ranks(ranks):
    total = 0
    aces = 0
    for r in ranks:
        v = RANK_VALUES[r]
        if r == 'A':
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
    r0 = cards[0] if isinstance(cards[0], str) else cards[0]['rank']
    r1 = cards[1] if isinstance(cards[1], str) else cards[1]['rank']
    return r0 == r1


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


def play_dealer_h17(shoe, dealer_cards, rng):
    cards = list(dealer_cards)
    while True:
        t, soft = hand_total_ranks(cards)
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


def basic_strategy_action(player_ranks, dealer_up_rank, can_double, can_split):
    t, soft = hand_total_ranks(player_ranks)
    if can_split and len(player_ranks) == 2 and player_ranks[0] == player_ranks[1]:
        r = player_ranks[0]
        v = RANK_VALUES[r]
        if r == 'A':
            return 'SPLIT'
        if v == 8:
            return 'SPLIT'
        dv = RANK_VALUES[dealer_up_rank]
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
        dv = RANK_VALUES[dealer_up_rank]
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
        dv = RANK_VALUES[dealer_up_rank]
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


def sim_play_hand_bs(shoe, player_ranks, dealer_up_rank, rng,
                     is_split_hand=False, split_depth=0, is_aces=False):
    cards = list(player_ranks)
    if is_aces and SPLIT_ACES_ONE_CARD_ONLY:
        return cards, False
    while True:
        t, _ = hand_total_ranks(cards)
        if t >= 21:
            break
        can_double = (len(cards) == 2) and DOUBLE_ONLY_ON_FIRST_TWO
        if is_split_hand and not DOUBLE_AFTER_SPLIT:
            can_double = False
        can_split = (len(cards) == 2 and cards[0] == cards[1]
                     and split_depth < MAX_SPLITS
                     and (not is_aces or RESPLIT_ACES))
        action = basic_strategy_action(cards, dealer_up_rank, can_double, can_split)
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


def sim_play_split_hands(shoe, split_rank, dealer_up_rank, rng, split_depth=1):
    is_aces = (split_rank == 'A')
    results = []
    for _ in range(2):
        new_card = shoe.draw_random(rng)
        sub_cards = [split_rank, new_card]
        if (sub_cards[0] == sub_cards[1] and split_depth < MAX_SPLITS
                and (not is_aces or RESPLIT_ACES)):
            action = basic_strategy_action(sub_cards, dealer_up_rank, False, True)
            if action == 'SPLIT':
                sub_results = sim_play_split_hands(
                    shoe, split_rank, dealer_up_rank, rng, split_depth + 1)
                results.extend(sub_results)
                continue
        final, doubled = sim_play_hand_bs(
            shoe, sub_cards, dealer_up_rank, rng,
            is_split_hand=True, split_depth=split_depth, is_aces=is_aces)
        pt, _ = hand_total_ranks(final)
        results.append((pt, 2 if doubled else 1))
    return results


def sim_stand(shoe, player_ranks, dealer_up_rank, dealer_hole, rng):
    pt, _ = hand_total_ranks(player_ranks)
    dc = play_dealer_h17(shoe, [dealer_up_rank, dealer_hole], rng)
    dt, _ = hand_total_ranks(dc)
    return compare_hands(pt, dt)


def sim_hit(shoe, player_ranks, dealer_up_rank, dealer_hole, rng):
    card = shoe.draw_random(rng)
    new_hand = list(player_ranks) + [card]
    t, _ = hand_total_ranks(new_hand)
    if t > 21:
        return -1
    final, doubled = sim_play_hand_bs(shoe, new_hand, dealer_up_rank, rng)
    pt, _ = hand_total_ranks(final)
    if pt > 21:
        return -1
    dc = play_dealer_h17(shoe, [dealer_up_rank, dealer_hole], rng)
    dt, _ = hand_total_ranks(dc)
    r = compare_hands(pt, dt)
    return r * (2 if doubled else 1)


def sim_double(shoe, player_ranks, dealer_up_rank, dealer_hole, rng):
    card = shoe.draw_random(rng)
    new_hand = list(player_ranks) + [card]
    pt, _ = hand_total_ranks(new_hand)
    if pt > 21:
        return -2
    dc = play_dealer_h17(shoe, [dealer_up_rank, dealer_hole], rng)
    dt, _ = hand_total_ranks(dc)
    return compare_hands(pt, dt) * 2


def sim_split(shoe, player_ranks, dealer_up_rank, dealer_hole, rng):
    split_rank = player_ranks[0]
    hand_results = sim_play_split_hands(shoe, split_rank, dealer_up_rank, rng, 1)
    dc = play_dealer_h17(shoe, [dealer_up_rank, dealer_hole], rng)
    dt, _ = hand_total_ranks(dc)
    total_ev = 0
    for pt, stake in hand_results:
        if pt > 21:
            total_ev -= stake
        else:
            r = compare_hands(pt, dt)
            total_ev += r * stake
    return total_ev


class OddsEngine:
    def __init__(self, n_sims=DEFAULT_SIMS, seed=SEED_BASE):
        self.n_sims = n_sims
        self.seed = seed

    def simulate_action(self, shoe, player_ranks, dealer_up_rank, action, n_sims=None):
        if n_sims is None:
            n_sims = self.n_sims
        rng = random.Random(self.seed)
        wins = losses = pushes = 0
        total_ev = 0.0
        for i in range(n_sims):
            rng.seed(self.seed + i * 13 + hash(action) % 9973)
            sim_shoe = shoe.copy()
            hole = sim_shoe.draw_random(rng)
            if action == 'STAND':
                result = sim_stand(sim_shoe, player_ranks, dealer_up_rank, hole, rng)
            elif action == 'HIT':
                result = sim_hit(sim_shoe, player_ranks, dealer_up_rank, hole, rng)
            elif action == 'DOUBLE':
                result = sim_double(sim_shoe, player_ranks, dealer_up_rank, hole, rng)
            elif action == 'SPLIT':
                result = sim_split(sim_shoe, player_ranks, dealer_up_rank, hole, rng)
            else:
                result = 0
            total_ev += result
            if result > 0:
                wins += 1
            elif result == 0:
                pushes += 1
            else:
                losses += 1
        return {
            'ev': total_ev / n_sims,
            'p_win': wins / n_sims,
            'p_push': pushes / n_sims,
            'p_lose': losses / n_sims
        }

    def compute_bust_prob(self, shoe, player_ranks, n_sims=None):
        if n_sims is None:
            n_sims = min(self.n_sims, 10000)
        rng = random.Random(self.seed + 7)
        busts = 0
        for i in range(n_sims):
            rng.seed(self.seed + 7 + i)
            sim_shoe = shoe.copy()
            card = sim_shoe.draw_random(rng)
            t, _ = hand_total_ranks(list(player_ranks) + [card])
            if t > 21:
                busts += 1
        return busts / n_sims

    def compute_dealer_bust_prob(self, shoe, dealer_up_rank, n_sims=None):
        if n_sims is None:
            n_sims = min(self.n_sims, 10000)
        rng = random.Random(self.seed + 11)
        busts = 0
        for i in range(n_sims):
            rng.seed(self.seed + 11 + i)
            sim_shoe = shoe.copy()
            hole = sim_shoe.draw_random(rng)
            dc = play_dealer_h17(sim_shoe, [dealer_up_rank, hole], rng)
            t, _ = hand_total_ranks(dc)
            if t > 21:
                busts += 1
        return busts / n_sims

    def full_analysis(self, shoe, player_ranks, dealer_up_rank,
                      can_double=True, can_split=False):
        actions_list = ['hit', 'stand']
        if can_double:
            actions_list.append('double')
        if can_split:
            actions_list.append('split')
        results = {}
        for action in actions_list:
            results[action] = self.simulate_action(
                shoe, player_ranks, dealer_up_rank, action.upper())
        bust_prob = self.compute_bust_prob(shoe, player_ranks)
        dealer_bust = self.compute_dealer_bust_prob(shoe, dealer_up_rank)
        best_action = max(results, key=lambda a: results[a]['ev'])
        evs_sorted = sorted(results.items(), key=lambda x: -x[1]['ev'])
        ev_gap = 0.0
        if len(evs_sorted) >= 2:
            ev_gap = evs_sorted[0][1]['ev'] - evs_sorted[1][1]['ev']
        return {
            'best': best_action,
            'actions': results,
            'bust_if_hit': bust_prob,
            'dealer_bust': dealer_bust,
            'ev_gap': ev_gap,
        }


class HandState:
    def __init__(self, hand_id=0):
        self.hand_id = hand_id
        self.cards = []
        self.status = 'active'
        self.doubled = False
        self.is_split_hand = False
        self.split_from_aces = False
        self.split_depth = 0
        self.stake = 0

    def ranks(self):
        return [c['rank'] for c in self.cards]

    def total(self):
        return hand_total_ranks(self.ranks())

    def can_hit(self):
        if self.status != 'active':
            return False
        t, _ = self.total()
        return t < 21

    def can_stand(self):
        return self.status == 'active'

    def can_double(self):
        if self.status != 'active':
            return False
        if len(self.cards) != 2:
            return False
        if not DOUBLE_ONLY_ON_FIRST_TWO:
            return True
        if self.is_split_hand and not DOUBLE_AFTER_SPLIT:
            return False
        return True

    def can_split(self):
        if self.status != 'active':
            return False
        if len(self.cards) != 2:
            return False
        if self.cards[0]['rank'] != self.cards[1]['rank']:
            return False
        if self.split_depth >= MAX_SPLITS:
            return False
        if self.split_from_aces and not RESPLIT_ACES:
            return False
        return True

    def to_dict(self):
        t, soft = self.total()
        return {
            'hand_id': self.hand_id,
            'cards': self.cards,
            'total': t,
            'soft': soft,
            'status': self.status,
            'doubled': self.doubled,
            'can_hit': self.can_hit(),
            'can_stand': self.can_stand(),
            'can_double': self.can_double(),
            'can_split': self.can_split(),
            'stake': self.stake,
        }


def compute_bet(true_count, min_bet, max_units):
    tc = true_count
    if tc <= 0:
        units = 1
    elif tc < 1:
        units = 1
    elif tc < 2:
        units = 2
    elif tc < 3:
        units = 4
    else:
        units = 6
    units = min(units, max_units)
    return min_bet * units


class GameState:
    def __init__(self, mode='regular', starting_bankroll=1000, min_bet=10,
                 max_units=8, n_sims=DEFAULT_SIMS, delay_ms=600,
                 stop_after_hands=50, stop_on_bankrupt=True):
        self.game_id = str(uuid.uuid4())
        self.mode = mode
        self.shoe = Shoe()
        self.rng = random.Random()
        self.engine = OddsEngine(n_sims=n_sims, seed=SEED_BASE)
        self.n_sims = n_sims
        self.dealer_cards = []
        self.dealer_hole_hidden = True
        self.player_hands = []
        self.active_hand_index = 0
        self.phase = 'idle'
        self.outcomes = []
        self.next_hand_id = 0
        self._hole_card_rank = None

        self.starting_bankroll = starting_bankroll
        self.bankroll = starting_bankroll
        self.min_bet = min_bet
        self.max_units = max_units
        self.current_bet = 0
        self.delay_ms = delay_ms
        self.stop_after_hands = stop_after_hands
        self.stop_on_bankrupt = stop_on_bankrupt

        self.hands_played = 0
        self.wins = 0
        self.losses = 0
        self.pushes = 0

        self.autoplay_active = False
        self.session_stopped = False
        self.stop_reason = None

    def _draw_card(self):
        rank, suit = self.shoe.draw_with_suit(self.rng)
        return {'rank': rank, 'suit': suit}

    def deal_new_hand(self):
        if self.session_stopped:
            return self.get_state()

        if self.stop_after_hands and self.hands_played >= self.stop_after_hands:
            self.session_stopped = True
            self.stop_reason = f'Reached {self.stop_after_hands} hands'
            self.autoplay_active = False
            return self.get_state()

        if self.stop_on_bankrupt and self.bankroll <= 0:
            self.session_stopped = True
            self.stop_reason = 'Bankroll depleted'
            self.autoplay_active = False
            return self.get_state()

        if self.shoe.cards_remaining < 20:
            self.shoe = Shoe()

        if self.bankroll < self.min_bet:
            self.session_stopped = True
            self.stop_reason = 'Bankroll too low for minimum bet'
            self.autoplay_active = False
            return self.get_state()

        self.current_bet = compute_bet(self.shoe.true_count, self.min_bet, self.max_units)
        if self.current_bet > self.bankroll:
            self.current_bet = self.bankroll

        self.bankroll -= self.current_bet

        self.dealer_cards = []
        self.player_hands = []
        self.active_hand_index = 0
        self.phase = 'player'
        self.outcomes = []
        self.dealer_hole_hidden = True
        self.next_hand_id = 0

        d1 = self._draw_card()
        d2_rank, d2_suit = self.shoe.draw_with_suit(self.rng)
        self.shoe.running_count -= HILO[d2_rank]
        self._hole_card_rank = d2_rank
        d2 = {'rank': d2_rank, 'suit': d2_suit, 'hidden': True}
        self.dealer_cards = [d1, d2]

        hand = HandState(self.next_hand_id)
        self.next_hand_id += 1
        c1 = self._draw_card()
        c2 = self._draw_card()
        hand.cards = [c1, c2]
        hand.stake = self.current_bet
        self.player_hands = [hand]

        t, _ = hand.total()
        if t == 21:
            hand.status = 'stood'
            self._finish_all_hands()

        return self.get_state()

    def reset_shoe(self):
        self.shoe = Shoe()
        self.phase = 'idle'
        self.dealer_cards = []
        self.player_hands = []
        self.outcomes = []
        self.hands_played = 0
        self.wins = 0
        self.losses = 0
        self.pushes = 0
        self.bankroll = self.starting_bankroll
        self.session_stopped = False
        self.stop_reason = None
        return self.get_state()

    def apply_action(self, action):
        if self.phase != 'player':
            return self.get_state()

        action = action.lower()
        hand = self.player_hands[self.active_hand_index]

        if action == 'hit' and hand.can_hit():
            card = self._draw_card()
            hand.cards.append(card)
            t, _ = hand.total()
            if t > 21:
                hand.status = 'bust'
                self._advance_hand()
            elif t == 21:
                hand.status = 'stood'
                self._advance_hand()

        elif action == 'stand' and hand.can_stand():
            hand.status = 'stood'
            self._advance_hand()

        elif action == 'double' and hand.can_double() and self.bankroll >= hand.stake:
            extra = hand.stake
            self.bankroll -= extra
            hand.stake += extra
            hand.doubled = True

            card = self._draw_card()
            hand.cards.append(card)
            t, _ = hand.total()
            if t > 21:
                hand.status = 'bust'
            else:
                hand.status = 'stood'
            self._advance_hand()

        elif action == 'split' and hand.can_split() and self.bankroll >= hand.stake:
            split_rank = hand.cards[0]['rank']
            is_aces = (split_rank == 'A')
            c1_old = hand.cards[0]
            c2_old = hand.cards[1]
            original_stake = hand.stake

            self.bankroll -= original_stake

            h1 = HandState(self.next_hand_id)
            self.next_hand_id += 1
            h1.is_split_hand = True
            h1.split_from_aces = is_aces
            h1.split_depth = hand.split_depth + 1
            h1.stake = original_stake
            new_c1 = self._draw_card()
            h1.cards = [c1_old, new_c1]

            h2 = HandState(self.next_hand_id)
            self.next_hand_id += 1
            h2.is_split_hand = True
            h2.split_from_aces = is_aces
            h2.split_depth = hand.split_depth + 1
            h2.stake = original_stake
            new_c2 = self._draw_card()
            h2.cards = [c2_old, new_c2]

            idx = self.active_hand_index
            self.player_hands[idx:idx+1] = [h1, h2]

            if is_aces and SPLIT_ACES_ONE_CARD_ONLY:
                h1.status = 'stood'
                h2.status = 'stood'
                self._advance_hand()
            else:
                t1, _ = h1.total()
                if t1 == 21:
                    h1.status = 'stood'
                    self.active_hand_index += 1
                    t2, _ = h2.total()
                    if t2 == 21:
                        h2.status = 'stood'
                        self._advance_hand()

        return self.get_state()

    def _advance_hand(self):
        for i in range(len(self.player_hands)):
            if self.player_hands[i].status == 'active':
                self.active_hand_index = i
                return
        self._finish_all_hands()

    def _finish_all_hands(self):
        self.phase = 'complete'
        self.dealer_hole_hidden = False

        if self._hole_card_rank:
            self.shoe.running_count += HILO[self._hole_card_rank]
            self._hole_card_rank = None

        dealer_ranks = [c['rank'] for c in self.dealer_cards]

        all_bust = all(h.status == 'bust' for h in self.player_hands)
        if not all_bust:
            dealer_final = play_dealer_h17(self.shoe, dealer_ranks, self.rng)
            while len(dealer_final) > len(self.dealer_cards):
                extra_rank = dealer_final[len(self.dealer_cards)]
                suit = self.shoe._suit_rng.choice(SUITS)
                self.dealer_cards.append({'rank': extra_rank, 'suit': suit})

        dt, _ = hand_total_ranks([c['rank'] for c in self.dealer_cards])

        self.outcomes = []
        for h in self.player_hands:
            pt, _ = h.total()
            if pt > 21:
                result = -1
            else:
                result = compare_hands(pt, dt)

            if result > 0:
                label = 'WIN'
                payout = h.stake * 2
                self.wins += 1
            elif result == 0:
                label = 'PUSH'
                payout = h.stake
                self.pushes += 1
            else:
                label = 'LOSE'
                payout = 0
                self.losses += 1

            self.bankroll += payout

            net = payout - h.stake
            self.outcomes.append({
                'hand_id': h.hand_id,
                'player_total': pt,
                'dealer_total': dt,
                'result': label,
                'stake': h.stake,
                'payout': payout,
                'net': net
            })

        self.hands_played += 1

    def _get_recommendation(self):
        if self.phase != 'player':
            return None
        hand = self.player_hands[self.active_hand_index]
        if hand.status != 'active':
            return None

        player_ranks = hand.ranks()
        dealer_up_rank = self.dealer_cards[0]['rank']

        can_dbl = hand.can_double() and self.bankroll >= hand.stake
        can_spl = hand.can_split() and self.bankroll >= hand.stake
        analysis = self.engine.full_analysis(
            self.shoe, player_ranks, dealer_up_rank,
            can_double=can_dbl,
            can_split=can_spl
        )

        evs = {}
        probs = {}
        for a, data in analysis['actions'].items():
            evs[a] = round(data['ev'], 4)
            probs[a] = {
                'win': round(data['p_win'], 3),
                'push': round(data['p_push'], 3),
                'lose': round(data['p_lose'], 3)
            }

        best = analysis['best']
        best_ev = evs[best]
        reasons = []
        reasons.append(f"EV = {best_ev:+.4f}")
        bust_pct = round(analysis['bust_if_hit'] * 100, 1)
        dealer_bust_pct = round(analysis['dealer_bust'] * 100, 1)
        reasons.append(f"Bust risk if hit: {bust_pct}%")
        reasons.append(f"Dealer bust chance: {dealer_bust_pct}%")
        if analysis['ev_gap'] > 0:
            reasons.append(f"EV edge over next best: {analysis['ev_gap']:+.4f}")

        return {
            'action': best,
            'evs': evs,
            'probs': probs,
            'bust_risk_hit': round(analysis['bust_if_hit'], 3),
            'dealer_bust_if_stand': round(analysis['dealer_bust'], 3),
            'explanation': '; '.join(reasons)
        }

    def auto_step(self):
        if not self.autoplay_active:
            return self.get_state()

        if self.session_stopped:
            self.autoplay_active = False
            return self.get_state()

        if self.phase == 'idle' or self.phase == 'complete':
            return self.deal_new_hand()

        if self.phase == 'player':
            hand = self.player_hands[self.active_hand_index]
            if hand.status != 'active':
                self._advance_hand()
                return self.get_state()

            rec = self._get_recommendation()
            if rec:
                action = rec['action']
                self.apply_action(action)
                state = self.get_state()
                state['recommendation'] = rec
                return state
            else:
                action = basic_strategy_action(
                    hand.ranks(), self.dealer_cards[0]['rank'],
                    hand.can_double(), hand.can_split()
                ).lower()
                return self.apply_action(action)

        return self.get_state()

    def get_state(self):
        dealer_out = []
        for i, c in enumerate(self.dealer_cards):
            if i == 1 and self.dealer_hole_hidden:
                dealer_out.append({'rank': '?', 'suit': '?', 'hidden': True})
            else:
                dealer_out.append({'rank': c['rank'], 'suit': c['suit'], 'hidden': False})

        visible_dealer = [c for c in dealer_out if not c['hidden']]
        dt_visible = 0
        if visible_dealer:
            dt_visible, _ = hand_total_ranks([c['rank'] for c in visible_dealer])

        dt_final = None
        if not self.dealer_hole_hidden and self.dealer_cards:
            dt_final, _ = hand_total_ranks([c['rank'] for c in self.dealer_cards])

        hands_out = [h.to_dict() for h in self.player_hands]

        active_hand = None
        actions_legal = {'hit': False, 'stand': False, 'double': False, 'split': False}
        reasons = {}
        if self.phase == 'player' and self.active_hand_index < len(self.player_hands):
            ah = self.player_hands[self.active_hand_index]
            active_hand = self.active_hand_index
            actions_legal['hit'] = ah.can_hit()
            actions_legal['stand'] = ah.can_stand()
            can_dbl = ah.can_double() and self.bankroll >= ah.stake
            can_spl = ah.can_split() and self.bankroll >= ah.stake
            actions_legal['double'] = can_dbl
            actions_legal['split'] = can_spl
            if not can_dbl:
                if len(ah.cards) != 2:
                    reasons['double'] = 'Only on first two cards'
                elif ah.is_split_hand and not DOUBLE_AFTER_SPLIT:
                    reasons['double'] = 'No double after split'
                elif ah.can_double() and self.bankroll < ah.stake:
                    reasons['double'] = 'Insufficient bankroll'
            if not can_spl:
                if len(ah.cards) != 2 or ah.cards[0]['rank'] != ah.cards[1]['rank']:
                    reasons['split'] = 'Need a pair to split'
                elif ah.split_depth >= MAX_SPLITS:
                    reasons['split'] = f'Max {MAX_SPLITS} splits reached'
                elif ah.split_from_aces and not RESPLIT_ACES:
                    reasons['split'] = 'Cannot resplit aces'
                elif ah.can_split() and self.bankroll < ah.stake:
                    reasons['split'] = 'Insufficient bankroll'

        net_profit = self.bankroll - self.starting_bankroll
        roi = (net_profit / self.starting_bankroll * 100) if self.starting_bankroll > 0 else 0

        return {
            'game_id': self.game_id,
            'mode': self.mode,
            'phase': self.phase,
            'dealer': {
                'cards': dealer_out,
                'total_visible': dt_visible,
                'total_final': dt_final
            },
            'player_hands': hands_out,
            'active_hand_index': active_hand,
            'actions_legal': actions_legal,
            'reasons': reasons,
            'recommendation': None,
            'count': {
                'running': self.shoe.running_count,
                'true': round(self.shoe.true_count, 1),
                'decks_remaining': round(self.shoe.decks_remaining, 2)
            },
            'outcome': self.outcomes if self.phase == 'complete' else None,
            'bankroll': {
                'current': self.bankroll,
                'starting': self.starting_bankroll,
                'current_bet': self.current_bet,
                'min_bet': self.min_bet,
                'max_units': self.max_units,
            },
            'stats': {
                'hands_played': self.hands_played,
                'wins': self.wins,
                'losses': self.losses,
                'pushes': self.pushes,
                'net_profit': net_profit,
                'roi': round(roi, 2),
            },
            'autoplay': {
                'active': self.autoplay_active,
                'delay_ms': self.delay_ms,
                'session_stopped': self.session_stopped,
                'stop_reason': self.stop_reason,
            },
            'config': {
                'decks': NUM_DECKS,
                'dealer_h17': DEALER_HITS_SOFT_17,
                'n_sims': self.n_sims,
            }
        }
