const byId = (id) => document.getElementById(id);
const colors = {red: '빨강', yellow: '노랑', green: '초록', blue: '파랑', wild: '와일드'};
const symbols = {skip: '⊘', reverse: '↻', draw2: '+2', wild: '★', draw4: '+4'};
const labels = {skip: '건너뛰기', reverse: '방향 전환', draw2: '+2', wild: '색 바꾸기', draw4: '+4'};
const storageKey = 'uno-championship-session';
let session = null;
let state = null;
let busy = false;
let renderedRevision = null;
let choiceRevision = null;

try {
  const saved = JSON.parse(sessionStorage.getItem(storageKey));
  if (/^[A-Z2-9]{6}$/.test(saved?.code) && typeof saved?.token === 'string') session = saved;
} catch { /* The room still works if browser storage is unavailable. */ }

function saveSession(value) {
  session = value;
  try {
    if (value) sessionStorage.setItem(storageKey, JSON.stringify(value));
    else sessionStorage.removeItem(storageKey);
  } catch { /* Refresh recovery requires session storage. */ }
}

async function request(path, data, token) {
  const headers = {};
  if (data) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, {
    method: data ? 'POST' : 'GET', headers, body: data ? JSON.stringify(data) : undefined,
    cache: 'no-store', signal: AbortSignal.timeout(12000),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(result.error || '서버가 응답하지 않습니다. 잠시 뒤 다시 시도해 주세요.');
    error.status = response.status;
    throw error;
  }
  return result;
}

function notice(message = '') {
  byId('notice').textContent = message;
  byId('notice').hidden = !message;
}

function el(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function makeCard(card, allowed, interactive) {
  const face = symbols[card.value] || card.value;
  const label = `${colors[card.color]} ${labels[card.value] || card.value}`;
  const element = el(interactive ? 'button' : 'div', face, `card ${card.color}`);
  element.setAttribute('aria-label', label);
  if (!interactive) element.setAttribute('role', 'img');
  element.title = labels[card.value] || card.value;
  if (interactive) {
    element.type = 'button';
    element.disabled = !allowed;
    element.onclick = () => chooseCard(card);
  }
  return element;
}

function render() {
  byId('entry').hidden = !!state;
  byId('arena').hidden = !state;
  if (!state) {
    byId('connection').textContent = '2–8인 멀티플레이';
    return;
  }
  if (renderedRevision === state.revision) return;
  renderedRevision = state.revision;
  if (byId('choice').open && choiceRevision !== state.revision) byId('choice').close();
  const playing = state.phase === 'playing';
  const myTurn = state.turn === state.you;
  const host = state.host === state.you;
  const turnName = state.players.find((player) => player.id === state.turn)?.name;
  const winner = state.players.find((player) => player.id === state.winner)?.name;
  byId('copy').textContent = `방 코드 ${state.code} · 복사`;
  byId('round-label').textContent = state.round ? `라운드 ${state.round} · 3승 선착` : '대기실';
  byId('headline').textContent = playing ? (myTurn ? '내 차례' : `${turnName} 님 차례`) : (winner ? `${winner} 님 ${state.phase === 'finished' ? '대회 우승' : '승리'}!` : 'UNO Championship');
  byId('lobby').hidden = playing;
  byId('table-play').hidden = !playing;
  byId('hand-area').hidden = !playing;
  byId('lobby-title').textContent = state.phase === 'finished' ? '대회 종료' : state.phase === 'between' ? '라운드 종료' : '플레이어 대기 중';
  byId('lobby-text').textContent = state.players.length < 2 ? '친구에게 방 코드를 보내세요. 2명부터 시작할 수 있습니다.' : host ? '시작하면 추가 규칙 두 가지가 공개됩니다.' : '방장이 시작하면 추가 규칙 두 가지가 공개됩니다.';
  byId('start').hidden = !host;
  byId('start').disabled = state.players.length < 2;
  byId('start').textContent = state.phase === 'finished' ? '새 대회 시작' : state.round ? '다음 라운드' : '라운드 시작';

  byId('players').replaceChildren(...state.players.map((player) => {
    const item = el('li', undefined, `player${player.id === state.turn ? ' active' : ''}`);
    const name = `${player.name}${player.id === state.you ? ' (나)' : ''}${player.id === state.host ? ' · 방장' : ''}`;
    item.append(el('span', name), el('span', `${player.wins}승${playing ? ` · ${player.count}장` : ''}`));
    return item;
  }));
  byId('rules-heading').textContent = playing ? '이번 라운드의 추가 규칙' : '추가 규칙 후보';
  const ruleCards = state.rules.map((rule) => {
    const item = el('div', undefined, 'rule');
    item.append(el('strong', rule.name), el('p', rule.description));
    return item;
  });
  if (!playing) ruleCards.unshift(el('p', '라운드를 시작하면 아래 규칙 중 2개가 무작위로 적용됩니다.'));
  byId('rules').replaceChildren(...ruleCards);
  byId('events').replaceChildren(...state.events.map((event) => el('li', event)));
  if (!playing) {
    byId('uno').checked = false;
    return;
  }
  byId('deck').textContent = `덱 ${state.deck}장`;
  byId('top-card').replaceChildren(makeCard(state.top, false, false));
  byId('active-color').textContent = `현재 색 · ${colors[state.color]}`;
  const direction = state.direction === 1 ? '정방향 ↻' : '역방향 ↺';
  byId('turn-detail').textContent = state.pending ? `${direction} · 누적 공격 +${state.pending}장` : direction;
  byId('draw').disabled = !state.canDraw;
  byId('draw').textContent = state.pending ? `공격 받기 (+${state.pending})` : '카드 뽑기';
  byId('pass').hidden = !state.canPass;
  byId('catch').hidden = !state.exposed || state.exposed === state.you;
  byId('hand-title').textContent = `내 손패 · ${state.hand.length}장`;
  byId('hand-hint').textContent = !myTurn ? '내 차례를 기다리는 중' : state.canPass ? '방금 뽑은 카드를 내거나 턴을 넘기세요.' : state.canPlay.length ? '낼 수 있는 카드가 밝게 표시됩니다.' : '낼 수 있는 카드가 없습니다. 카드를 뽑으세요.';
  byId('hand').replaceChildren(...state.hand.map((card) => makeCard(card, state.canPlay.includes(card.id), true)));
}

function accept(next) {
  if (!state || next.revision >= state.revision) {
    state = next;
    render();
  }
  byId('connection').textContent = '서버 연결됨';
}

function clearRoom() {
  saveSession(null);
  state = null;
  renderedRevision = null;
  if (byId('choice').open) byId('choice').close();
  render();
}

function problem(error) {
  if (error.status === 401 || error.status === 404) clearRoom();
  notice(error.status ? error.message : '연결이 끊겼거나 서버가 시작 중입니다. 잠시 뒤 다시 시도해 주세요.');
}

function roomPath(operation, active = session) {
  return `/api/room/${active.code}/${operation}`;
}

async function poll() {
  const active = session;
  if (active && !busy) {
    try {
      const next = await request(roomPath('state', active), undefined, active.token);
      if (session === active && !busy) accept(next);
    } catch (error) {
      if (session === active && !busy) {
        byId('connection').textContent = '서버 다시 연결 중…';
        if (error.status === 401 || error.status === 404) problem(error);
      }
    }
  }
  setTimeout(poll, 900);
}

async function move(action, details = {}) {
  if (!session || !state || busy) return;
  busy = true;
  notice();
  try {
    const next = await request(roomPath('move'), {action, revision: state.revision, ...details}, session.token);
    if (action === 'play') byId('uno').checked = false;
    accept(next);
  } catch (error) {
    problem(error);
  } finally {
    busy = false;
  }
}

function showOptions(title, options, onSelect) {
  const dialog = byId('choice');
  choiceRevision = state.revision;
  byId('choice-title').textContent = title;
  byId('options').replaceChildren(...options.map(({value, label, color}) => {
    const button = el('button', label, color ? `option ${color}` : 'option');
    button.type = 'button';
    button.onclick = () => {
      dialog.close();
      if (state?.revision === choiceRevision) onSelect(value);
    };
    return button;
  }));
  dialog.showModal();
}

function chooseCard(card) {
  if (!state?.canPlay.includes(card.id) || busy) return;
  const details = {card: card.id, uno: byId('uno').checked};
  if (card.color === 'wild') {
    const options = Object.entries(colors).filter(([color]) => color !== 'wild').map(([color, label]) => ({value: color, color, label}));
    showOptions('다음 색을 고르세요', options, (color) => move('play', {...details, color}));
  } else if (card.value === '7' && state.hand.length > 1 && state.rules.some((rule) => rule.key === 'seven')) {
    const options = state.players.filter((player) => player.id !== state.you).map((player) => ({value: player.id, label: player.name}));
    showOptions('손패를 교환할 상대', options, (target) => move('play', {...details, target}));
  } else {
    move('play', details);
  }
}

byId('entry-form').onsubmit = async (event) => {
  event.preventDefault();
  if (busy) return;
  const operation = event.submitter?.value || 'create';
  const code = byId('code').value.trim().toUpperCase();
  if (operation === 'join' && !/^[A-Z2-9]{6}$/.test(code)) {
    notice('6자리 방 코드를 확인해 주세요.');
    return;
  }
  busy = true;
  notice();
  try {
    const result = await request(`/api/${operation}`, {name: byId('name').value, code});
    renderedRevision = null;
    state = null;
    saveSession({code: result.state.code, token: result.token});
    accept(result.state);
  } catch (error) {
    problem(error);
  } finally {
    busy = false;
  }
};

byId('copy').onclick = async () => {
  if (!state) return;
  try {
    await navigator.clipboard.writeText(state.code);
    notice('방 코드를 복사했습니다.');
  } catch {
    notice(`방 코드 ${state.code}를 친구에게 보내세요.`);
  }
};

byId('leave').onclick = async () => {
  if (!session || busy) return;
  if (state.phase === 'playing' && !window.confirm('나가면 현재 라운드가 종료됩니다. 방을 나갈까요?')) return;
  busy = true;
  notice();
  try {
    await request(roomPath('leave'), {}, session.token);
    clearRoom();
  } catch (error) {
    problem(error);
  } finally {
    busy = false;
  }
};

byId('start').onclick = () => move('start');
byId('draw').onclick = () => move('draw');
byId('pass').onclick = () => move('pass');
byId('catch').onclick = () => move('catch');
poll();
