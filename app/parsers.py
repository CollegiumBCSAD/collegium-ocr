import re

from .schemas import ScannedPlayer

GAMES = {"VALORANT", "LOL", "CODM", "MLBB"}

KDA_RE = re.compile(r"(\d{1,3})\s*/\s*(\d{1,3})\s*/\s*(\d{1,3})")
NON_PLAYER_LABELS = {"team1", "team2", "team", "total"}


def _ycenter(box):
    return sum(point[1] for point in box) / len(box)


def _xleft(box):
    return min(point[0] for point in box)


def _has_alpha(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def _median_line_height(items) -> float:
    heights = [
        max(p[1] for p in box) - min(p[1] for p in box) for box, _, _ in items
    ]
    heights = sorted(h for h in heights if h > 0)
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


def _pick_ign(row_sorted, kda_idx, game) -> str:
    left = row_sorted[:kda_idx]
    alpha = [text for _, text, _ in left if _has_alpha(text)]
    if game == "LOL":
        return alpha[-1] if alpha else ""
    if alpha:
        return alpha[0]
    return left[0][1] if left else ""


def parse(game: str, items) -> list[ScannedPlayer]:
    game = game.upper()
    if not items:
        return []

    tol = _median_line_height(items) * 0.6
    players: list[ScannedPlayer] = []

    for row in _cluster_rows(items, tol):
        row_sorted = sorted(row, key=lambda it: _xleft(it[0]))
        texts = [text for _, text, _ in row_sorted]
        joined = " ".join(texts)

        match = KDA_RE.search(joined)
        if not match:
            continue

        kda_idx = next(
            (i for i, text in enumerate(texts) if KDA_RE.search(text)), len(texts)
        )
        ign = _pick_ign(row_sorted, kda_idx, game).strip()
        if not _has_alpha(ign) or ign.lower() in NON_PLAYER_LABELS:
            continue

        players.append(
            ScannedPlayer(
                ign=ign,
                team=None,
                kills=int(match.group(1)),
                deaths=int(match.group(2)),
                assists=int(match.group(3)),
                extra={},
            )
        )

    return players
