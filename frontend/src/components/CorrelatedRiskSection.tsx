import { AlertTriangle } from "lucide-react"

import type { CorrelatedRiskRow } from "@/api/types"
import { Skeleton } from "@/components/ui/skeleton"
import { surfaceToneClasses, textToneClasses } from "@/lib/ui-tokens"

export function CorrelatedRiskSection({
  rows,
  isLoading,
  isError,
}: {
  rows: CorrelatedRiskRow[]
  isLoading?: boolean
  isError?: boolean
}) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 2 }).map((_, index) => (
          <Skeleton key={index} className="h-10 w-full rounded" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <p className="text-xs text-muted-foreground">
        Correlated risk data unavailable. Check that the backend is running, then refresh.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">Correlated NFL Team Risk</p>
      {rows.length ? (
        <div className="space-y-2">
          {rows.map((row) => (
            <div
              key={`${row.nfl_team}-${row.league_ids.join("-")}`}
              className={`flex items-start gap-2 rounded-md px-3 py-2 ${surfaceToneClasses.warning}`}
            >
              <AlertTriangle className={`mt-0.5 size-4 ${textToneClasses.warning}`} />
              <p className={`text-sm ${textToneClasses.warning}`}>
                {row.risk_string}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          No correlated NFL team clusters detected.
        </p>
      )}
    </div>
  )
}
