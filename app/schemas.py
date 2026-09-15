from pydantic import BaseModel, Field


class ScannedPlayer(BaseModel):
    ign: str
    team: str | None = None
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    extra: dict = Field(default_factory=dict)


class ScanResult(BaseModel):
    game: str
    players: list[ScannedPlayer]
