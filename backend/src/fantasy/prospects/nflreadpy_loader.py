from __future__ import annotations

from typing import Any

import polars as pl


def _optional_nflreadpy() -> Any | None:
    try:
        import nflreadpy  # type: ignore
    except ModuleNotFoundError:
        return None
    return nflreadpy


class NflReadPyLoader:
    def load_combine(self, start_year: int, end_year: int) -> pl.DataFrame:
        nflreadpy = _optional_nflreadpy()
        if nflreadpy is None:
            return pl.DataFrame()
        loader = getattr(nflreadpy, "load_combine", None)
        if loader is None:
            return pl.DataFrame()
        data = loader(seasons=list(range(start_year, end_year)))
        return self._to_polars(data)

    def load_players(self) -> pl.DataFrame:
        nflreadpy = _optional_nflreadpy()
        if nflreadpy is None:
            return pl.DataFrame()
        loader = getattr(nflreadpy, "load_players", None)
        if loader is None:
            return pl.DataFrame()
        data = loader()
        return self._to_polars(data)

    def load_draft_picks(self, start_year: int, end_year: int) -> pl.DataFrame:
        nflreadpy = _optional_nflreadpy()
        if nflreadpy is None:
            return pl.DataFrame()
        loader = getattr(nflreadpy, "load_draft_picks", None)
        if loader is None:
            return pl.DataFrame()
        data = loader(seasons=list(range(start_year, end_year)))
        return self._to_polars(data)

    def _to_polars(self, data: Any) -> pl.DataFrame:
        if isinstance(data, pl.DataFrame):
            return data
        if hasattr(data, "to_pandas"):
            maybe_pandas = data.to_pandas()
            if maybe_pandas is not None:
                return pl.from_pandas(maybe_pandas)
        if hasattr(data, "to_dicts"):
            return pl.DataFrame(data.to_dicts())
        if hasattr(data, "to_dict"):
            return pl.from_pandas(data)
        return pl.DataFrame(data)
