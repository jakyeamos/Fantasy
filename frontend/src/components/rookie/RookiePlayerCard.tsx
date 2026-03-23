import type { RookiePlayer } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

const RISK_BORDER: Record<RookiePlayer["risk_band"], string> = {
  Low: "border-l-green-500",
  Moderate: "border-l-amber-400",
  High: "border-l-red-400",
}

const RISK_BADGE: Record<RookiePlayer["risk_band"], string> = {
  Low: "bg-green-50 text-green-700 dark:bg-green-950/20 dark:text-green-300",
  Moderate: "bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-300",
  High: "bg-red-50 text-red-600 dark:bg-red-950/20 dark:text-red-400",
}

export function RookiePlayerCard({
  player,
  isAvailableAtSlot = false,
  selectedSlot,
}: {
  player: RookiePlayer
  isAvailableAtSlot?: boolean
  selectedSlot?: string
}) {
  return (
    <Card
      className={cn(
        "border-l-4",
        RISK_BORDER[player.risk_band],
        isAvailableAtSlot && "bg-primary/10",
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-medium">{player.full_name}</p>
          <Badge variant="outline">{player.position}</Badge>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{player.archetype_label}</p>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-muted-foreground">{player.risk_band} risk</span>
          <span className={cn("rounded px-2 py-0.5 text-xs font-medium", RISK_BADGE[player.risk_band])}>
            {player.risk_band}
          </span>
        </div>
        {isAvailableAtSlot && selectedSlot ? (
          <p className="mt-2 text-xs text-primary">Available at ~{selectedSlot}</p>
        ) : null}
      </CardContent>
    </Card>
  )
}
