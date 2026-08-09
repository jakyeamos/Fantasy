import type { PackageBuilderResult, TradeAsset } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function renderAssets(assets: TradeAsset[]) {
  return assets
    .map((asset, index) => {
      if (asset.asset_type === "player")
        return asset.player_id ?? `Player ${index + 1}`
      return `${asset.pick_year} Round ${asset.pick_round}`
    })
    .join(", ")
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

  const offers = [packageBuilder.aggressive_open, packageBuilder.fair_close]

  return (
    <div className="space-y-4">
      <div>
        <p className="terminal-label text-primary/80">Suggested framing</p>
        <h3 className="font-headline text-2xl font-bold">Package Builder</h3>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {offers.map((offer) => (
          <Card key={offer.label}>
            <CardHeader>
              <CardTitle>{offer.label}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="rounded-lg border border-border/35 bg-card/45 px-3 py-3 text-sm">
                <span className="terminal-label text-muted-foreground">
                  Send
                </span>{" "}
                {renderAssets(offer.send_assets)}
              </p>
              <p className="rounded-lg border border-border/35 bg-card/45 px-3 py-3 text-sm">
                <span className="terminal-label text-muted-foreground">
                  Receive
                </span>{" "}
                {renderAssets(offer.receive_assets)}
              </p>
              <p className="border-t border-border/60 pt-3 text-sm italic text-muted-foreground">
                {offer.reasoning}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
      {packageBuilder.participant_offers?.length ? (
        <Card>
          <CardHeader>
            <CardTitle>Participant Offers</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {packageBuilder.participant_offers.map((offer) => (
              <div
                key={`${offer.roster_id}-${offer.role}`}
                className="rounded-lg border border-border/35 bg-card/45 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold">{offer.label}</p>
                    <p className="terminal-label text-muted-foreground">
                      {offer.role.replace("_", " ")}
                    </p>
                  </div>
                  {offer.market_fairness ? (
                    <span className="rounded-md border border-border/45 px-2 py-1 text-xs font-medium">
                      {Math.round(offer.market_fairness.score)}
                    </span>
                  ) : null}
                </div>
                <div className="mt-3 space-y-2 text-sm">
                  <p>
                    <span className="terminal-label text-muted-foreground">
                      Sends
                    </span>{" "}
                    {renderAssets(offer.send_assets)}
                  </p>
                  <p>
                    <span className="terminal-label text-muted-foreground">
                      Receives
                    </span>{" "}
                    {renderAssets(offer.receive_assets)}
                  </p>
                </div>
                <p className="mt-3 border-t border-border/50 pt-3 text-sm italic text-muted-foreground">
                  {offer.reasoning}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
