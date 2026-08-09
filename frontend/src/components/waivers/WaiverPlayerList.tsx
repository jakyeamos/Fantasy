import type { WaiverRecommendation } from "@/api/types"
import { WaiverPlayerRow } from "@/components/waivers/WaiverPlayerRow"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { surfaceToneClasses, textToneClasses } from "@/lib/ui-tokens"

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
            The engine found no add/drop moves worth forcing. This can mean
            every available player is below the bench threshold, league waiver
            data has not been ingested, or the selected roster has no safe drop
            candidate.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">
          Add / Drop / FAAB
        </p>
        <CardTitle>Waiver Decision Board</CardTitle>
      </CardHeader>
      <CardContent>
        {dataFreshnessWarning ? (
          <div
            className={`mb-4 rounded border px-3 py-2 text-sm ${surfaceToneClasses.attention} ${textToneClasses.attention}`}
          >
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
