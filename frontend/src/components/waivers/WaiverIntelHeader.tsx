import type { WaiverRecommendationsResponse } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatModelLabel } from "@/lib/utils"

type WaiverIntelHeaderProps = {
  directionLabel: string
  waiver: WaiverRecommendationsResponse
}

const postureByDirection: Record<string, string> = {
  true_contender:
    "Bid aggressively for players who can score for you immediately.",
  fragile_contender:
    "Protect the starting lineup and pay for stability, not roster clutter.",
  hard_rebuild:
    "Keep bids disciplined and prioritize young upside stashes over short-term points.",
  elite_value_accumulation:
    "Stay patient and spend only when the market gives you insulation or upside.",
}

export function WaiverIntelHeader({
  directionLabel,
  waiver,
}: WaiverIntelHeaderProps) {
  const budgetLabel =
    waiver.remaining_faab === null
      ? "—"
      : `$${waiver.remaining_faab.toFixed(0)}`
  const posture =
    postureByDirection[directionLabel] ??
    "Let direction drive aggression: pay for immediate starters, not empty depth."

  return (
    <Card>
      <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="terminal-label text-primary/85">Waiver Wire</p>
          <CardTitle className="mt-2 text-display-card font-extrabold tracking-tight">
            {budgetLabel}
          </CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">Remaining FAAB</p>
        </div>
        <Badge variant="outline">{waiver.waiver_type_label}</Badge>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="font-headline text-xl font-bold">
          {formatModelLabel(directionLabel)}
        </p>
        <p className="text-sm leading-6 text-muted-foreground">{posture}</p>
      </CardContent>
    </Card>
  )
}
