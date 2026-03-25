import type { PickValue, TradeAsset } from "@/api/types"
import { RuleCitation } from "@/components/picks/RuleCitation"
import { TimingBadge } from "@/components/picks/TimingBadge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

function label(asset: TradeAsset) {
  if (asset.asset_type === "player") {
    return asset.player_name ?? asset.player_id ?? "Unknown"
  }
  if (asset.pick_owner_name) {
    return `${asset.pick_owner_name} ${asset.pick_year} R${asset.pick_round}`
  }
  return `${asset.pick_year} Round ${asset.pick_round}`
}

export function AssetChip({
  asset,
  detail,
  leagueId,
  pickValue,
  onRemove,
}: {
  asset: TradeAsset
  detail?: string
  leagueId: string
  pickValue?: PickValue
  onRemove: () => void
}) {
  if (asset.asset_type === "pick" && pickValue) {
    const isBlocked = pickValue.rule_citation === null
    return (
      <div className="flex flex-col gap-1 rounded-lg border border-border/35 bg-card/45 px-3 py-2 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span>{label(asset)}</span>
          {!isBlocked && detail ? <Badge variant="outline">{detail}</Badge> : null}
          {!isBlocked && pickValue.years_out > 0 ? (
            <span className="text-muted-foreground">(future year)</span>
          ) : null}
          {!isBlocked ? (
            <TimingBadge
              label={pickValue.timing_label}
              reasoning={pickValue.timing_reasoning}
              showReasoning={false}
            />
          ) : null}
          <Button size="sm" variant="ghost" className="h-7 px-2" onClick={onRemove}>
            ×
          </Button>
        </div>
        {!isBlocked ? <p className="text-xs text-muted-foreground">{pickValue.timing_reasoning}</p> : null}
        <RuleCitation citation={pickValue.rule_citation} leagueId={leagueId} />
      </div>
    )
  }

  return (
    <div className="inline-flex items-center gap-2 rounded-lg border border-border/35 bg-card/45 px-2 py-1 text-xs">
      <span>{label(asset)}</span>
      {detail ? <Badge variant="outline">{detail}</Badge> : null}
      <Button size="sm" variant="ghost" className="h-7 px-2" onClick={onRemove}>
        ×
      </Button>
    </div>
  )
}
