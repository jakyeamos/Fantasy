import type { PackageBuilderResult, TradeAsset } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function renderAssets(assets: TradeAsset[]) {
  return assets.map((asset, index) => {
    if (asset.asset_type === "player") return asset.player_id ?? `Player ${index + 1}`
    return `${asset.pick_year} Round ${asset.pick_round}`
  }).join(", ")
}

export function PackageBuilderPanel({
  packageBuilder,
}: {
  packageBuilder: PackageBuilderResult | null | undefined
}) {
  if (!packageBuilder) {
    return (
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">
            Insufficient data to build a package for this trade.
          </p>
        </CardContent>
      </Card>
    )
  }

  const offers = [
    packageBuilder.aggressive_open,
    packageBuilder.fair_close,
  ]

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Package Builder</h3>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {offers.map((offer) => (
          <Card key={offer.label}>
            <CardHeader>
              <CardTitle>{offer.label}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm">
                <span className="text-xs text-muted-foreground">Send:</span>{" "}
                {renderAssets(offer.send_assets)}
              </p>
              <p className="text-sm">
                <span className="text-xs text-muted-foreground">Receive:</span>{" "}
                {renderAssets(offer.receive_assets)}
              </p>
              <p className="border-t border-border/60 pt-3 text-sm italic text-muted-foreground">
                {offer.reasoning}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
