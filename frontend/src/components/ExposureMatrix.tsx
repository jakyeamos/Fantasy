import { Check } from "lucide-react"

import type { ExposureRow } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

interface LeagueColumn {
  leagueId: string
  leagueName: string
}

function ConcentrationBadge({ count }: { count: number }) {
  if (count >= 3) {
    return (
      <Badge className="bg-red-50 text-red-600 dark:bg-red-950/20 dark:text-red-400">
        {count} leagues
      </Badge>
    )
  }
  if (count === 2) {
    return (
      <Badge className="bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-300">
        2 leagues
      </Badge>
    )
  }
  return (
    <Badge className="bg-muted text-muted-foreground">
      1 league
    </Badge>
  )
}

function sortExposureRows(rows: ExposureRow[]) {
  const rank = (row: ExposureRow) => (row.league_count >= 3 ? 0 : row.league_count === 2 ? 1 : 2)
  return [...rows].sort(
    (a, b) => rank(a) - rank(b) || a.full_name.localeCompare(b.full_name),
  )
}

export function ExposureMatrix({
  rows,
  leagueColumns,
  isLoading,
  isError,
}: {
  rows: ExposureRow[]
  leagueColumns: LeagueColumn[]
  isLoading?: boolean
  isError?: boolean
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
        Portfolio data unavailable. Check that the backend is running, then refresh.
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
              className={cn(index % 2 === 1 && "bg-muted/30")}
            >
              <td className="px-3 py-3 align-top">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-foreground">{row.full_name}</span>
                  <Badge variant="outline" className="text-xs">
                    {row.position}
                  </Badge>
                </div>
              </td>
              {leagueColumns.map((column) => (
                <td key={column.leagueId} className="px-3 py-3 text-center align-top">
                  {row.owned_in_leagues.includes(column.leagueId) ? (
                    <Check className="mx-auto size-4 text-green-700 dark:text-green-300" />
                  ) : null}
                </td>
              ))}
              <td className="px-3 py-3 align-top">
                <div className="space-y-1">
                  <ConcentrationBadge count={row.league_count} />
                  {row.hedge_rec ? (
                    <p className="text-xs italic text-muted-foreground">
                      {row.hedge_rec}
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
