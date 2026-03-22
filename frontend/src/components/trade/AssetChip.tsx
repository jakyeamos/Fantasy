import type { TradeAsset } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

function label(asset: TradeAsset) {
  if (asset.asset_type === "player") return asset.player_id ?? "Unknown"
  return `${asset.pick_year} Round ${asset.pick_round}`
}

export function AssetChip({
  asset,
  detail,
  onRemove,
}: {
  asset: TradeAsset
  detail?: string
  onRemove: () => void
}) {
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
