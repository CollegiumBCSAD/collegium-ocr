import re

from .engine import read_text
from .schemas import ScannedPlayer

GAMES = {"VALORANT", "LOL", "CODM", "MLBB"}

DIGIT_LOOKALIKES = str.maketrans("OoIlSBZ", "0011582")
KDA_RE = re.compile(
    r"([\dOoIlSBZ]{1,3})\s*/\s*([\dOoIlSBZ]{1,3})\s*/\s*([\dOoIlSBZ]{1,3})"
)
COUNT_RE = re.compile(r"[A-Za-z]*\d+")
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


def _cluster_rows(items, tol):
    ordered = sorted(items, key=lambda it: _ycenter(it[0]))
    rows, current, center = [], [], None
    for item in ordered:
        yc = _ycenter(item[0])
        if center is None or abs(yc - center) <= tol:
            current.append(item)
            center = yc if center is None else (center + yc) / 2
        else:
            rows.append(current)
            current, center = [item], yc
    if current:
        rows.append(current)
    return rows


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


def _split_columns(image, x0, y0, x1, y1):
    height, width = image.shape[:2]
    x0, x1 = max(0, int(x0) - 8), min(width, int(x1) + 8)
    y0, y1 = max(0, int(y0) - 6), min(height, int(y1) + 6)
    crop = image[y0:y1, x0:x1]
    if crop.size == 0:
        return []

    gray = crop.mean(axis=2)
    lit = (gray > (gray.max() + gray.min()) / 2).any(axis=0)

    runs, start = [], None
    for i, on in enumerate(lit):
        if on and start is None:
            start = i
        elif not on and start is not None:
            runs.append([start, i])
            start = None
    if start is not None:
        runs.append([start, len(lit)])

    gap = max(6.0, (y1 - y0) * 0.35)
    merged = []
    for begin, end in runs:
        if merged and begin - merged[-1][1] < gap:
            merged[-1][1] = end
        else:
            merged.append([begin, end])

    texts = []
    for begin, end in merged:
        if end - begin < 4:
            continue
        text = read_text(image[y0:y1, x0 + max(0, begin - 4) : x0 + end + 4]).strip()
        if text:
            texts.append(text)
    return texts


def _mlbb_name(row, x0, x1, right):
    if right:
        after = [(b, t) for b, t, _ in row if _is_name(t) and _bounds(b)[0] >= x1]
        return min(after, key=lambda c: _bounds(c[0])[0])[1] if after else ""
    before = [(b, t) for b, t, _ in row if _is_name(t) and _bounds(b)[2] <= x0]
    return max(before, key=lambda c: _bounds(c[0])[2])[1] if before else ""


def _parse_mlbb(items, image, tol):
    if image is None:
        return []

    middle = image.shape[1] / 2
    players = []
    for row in _cluster_rows(items, tol):
        for right in (False, True):
            boxes = [
                b
                for b, t, _ in row
                if COUNT_RE.fullmatch(t)
                and ((_bounds(b)[0] + _bounds(b)[2]) / 2 > middle) == right
            ]
            if not boxes:
                continue

            bounds = [_bounds(b) for b in boxes]
            x0 = min(b[0] for b in bounds)
            y0 = min(b[1] for b in bounds)
            x1 = max(b[2] for b in bounds)
            y1 = max(b[3] for b in bounds)

            texts = _split_columns(image, x0, y0, x1, y1)
            digits = [t for t in texts if t.isdigit()]
            if len(digits) < 4:
                continue
            if right:
                gold, kills, deaths, assists = (int(t) for t in digits[:4])
            else:
                kills, deaths, assists, gold = (int(t) for t in digits[-4:])

            ign = _mlbb_name(row, x0, x1, right) or " ".join(
                t for t in texts if not t.isdigit()
            )
            if not _is_name(ign):
                continue

            players.append(
                ScannedPlayer(
                    ign=ign.strip(),
                    team=None,
                    kills=kills,
                    deaths=deaths,
                    assists=assists,
                    extra={"gold": gold},
                )
            )
    return players


def parse(game: str, items, image=None) -> list[ScannedPlayer]:
    game = game.upper()
    if not items:
        return []

    ordered = sorted(items, key=lambda it: (_ycenter(it[0]), _xleft(it[0])))
    tol = _median_line_height(items) * 0.8

    if game == "MLBB":
        return _parse_mlbb(ordered, image, tol)
    return _parse_kda_columns(game, ordered, tol)
