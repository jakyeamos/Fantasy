import type { HistoricalComp } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { badgeToneClasses } from "@/lib/ui-tokens"
import { cn } from "@/lib/utils"

const ROLE_STYLES: Record<HistoricalComp["role"], string> = {
  ceiling: badgeToneClasses.success,
  median: "text-muted-foreground",
  floor: badgeToneClasses.destructive,
}

const OUTCOME_STYLES: Record<HistoricalComp["outcome_bucket"], string> = {
  hit: badgeToneClasses.success,
  mediocre: badgeToneClasses.warning,
  bust: badgeToneClasses.destructive,
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
