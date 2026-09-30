import re

from .schemas import ScannedPlayer

GAMES = {"VALORANT", "LOL", "CODM", "MLBB"}

DIGIT_LOOKALIKES = str.maketrans("OoIlSBZ", "0011582")
KDA_RE = re.compile(
    r"([\dOoIlSBZ]{1,3})\s*/\s*([\dOoIlSBZ]{1,3})\s*/\s*([\dOoIlSBZ]{1,3})"
)
NON_PLAYER_LABELS = {"team1", "team2", "team", "total", "mvp"}


def _bounds(box):
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    return min(xs), min(ys), max(xs), max(ys)


def _ycenter(box):
    _, y0, _, y1 = _bounds(box)
    return (y0 + y1) / 2


def _xleft(box):
    return _bounds(box)[0]


def _has_alpha(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def _is_name(text: str) -> bool:
    return _has_alpha(text) and text.strip().lower() not in NON_PLAYER_LABELS


def _median_line_height(items) -> float:
    heights = sorted(
        h for h in (_bounds(box)[3] - _bounds(box)[1] for box, _, _ in items) if h > 0
    )
    return heights[len(heights) // 2] if heights else 20.0


def _parse_kda_columns(game, items, tol):
    players = []
    for box, text, _ in items:
        match = KDA_RE.search(text)
        if not match:
            continue
        x0, _, _, _ = _bounds(box)
        yc = _ycenter(box)
        names = [
            (b, t)
            for b, t, _ in items
            if _is_name(t) and _xleft(b) < x0 and abs(_ycenter(b) - yc) <= tol
        ]
        if not names:
            continue
        if game == "VALORANT":
            ign = min(names, key=lambda n: _ycenter(n[0]))[1]
        else:
            ign = max(names, key=lambda n: _xleft(n[0]))[1]
        kills, deaths, assists = (
            int(group.translate(DIGIT_LOOKALIKES)) for group in match.groups()
        )
        players.append(
            ScannedPlayer(
                ign=ign.strip(),
                team=None,
                kills=kills,
                deaths=deaths,
                assists=assists,
                extra={},
            )
        )
    return players


def parse(game: str, items) -> list[ScannedPlayer]:
    game = game.upper()
    if not items:
        return []

    ordered = sorted(items, key=lambda it: (_ycenter(it[0]), _xleft(it[0])))
    return _parse_kda_columns(game, ordered, _median_line_height(items) * 0.8)
