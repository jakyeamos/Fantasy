import type { PickValue, TradeAsset } from "@/api/types"
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
  pickValue,
  onRemove,
}: {
  asset: TradeAsset
  detail?: string
  pickValue?: PickValue
  onRemove: () => void
}) {
  if (asset.asset_type === "pick" && pickValue) {
    return (
      <div className="flex flex-col gap-1 rounded-lg bg-secondary px-3 py-2 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span>{label(asset)}</span>
          {detail ? <Badge variant="outline">{detail}</Badge> : null}
          {pickValue.years_out > 0 ? (
            <span className="text-muted-foreground">(future year)</span>
          ) : null}
          <TimingBadge
            label={pickValue.timing_label}
            reasoning={pickValue.timing_reasoning}
            showReasoning={false}
          />
          <Button size="sm" variant="ghost" className="h-7 px-2" onClick={onRemove}>
            ×
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">{pickValue.timing_reasoning}</p>
      </div>
    )
  }

  return (
    <div className="inline-flex items-center gap-2 rounded-lg bg-secondary px-2 py-1 text-xs">
      <span>{label(asset)}</span>
      {detail ? <Badge variant="outline">{detail}</Badge> : null}
      <Button size="sm" variant="ghost" className="h-7 px-2" onClick={onRemove}>
        ×
      </Button>
    </div>
  )
}
