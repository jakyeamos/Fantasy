import { Check } from "lucide-react"

import type { ExposureRow } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { badgeToneClasses, textToneClasses } from "@/lib/ui-tokens"
import { cn } from "@/lib/utils"

interface LeagueColumn {
  leagueId: string
  leagueName: string
}

function ConcentrationBadge({ count }: { count: number }) {
  if (count >= 3) {
    return (
      <Badge className={badgeToneClasses.destructive}>{count} leagues</Badge>
    )
  }
  if (count === 2) {
    return <Badge className={badgeToneClasses.warning}>2 leagues</Badge>
  }
  return <Badge className="bg-muted text-muted-foreground">1 league</Badge>
}

function sortExposureRows(rows: ExposureRow[]) {
  const urgencyRank: Record<ExposureRow["urgency"], number> = {
    sell: 0,
    hedge: 1,
    monitor: 2,
    hold: 3,
  }
  return [...rows].sort(
    (a, b) =>
      urgencyRank[a.urgency] - urgencyRank[b.urgency] ||
      b.league_count - a.league_count ||
      a.full_name.localeCompare(b.full_name),
  )
}

export function ExposureMatrix({
  rows,
  leagueColumns,
  isLoading,
  isError,
  highlightedPlayerId,
}: {
  rows: ExposureRow[]
  leagueColumns: LeagueColumn[]
  isLoading?: boolean
  isError?: boolean
  highlightedPlayerId?: string
}) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-8 w-full rounded" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <p className="text-sm text-muted-foreground">
        Portfolio data unavailable. Check that the backend is running, then
        refresh.
      </p>
    )
  }

  if (!rows.length) {
    return (
      <p className="text-center text-sm text-muted-foreground">
        No players owned across multiple leagues.
      </p>
    )
  }

  const sortedRows = sortExposureRows(rows)

  return (
    <div className="overflow-x-auto rounded-xl border border-border/60">
      <table className="w-full text-sm">
        <thead className="bg-muted/40">
          <tr>
            <th className="px-3 py-3 text-left text-xs font-normal text-muted-foreground">
              Player
            </th>
            {leagueColumns.map((column) => (
              <th
                key={column.leagueId}
                className="px-3 py-3 text-center text-xs font-normal text-muted-foreground"
                title={column.leagueName}
              >
                <span className="block max-w-[8rem] truncate">
                  {column.leagueName}
                </span>
              </th>
            ))}
            <th className="px-3 py-3 text-left text-xs font-normal text-muted-foreground">
              Exposure
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row, index) => (
            <tr
              key={row.player_id}
              className={cn(
                index % 2 === 1 && "bg-muted/30",
                highlightedPlayerId === row.player_id &&
                  "bg-primary/10 outline outline-2 outline-primary/45",
              )}
            >
              <td className="px-3 py-3 align-top">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-foreground">
                    {row.full_name}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {row.position}
                  </Badge>
                </div>
              </td>
              {leagueColumns.map((column) => (
                <td
                  key={column.leagueId}
                  className="px-3 py-3 text-center align-top"
                >
                  {row.owned_in_leagues.includes(column.leagueId) ? (
                    <Check
                      className={`mx-auto size-4 ${textToneClasses.success}`}
                    />
                  ) : null}
                </td>
              ))}
              <td className="px-3 py-3 align-top">
                <div className="space-y-1">
                  <ConcentrationBadge count={row.league_count} />
                  <Badge
                    variant={
                      row.urgency === "sell"
                        ? "default"
                        : row.urgency === "hedge"
                          ? "secondary"
                          : "outline"
                    }
                  >
                    {row.urgency}
                  </Badge>
                  {row.hedge_rec ? (
                    <p className="text-xs italic text-muted-foreground">
                      {row.hedge_rec}
                    </p>
                  ) : null}
                  {row.urgency_reason ? (
                    <p className="text-xs text-muted-foreground">
                      {row.urgency_reason}
                    </p>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
