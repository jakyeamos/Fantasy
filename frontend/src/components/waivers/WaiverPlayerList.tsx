import type { WaiverRecommendation } from "@/api/types"
import { WaiverPlayerRow } from "@/components/waivers/WaiverPlayerRow"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type WaiverPlayerListProps = {
  recommendations: WaiverRecommendation[]
  dataFreshnessWarning: boolean
}

export function WaiverPlayerList({
  recommendations,
  dataFreshnessWarning,
}: WaiverPlayerListProps) {
  if (!recommendations.length) {
    return (
      <Card className="border-dashed border-border/45">
        <CardHeader>
          <p className="terminal-label text-muted-foreground">Add Candidates</p>
          <CardTitle>No Waiver Targets</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">
            The engine found no players worth adding at this time. Check back after the next
            ingest or when a new player becomes available.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">Add Candidates</p>
        <CardTitle>Waiver Board</CardTitle>
      </CardHeader>
      <CardContent>
        {dataFreshnessWarning ? (
          <div className="mb-4 rounded border border-orange-400/30 bg-orange-400/10 px-3 py-2 text-sm text-orange-400">
            Waiver data may be stale. Re-run ingest for accurate FAAB budgets.
          </div>
        ) : null}
        <div className="divide-y divide-border/40">
          {recommendations.map((recommendation) => (
            <WaiverPlayerRow
              key={recommendation.player_id}
              recommendation={recommendation}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
