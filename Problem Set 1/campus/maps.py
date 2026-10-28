"""Map parsing and metadata only; students implement the world transitions."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MapSpec:
    rows: tuple[str, ...]

    def __post_init__(self):
        object.__setattr__(self, "rows", tuple(self.rows))
        if not self.rows or not self.rows[0] or any(len(row) != len(self.rows[0]) for row in self.rows):
            raise ValueError("Use a nonempty rectangular map")
        if set("".join(self.rows)) - set("SGKD#w."):
            raise ValueError("Unknown map symbol")
        if any(len(self.locations(symbol)) != 1 for symbol in "SG"):
            raise ValueError("Exactly one S and one G are required")
        if len(self.locations("K")) > 1:
            raise ValueError("At most one required pickup is supported")

    @classmethod
    def from_file(cls, path):
        return cls(tuple(Path(path).read_text(encoding="utf-8").splitlines()))

    @property
    def height(self):
        return len(self.rows)

    @property
    def width(self):
        return len(self.rows[0])

    def locations(self, symbol):
        return [(row, column) for row, tiles in enumerate(self.rows) for column, tile in enumerate(tiles) if tile == symbol]

    @property
    def start(self):
        return self.locations("S")[0]

    @property
    def goal(self):
        return self.locations("G")[0]

    @property
    def pickup(self):
        locations = self.locations("K")
        return locations[0] if locations else None
