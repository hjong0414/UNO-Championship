"""Server-side rules for UNO Championship."""

from collections import deque
from dataclasses import dataclass, field
from itertools import combinations
from random import SystemRandom
from time import monotonic


COLORS = {"red": "빨강", "yellow": "노랑", "green": "초록", "blue": "파랑"}
LABELS = {"skip": "건너뛰기", "reverse": "방향 전환", "draw2": "+2",
          "wild": "와일드", "draw4": "+4"}
ATTACKS = {"draw2": 2, "draw4": 4}
RULES = {
    "stack": ("공격 누적", "같은 종류의 +2 또는 +4로만 공격을 넘길 수 있습니다. +4의 색 제한은 적용됩니다."),
    "zero": ("0 카드 돌리기", "0을 내면 모두가 진행 방향의 다음 사람에게 손패를 넘깁니다."),
    "seven": ("7 카드 교환", "7을 내면 지정한 상대 한 명과 손패 전체를 교환합니다."),
    "draw_until": ("나올 때까지 뽑기", "뽑기를 시작하면 낼 수 있는 카드가 나올 때까지 뽑습니다. 그 카드를 내거나 턴을 넘길 수 있습니다."),
    "nine": ("9장 스타트", "이번 라운드는 각자 카드 9장으로 시작합니다."),
    "double_skip": ("더블 스킵", "건너뛰기 카드가 상대를 최대 두 명까지 건너뜁니다."),
}
RULE_PAIRS = tuple(combinations(RULES, 2))
RNG = SystemRandom()


class GameError(Exception):
    pass


@dataclass(frozen=True)
class Card:
    id: int
    color: str
    value: str


def make_deck():
    faces = [(color, "0") for color in COLORS]
    for color in COLORS:
        for value in (*map(str, range(1, 10)), "skip", "reverse", "draw2"):
            faces.extend([(color, value)] * 2)
    faces.extend([("wild", "wild"), ("wild", "draw4")] * 4)
    deck = [Card(index, color, value) for index, (color, value) in enumerate(faces)]
    RNG.shuffle(deck)
    return deck


@dataclass
class Player:
    id: str
    token: str
    name: str
    wins: int = 0
    hand: list = field(default_factory=list)


@dataclass
class Room:
    code: str
    players: list
    phase: str = "lobby"
    rules: tuple = ()
    deck: list = field(default_factory=list)
    pile: list = field(default_factory=list)
    events: deque = field(default_factory=lambda: deque(maxlen=14))
    revision: int = 0
    touched: float = field(default_factory=monotonic)
    round: int = 0
    turn: int = 0
    direction: int = 1
    color: str = ""
    drawn: int | None = None
    pending: int = 0
    exposed: str | None = None
    winner: str | None = None

    def record(self, message):
        self.events.appendleft(message)

    def add(self, player):
        if self.phase != "lobby" or self.round:
            raise GameError("대회가 이미 시작됐습니다. 새 방을 만들어 주세요.")
        if len(self.players) >= 8:
            raise GameError("방에 최대 8명까지 들어갈 수 있습니다.")
        if any(member.name.casefold() == player.name.casefold() for member in self.players):
            raise GameError("이미 쓰고 있는 닉네임입니다.")
        self.players.append(player)
        self.record(f"{player.name} 님이 입장했습니다.")

    def leave(self, player):
        self.players.remove(player)
        self.record(f"{player.name} 님이 나갔습니다.")
        if self.phase == "playing":
            self.phase = "between"
            self.winner = None
            self.exposed = None
            self.record("현재 라운드를 종료했습니다. 다음 라운드를 시작할 수 있습니다.")

    def start(self, player):
        if player is not self.players[0]:
            raise GameError("방장만 라운드를 시작할 수 있습니다.")
        if self.phase == "playing" or len(self.players) < 2:
            raise GameError("라운드를 시작하려면 대기 중인 플레이어가 2명 이상 필요합니다.")
        if self.phase == "finished":
            self.round = 0
            for member in self.players:
                member.wins = 0
        self.round += 1
        self.rules = RNG.choice([pair for pair in RULE_PAIRS if pair != self.rules])
        self.deck = make_deck()
        self.pile = [self.deck.pop(next(index for index, card in enumerate(self.deck) if card.value.isdigit()))]
        self.color = self.pile[-1].color
        for member in self.players:
            member.hand = self.take(9 if "nine" in self.rules else 7)
        self.phase = "playing"
        self.turn = (self.round - 1) % len(self.players)
        self.direction = 1
        self.drawn = None
        self.pending = 0
        self.exposed = None
        self.winner = None
        self.record(f"{self.round}라운드 시작 · {' + '.join(RULES[key][0] for key in self.rules)}")

    def take(self, amount):
        cards = []
        for _ in range(amount):
            if not self.deck and len(self.pile) > 1:
                self.deck = self.pile[:-1]
                self.pile = self.pile[-1:]
                RNG.shuffle(self.deck)
            if not self.deck:
                break
            cards.append(self.deck.pop())
        return cards

    def playable(self, player, card):
        top = self.pile[-1]
        if self.drawn is not None and self.drawn != card.id:
            return False
        if self.pending and ("stack" not in self.rules or card.value != top.value):
            return False
        if card.value == "draw4":
            return all(other.color != self.color for other in player.hand)
        return card.color in {"wild", self.color} or card.value == top.value

    def advance(self, steps=1):
        self.turn = (self.turn + self.direction * steps) % len(self.players)
        self.drawn = None

    def action(self, player, data):
        if self.phase != "playing":
            raise GameError("진행 중인 라운드가 없습니다.")
        kind = data.get("action")
        if kind == "catch":
            target = next((member for member in self.players if member.id == self.exposed), None)
            if target is None or target is player:
                raise GameError("지금 지적할 수 있는 상대가 없습니다.")
            penalty = self.take(2)
            target.hand.extend(penalty)
            self.exposed = None
            self.record(f"{player.name} 님이 {target.name} 님의 UNO를 지적했습니다. +{len(penalty)}장")
            return
        if self.players[self.turn] is not player:
            raise GameError("내 차례에만 할 수 있습니다.")
        if kind == "play":
            self.play(player, data)
        elif kind == "draw" and self.drawn is None:
            self.draw(player)
        elif kind == "pass" and self.drawn is not None:
            self.exposed = None
            self.record(f"{player.name} 님이 차례를 넘겼습니다.")
            self.advance()
        else:
            raise GameError("지금 할 수 없는 행동입니다.")

    def draw(self, player):
        self.exposed = None
        if self.pending:
            cards = self.take(self.pending)
            player.hand.extend(cards)
            self.record(f"{player.name} 님이 공격을 받아 {len(cards)}장을 뽑았습니다.")
            self.pending = 0
            self.advance()
            return
        amount = 0
        while cards := self.take(1):
            card = cards[0]
            player.hand.append(card)
            amount += 1
            if self.playable(player, card):
                self.drawn = card.id
                break
            if "draw_until" not in self.rules:
                break
        self.record(f"{player.name} 님이 {amount}장을 뽑았습니다.")
        if self.drawn is None:
            self.advance()

    def play(self, player, data):
        card_id = data.get("card")
        card = next((item for item in player.hand if type(card_id) is int and item.id == card_id), None)
        if card is None or not self.playable(player, card):
            raise GameError("지금 낼 수 없는 카드입니다.")
        color = data.get("color") if card.color == "wild" else card.color
        if not isinstance(color, str) or color not in COLORS:
            raise GameError("다음 색을 선택해 주세요.")
        swap = None
        if len(player.hand) > 1 and card.value == "7" and "seven" in self.rules:
            swap = next((member for member in self.players if member.id == data.get("target") and member is not player), None)
            if swap is None:
                raise GameError("카드를 교환할 상대를 선택해 주세요.")
        self.exposed = None
        player.hand.remove(card)
        self.pile.append(card)
        self.color = color
        self.record(f"{player.name} 님이 {COLORS[color]} {LABELS.get(card.value, card.value)} 카드를 냈습니다.")
        if not player.hand:
            player.wins += 1
            self.winner = player.id
            self.phase = "finished" if player.wins >= 3 else "between"
            self.pending = 0
            self.record(f"{player.name} 님이 {'대회' if self.phase == 'finished' else '라운드'}에서 우승했습니다!")
            return

        steps = 1
        if card.value == "reverse":
            self.direction *= -1
            if len(self.players) == 2:
                steps = 2
        elif card.value == "skip":
            steps = min(len(self.players), 3) if "double_skip" in self.rules else 2
        elif card.value in ATTACKS:
            attack = ATTACKS[card.value]
            if "stack" in self.rules:
                self.pending += attack
            else:
                target = self.players[(self.turn + self.direction) % len(self.players)]
                cards = self.take(attack)
                target.hand.extend(cards)
                self.record(f"{target.name} 님이 공격을 받아 {len(cards)}장을 뽑았습니다.")
                steps = 2
        elif card.value == "0" and "zero" in self.rules:
            hands = [member.hand for member in self.players]
            for index, member in enumerate(self.players):
                member.hand = hands[(index - self.direction) % len(self.players)]
            self.record("모두 진행 방향으로 손패를 넘겼습니다.")
        elif swap:
            player.hand, swap.hand = swap.hand, player.hand
            self.record(f"{player.name} 님과 {swap.name} 님이 손패를 교환했습니다.")

        if len(player.hand) == 1:
            if data.get("uno") is True:
                self.record(f"{player.name} 님이 UNO를 외쳤습니다!")
            else:
                self.exposed = player.id
        self.advance(steps)

    def view(self, player):
        playing = self.phase == "playing"
        current = self.players[self.turn] if playing else None
        my_turn = current is player
        return {
            "code": self.code, "phase": self.phase, "revision": self.revision,
            "round": self.round, "you": player.id, "host": self.players[0].id,
            "players": [{"id": member.id, "name": member.name, "wins": member.wins,
                         "count": len(member.hand) if playing else None} for member in self.players],
            "rules": [{"key": key, "name": RULES[key][0], "description": RULES[key][1]} for key in self.rules],
            "hand": [vars(card) for card in player.hand] if playing else [],
            "top": vars(self.pile[-1]) if playing else None, "color": self.color,
            "turn": current.id if current else None, "direction": self.direction,
            "deck": len(self.deck), "pending": self.pending if playing else 0,
            "exposed": self.exposed if playing else None, "winner": self.winner,
            "canPlay": [card.id for card in player.hand if self.playable(player, card)] if my_turn else [],
            "canDraw": my_turn and self.drawn is None, "canPass": my_turn and self.drawn is not None,
            "events": list(self.events),
        }
