import numpy as np

from app import parsers
from app.parsers import parse


def box(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def test_valorant_picks_name_above_agent():
    items = [
        (box(335, 325, 451, 352), "NU Arguelles", 0.95),
        (box(336, 349, 376, 367), "NEON", 0.99),
        (box(599, 337, 631, 355), "317", 1.0),
        (box(703, 336, 784, 356), "18/13/5", 0.98),
    ]
    players = parse("VALORANT", items)
    assert len(players) == 1
    assert players[0].ign == "NU Arguelles"
    assert (players[0].kills, players[0].deaths, players[0].assists) == (18, 13, 5)


def test_lol_picks_name_not_champion():
    items = [
        (box(10, 100, 40, 130), "18", 0.9),
        (box(50, 100, 140, 130), "Ambessa", 0.9),
        (box(150, 100, 230, 130), "awtysm", 0.95),
        (box(250, 100, 320, 130), "8/2/10", 0.95),
        (box(340, 100, 420, 130), "30,134", 0.9),
    ]
    players = parse("LOL", items)
    assert len(players) == 1
    assert players[0].ign == "awtysm"
    assert (players[0].kills, players[0].deaths, players[0].assists) == (8, 2, 10)


def test_team_total_row_is_filtered():
    items = [
        (box(10, 100, 80, 130), "TEAM1", 0.9),
        (box(90, 100, 180, 130), "40/16/48", 0.95),
        (box(200, 100, 260, 130), "65,183", 0.9),
    ]
    assert parse("LOL", items) == []


def test_codm_splits_side_by_side_tables():
    items = [
        (box(258, 326, 354, 360), "ARDE Law", 0.91),
        (box(428, 326, 476, 360), "MVP", 0.99),
        (box(297, 373, 369, 402), "400", 0.99),
        (box(642, 348, 732, 379), "41/20/12", 0.99),
        (box(1214, 328, 1295, 360), "SY Josh.", 0.95),
        (box(1596, 346, 1689, 381), "23/32/B", 0.99),
    ]
    players = parse("CODM", items)
    assert [p.ign for p in players] == ["ARDE Law", "SY Josh."]
    assert (players[0].kills, players[0].deaths, players[0].assists) == (41, 20, 12)
    assert (players[1].kills, players[1].deaths, players[1].assists) == (23, 32, 8)


def _mlbb_image():
    image = np.zeros((900, 2048, 3), dtype=np.uint8)
    for x0, x1 in [(650, 670), (700, 720), (750, 770), (800, 844)]:
        image[683:710, x0:x1] = 255
    for x0, x1 in [(1207, 1250), (1290, 1310), (1340, 1360), (1380, 1398)]:
        image[683:710, x0:x1] = 255
    return image


def test_mlbb_reads_columns_per_side(monkeypatch):
    reads = iter(["6", "5", "17", "12813", "15502", "12", "7", "7"])
    monkeypatch.setattr(parsers, "read_text", lambda crop: next(reads))
    items = [
        (box(432, 684, 542, 712), "Apostatis", 0.99),
        (box(650, 683, 844, 710), "651712813", 0.99),
        (box(1207, 683, 1398, 710), "155021277", 1.0),
        (box(1475, 684, 1622, 709), "EnumaElish", 0.99),
    ]
    left, right = parse("MLBB", items, _mlbb_image())
    assert left.ign == "Apostatis"
    assert (left.kills, left.deaths, left.assists) == (6, 5, 17)
    assert left.extra == {"gold": 12813}
    assert right.ign == "EnumaElish"
    assert (right.kills, right.deaths, right.assists) == (12, 7, 7)
    assert right.extra == {"gold": 15502}


def test_mlbb_without_image_returns_nothing():
    items = [(box(650, 683, 844, 710), "651712813", 0.99)]
    assert parse("MLBB", items) == []


def test_empty_items():
    assert parse("CODM", []) == []
