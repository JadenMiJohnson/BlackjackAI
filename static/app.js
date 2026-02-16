let gameId = null;
let currentState = null;

const SUIT_SYMBOLS = {
    spades: '\u2660', hearts: '\u2665', diamonds: '\u2666', clubs: '\u2663'
};
const RED_SUITS = new Set(['hearts', 'diamonds']);

async function api(endpoint, body = null, method = null) {
    const opts = { headers: { 'Content-Type': 'application/json' } };
    if (method) {
        opts.method = method;
    } else if (body !== null) {
        opts.method = 'POST';
    }
    if (body !== null) {
        opts.body = JSON.stringify(body);
    }
    const res = await fetch(endpoint, opts);
    return res.json();
}

function showLoading() {
    document.getElementById('loading-overlay').classList.remove('hidden');
}
function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

async function fetchRecommendation() {
    if (!gameId || !currentState || currentState.phase !== 'player') return;
    setRecLoading(true);
    try {
        const data = await api('/api/recommend', { game_id: gameId });
        if (currentState && currentState.phase === 'player') {
            currentState.recommendation = data.recommendation;
            renderRecommendation(currentState);
            renderOdds(currentState);
        }
    } catch (e) {
        console.error('Recommendation error:', e);
    }
    setRecLoading(false);
}

function setRecLoading(loading) {
    const recAction = document.getElementById('rec-action');
    const recExpl = document.getElementById('rec-explanation');
    if (loading) {
        recAction.textContent = 'Analyzing...';
        recAction.className = 'rec-action no-rec';
        recExpl.textContent = 'Running Monte Carlo simulations...';
    }
}

async function startGame() {
    showLoading();
    const state = await api('/api/new_game', {}, 'POST');
    gameId = state.game_id;
    currentState = state;
    render(state);
    hideLoading();
    fetchRecommendation();
}

async function newHand() {
    if (!gameId) return startGame();
    showLoading();
    const state = await api('/api/new_hand', { game_id: gameId });
    currentState = state;
    render(state);
    hideLoading();
    fetchRecommendation();
}

async function resetShoe() {
    if (!gameId) return startGame();
    showLoading();
    await api('/api/reset_shoe', { game_id: gameId });
    const state = await api('/api/new_hand', { game_id: gameId });
    currentState = state;
    render(state);
    hideLoading();
    fetchRecommendation();
}

async function doAction(action) {
    if (!gameId) return;
    showLoading();
    const state = await api('/api/action', { game_id: gameId, action: action });
    if (state.error) {
        console.error('Action error:', state.error);
        hideLoading();
        return;
    }
    currentState = state;
    render(state);
    hideLoading();
    if (state.phase === 'player') {
        fetchRecommendation();
    }
}

function createCardEl(card) {
    const el = document.createElement('div');
    if (card.hidden) {
        el.className = 'card face-down';
        return el;
    }
    const isRed = RED_SUITS.has(card.suit);
    el.className = 'card face-up ' + (isRed ? 'red' : 'black');
    const suitSym = SUIT_SYMBOLS[card.suit] || card.suit;
    el.innerHTML =
        '<span class="corner-rank">' + card.rank + '</span>' +
        '<span class="corner-suit">' + suitSym + '</span>' +
        '<span class="rank">' + card.rank + '</span>' +
        '<span class="suit">' + suitSym + '</span>';
    return el;
}

function render(state) {
    renderDealer(state);
    renderPlayerHands(state);
    renderActions(state);
    renderRecommendation(state);
    renderOdds(state);
    renderCount(state);
    renderOutcome(state);
}

function renderDealer(state) {
    const container = document.getElementById('dealer-cards');
    container.innerHTML = '';
    for (const card of state.dealer.cards) {
        container.appendChild(createCardEl(card));
    }
    const totalEl = document.getElementById('dealer-total');
    if (state.dealer.total_final !== null && state.dealer.total_final !== undefined) {
        totalEl.textContent = 'Total: ' + state.dealer.total_final;
    } else {
        totalEl.textContent = 'Showing: ' + state.dealer.total_visible;
    }
}

function renderPlayerHands(state) {
    const container = document.getElementById('player-hands');
    container.innerHTML = '';
    const hands = state.player_hands;
    const multiHand = hands.length > 1;

    for (let i = 0; i < hands.length; i++) {
        const h = hands[i];
        const group = document.createElement('div');
        group.className = 'player-hand-group';

        const label = document.createElement('div');
        label.className = 'hand-label';
        let labelText = multiHand ? 'Hand ' + (i + 1) : '';
        let extras = '';
        if (state.phase === 'player' && i === state.active_hand_index && h.status === 'active') {
            extras += '<span class="active-dot"></span>';
        }
        if (h.status === 'bust') {
            extras += '<span class="status-badge bust">BUST</span>';
        } else if (h.status === 'stood' && state.phase === 'player') {
            extras += '<span class="status-badge stood">STOOD</span>';
        }
        label.innerHTML = labelText + ' ' + extras;
        if (labelText || extras) group.appendChild(label);

        const cardsRow = document.createElement('div');
        cardsRow.className = 'cards-row';
        for (const card of h.cards) {
            cardsRow.appendChild(createCardEl(card));
        }
        group.appendChild(cardsRow);

        const totalEl = document.createElement('div');
        totalEl.className = 'hand-total';
        const softStr = h.soft ? ' (soft)' : '';
        totalEl.textContent = 'Total: ' + h.total + softStr;
        if (h.doubled) totalEl.textContent += ' [DOUBLED]';
        group.appendChild(totalEl);

        container.appendChild(group);
    }
}

function renderActions(state) {
    const actions = state.actions_legal;
    const reasons = state.reasons || {};
    const phase = state.phase;

    const btnHit = document.getElementById('btn-hit');
    const btnStand = document.getElementById('btn-stand');
    const btnDouble = document.getElementById('btn-double');
    const btnSplit = document.getElementById('btn-split');

    if (phase !== 'player') {
        btnHit.disabled = true;
        btnStand.disabled = true;
        btnDouble.disabled = true;
        btnSplit.disabled = true;
        return;
    }

    btnHit.disabled = !actions.hit;
    btnStand.disabled = !actions.stand;
    btnDouble.disabled = !actions.double;
    btnSplit.disabled = !actions.split;

    btnDouble.title = reasons.double || '';
    btnSplit.title = reasons.split || '';
}

function renderRecommendation(state) {
    const recAction = document.getElementById('rec-action');
    const recExpl = document.getElementById('rec-explanation');
    const recDetails = document.getElementById('rec-details');

    if (!state.recommendation) {
        if (state.phase === 'complete') {
            recAction.textContent = 'Hand Complete';
            recAction.className = 'rec-action no-rec';
        }
        recExpl.textContent = '';
        recDetails.textContent = '';
        return;
    }

    const rec = state.recommendation;
    const actionName = rec.action.toUpperCase();
    recAction.textContent = '\u2192 ' + actionName;
    recAction.className = 'rec-action ' + rec.action;
    recExpl.textContent = rec.explanation;

    const bustPct = (rec.bust_risk_hit * 100).toFixed(1);
    const dealerBustPct = (rec.dealer_bust_if_stand * 100).toFixed(1);
    recDetails.textContent = 'Bust risk if hit: ' + bustPct + '% \u00B7 Dealer bust: ' + dealerBustPct + '%';
}

function renderOdds(state) {
    const tbody = document.getElementById('odds-body');
    tbody.innerHTML = '';

    if (!state.recommendation) return;

    const rec = state.recommendation;
    const best = rec.action;

    const order = ['hit', 'stand', 'double', 'split'];
    for (const action of order) {
        if (!(action in rec.probs)) continue;
        const p = rec.probs[action];
        const ev = rec.evs[action];
        const tr = document.createElement('tr');
        if (action === best) tr.className = 'best';
        const marker = action === best ? ' \u2190' : '';
        tr.innerHTML =
            '<td>' + action.toUpperCase() + marker + '</td>' +
            '<td>' + (p.win * 100).toFixed(1) + '%</td>' +
            '<td>' + (p.push * 100).toFixed(1) + '%</td>' +
            '<td>' + (p.lose * 100).toFixed(1) + '%</td>' +
            '<td>' + (ev >= 0 ? '+' : '') + ev.toFixed(4) + '</td>';
        tbody.appendChild(tr);
    }
}

function renderCount(state) {
    const rc = state.count.running;
    document.getElementById('running-count').textContent = (rc >= 0 ? '+' : '') + rc;
    document.getElementById('true-count').textContent =
        (state.count.true >= 0 ? '+' : '') + state.count.true.toFixed(1);
    document.getElementById('decks-remaining').textContent = state.count.decks_remaining.toFixed(2);
}

function renderOutcome(state) {
    const banner = document.getElementById('outcome-banner');
    if (state.phase !== 'complete' || !state.outcome) {
        banner.classList.add('hidden');
        return;
    }

    banner.classList.remove('hidden');
    const results = state.outcome;
    let totalNet = 0;
    const parts = [];
    for (const r of results) {
        totalNet += r.net;
        if (results.length > 1) {
            parts.push('Hand (' + r.player_total + ' vs ' + r.dealer_total + '): ' + r.result + ' ' + (r.net >= 0 ? '+' : '') + r.net);
        }
    }

    let text = '';
    if (results.length === 1) {
        const r = results[0];
        text = r.result + ' \u2014 Your ' + r.player_total + ' vs Dealer ' + r.dealer_total + ' (' + (r.net >= 0 ? '+' : '') + r.net + ' units)';
    } else {
        text = parts.join(' \u00B7 ') + ' \u2014 Net: ' + (totalNet >= 0 ? '+' : '') + totalNet + ' units';
    }

    banner.textContent = text;

    if (totalNet > 0) {
        banner.style.background = '#238636';
        banner.style.color = '#fff';
    } else if (totalNet === 0) {
        banner.style.background = '#30363d';
        banner.style.color = '#c9d1d9';
    } else {
        banner.style.background = '#da3633';
        banner.style.color = '#fff';
    }
}

startGame();
