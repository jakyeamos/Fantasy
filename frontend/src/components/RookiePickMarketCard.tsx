import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

interface RookiePickMarketCardProps {
  positionalTendency: Record<string, number>
  dominantArchetype: string | null
  pickPremiumScore: number | null
  isLoading?: boolean
}

function topTendency(positionalTendency: Record<string, number>) {
  const entries = Object.entries(positionalTendency)
  if (!entries.length) {
    return null
  }
  return entries.reduce((best, current) =>
    current[1] > best[1] ? current : best,
  )
}

export function RookiePickMarketCard({
  positionalTendency,
  dominantArchetype,
  pickPremiumScore,
  isLoading = false,
}: RookiePickMarketCardProps) {
  const tendency = topTendency(positionalTendency)
  const tendencyLabel =
    tendency && tendency[1] > 0.05 ? `${tendency[0]}-heavy` : "Balanced"

  return (
    <Card>
      <CardContent className="pt-4 space-y-3">
        <p className="terminal-label">Rookie & Pick Market</p>
        {isLoading ? <Skeleton className="h-24 w-full" /> : null}
        {!isLoading ? (
          <>
            <div className="rounded-lg border border-border/35 bg-card/45 px-3 py-2">
              <p className="terminal-label mb-1">Positional Tendency</p>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium">{tendencyLabel}</span>
                {tendency ? (
                  <span className="text-xs text-muted-foreground">
                    {(tendency[1] * 100).toFixed(0)} pts vs league average
                  </span>
                ) : null}
              </div>
            </div>
            <div className="rounded-lg border border-border/35 bg-card/45 px-3 py-2">
              <p className="terminal-label mb-1">Dominant Archetype</p>
              <span className="text-sm">
                {dominantArchetype ?? "No pattern established"}
              </span>
            </div>
            {pickPremiumScore !== null && pickPremiumScore >= 0.1 ? (
              <div className="rounded-lg border border-border/35 bg-card/45 px-3 py-2">
                <p className="terminal-label mb-2">Pick Premium</p>
                <div className="flex items-center justify-between gap-3">
                  <Badge variant="secondary">Pick Premium</Badge>
                  <span className="text-xs text-muted-foreground">
                    Score {pickPremiumScore.toFixed(2)}
                  </span>
                </div>
              </div>
            ) : null}
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}
