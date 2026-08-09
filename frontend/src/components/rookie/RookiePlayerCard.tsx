import { Separator } from "@/components/ui/separator"

import type { ProspectModelOutput, RookiePlayer } from "@/api/types"
import { MarketGapPanel } from "@/components/recommendations/MarketGapPanel"
import { CompRow } from "@/components/rookie/CompRow"
import { HitRateBadge } from "@/components/rookie/HitRateBadge"
import { OverUndervalueFlag } from "@/components/rookie/OverUndervalueFlag"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { badgeToneClasses } from "@/lib/ui-tokens"
import { cn } from "@/lib/utils"

const RISK_BORDER: Record<RookiePlayer["risk_band"], string> = {
  Low: "border-l-success-border",
  Moderate: "border-l-warning-border",
  High: "border-l-destructive-border",
}

const RISK_BADGE: Record<RookiePlayer["risk_band"], string> = {
  Low: badgeToneClasses.success,
  Moderate: badgeToneClasses.warning,
  High: badgeToneClasses.destructive,
}

export function RookiePlayerCard({
  player,
  isAvailableAtSlot = false,
  selectedSlot,
  modelOutput,
  isModelLoading = false,
}: {
  player: RookiePlayer
  isAvailableAtSlot?: boolean
  selectedSlot?: string
  modelOutput?: ProspectModelOutput | null
  isModelLoading?: boolean
}) {
  return (
    <Card
      className={cn(
        "border-l-4 transition-transform duration-200 hover:-translate-y-1",
        RISK_BORDER[player.risk_band],
        isAvailableAtSlot && "bg-primary/10",
      )}
    >
      <CardContent className="p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="terminal-label text-muted-foreground">Prospect</p>
            <p className="mt-2 text-sm font-semibold">{player.full_name}</p>
          </div>
          <Badge variant="outline">{player.position}</Badge>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {player.archetype_label}
        </p>
        <div className="mt-3 flex items-center gap-2">
          <span className="terminal-label text-muted-foreground">
            {player.risk_band} risk
          </span>
          <span
            className={cn(
              "rounded px-2 py-0.5 text-xs font-medium",
              RISK_BADGE[player.risk_band],
            )}
          >
            {player.risk_band}
          </span>
        </div>
        {isAvailableAtSlot && selectedSlot ? (
          <p className="mt-3 rounded-lg border border-primary/20 bg-primary/10 px-3 py-2 text-xs text-primary">
            Available at ~{selectedSlot}
          </p>
        ) : null}
        {player.draft_action ? (
          <p className="mt-3 rounded-lg border border-border/50 bg-background/40 px-3 py-2 text-xs text-foreground">
            Draft action: {player.draft_action}
          </p>
        ) : null}
        <Separator className="my-3" />
        {isModelLoading ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-5 w-28" />
            </div>
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : modelOutput ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="terminal-label text-muted-foreground">
                  Model signal
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {modelOutput.predicted_bucket} outcome lean
                </p>
              </div>
              <HitRateBadge
                bucket={modelOutput.hit_rate_bucket}
                lowConfidence={modelOutput.low_confidence}
              />
            </div>
            <OverUndervalueFlag
              direction={modelOutput.overvalue_flag_direction}
              magnitude={modelOutput.overvalue_magnitude}
              lowConfidence={modelOutput.low_confidence}
              subFlags={modelOutput.sub_flags}
            />
            <div className="space-y-2">
              <p className="terminal-label text-muted-foreground">
                Historical comps
              </p>
              {modelOutput.comps.length ? (
                modelOutput.comps.map((comp) => (
                  <CompRow
                    key={`${player.player_id}-${comp.role}`}
                    comp={comp}
                  />
                ))
              ) : (
                <p className="text-xs text-muted-foreground">
                  No historical comps surfaced for this profile yet.
                </p>
              )}
            </div>
            {player.model_vs_market_gap ? (
              <MarketGapPanel gap={player.model_vs_market_gap} />
            ) : null}
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Phase 8 model output unavailable for this prospect.
            </p>
            {player.model_vs_market_gap ? (
              <MarketGapPanel gap={player.model_vs_market_gap} />
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
