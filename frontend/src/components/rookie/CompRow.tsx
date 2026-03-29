import type { HistoricalComp } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const ROLE_STYLES: Record<HistoricalComp["role"], string> = {
  ceiling: "border-green-500 text-green-700 dark:text-green-300",
  median: "text-muted-foreground",
  floor: "border-red-400 text-red-600 dark:text-red-400",
}

const OUTCOME_STYLES: Record<HistoricalComp["outcome_bucket"], string> = {
  hit: "bg-green-50 text-green-700 dark:bg-green-950/20 dark:text-green-300",
  mediocre: "bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-300",
  bust: "bg-red-50 text-red-600 dark:bg-red-950/20 dark:text-red-400",
}

export function CompRow({ comp }: { comp: HistoricalComp }) {
  return (
    <div className="flex items-start gap-2 rounded-md bg-muted/20 p-2">
      <div className="w-16 shrink-0 space-y-1">
        <Badge variant="outline" className={cn("capitalize", ROLE_STYLES[comp.role])}>
          {comp.role}
        </Badge>
        <Badge className={OUTCOME_STYLES[comp.outcome_bucket]}>{comp.outcome_bucket}</Badge>
      </div>
      <div className="min-w-0 flex-1">
        <p className="terminal-label text-foreground/85">{comp.player_name}</p>
        <p className="mt-1 text-sm leading-tight text-muted-foreground">{comp.match_reason}</p>
      </div>
    </div>
  )
}
