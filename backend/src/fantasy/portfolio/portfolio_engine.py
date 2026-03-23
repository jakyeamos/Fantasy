from __future__ import annotations

import duckdb

from fantasy.portfolio.constants import CONCENTRATION_HEDGE_THRESHOLD
from fantasy.portfolio.models import CorrelatedRiskRow, ExposureRow
from fantasy.portfolio.portfolio_repo import PortfolioRepo


def _first_unique_names(row: CorrelatedRiskRow) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for player in row.players:
        if player.player_id in seen:
            continue
        seen.add(player.player_id)
        names.append(player.full_name)
    return names


class PortfolioEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._repo = PortfolioRepo(conn)

    def compute_exposure(self) -> list[ExposureRow]:
        rows = self._repo.load_exposure_rows()
        for row in rows:
            if row.league_count >= CONCENTRATION_HEDGE_THRESHOLD:
                row.hedge_rec = (
                    f"{row.full_name} is on {row.league_count} rosters - "
                    "consider trading in your most contending league to reduce exposure"
                )
        return rows

    def compute_correlated_risk(self) -> list[CorrelatedRiskRow]:
        rows = self._repo.load_correlated_risk_rows()
        for row in rows:
            unique_names = _first_unique_names(row)
            if len(unique_names) > 3:
                player_label = " + ".join(unique_names[:3]) + f" + {len(unique_names) - 3} more"
            else:
                player_label = " + ".join(unique_names)

            player_count = len(unique_names)
            if player_count <= 2:
                impact_label = "both"
            elif player_count == 3:
                impact_label = "all three"
            else:
                impact_label = f"all {player_count}"

            row.risk_string = (
                f"{player_label} across {len(row.league_ids)} leagues - "
                f"one {row.nfl_team} collapse hits {impact_label}"
            )
        return rows
