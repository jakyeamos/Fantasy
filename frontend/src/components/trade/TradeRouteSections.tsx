import type {
  PickSearchResult,
  PickValue,
  PlayerSearchResult,
  TradeAsset,
  TradeRosterResult,
} from "@/api/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  AssetBucketPanel,
  RosterField,
} from "@/components/trade/TradeBuilderFields"
import type { AssetBucket, QueryTarget } from "@/lib/tradeAssetSearch"
import type { ThirdPartyTradeDraft } from "@/lib/tradeRouteHelpers"

export function SuggestedOfferStartCard({
  prefilledPlayerAsset,
  prefilledSendAsset,
  prefilledReceiveAsset,
}: {
  prefilledPlayerAsset: TradeAsset | null
  prefilledSendAsset: TradeAsset | null
  prefilledReceiveAsset: TradeAsset | null
}) {
  return (
    <Card className="border-primary/25 bg-primary/5">
      <CardHeader>
        <p className="terminal-label text-primary/85">Suggested Offer Starting Point</p>
        <CardTitle className="text-xl">
          {prefilledPlayerAsset
            ? `Build around ${prefilledPlayerAsset.player_name}`
            : prefilledReceiveAsset
              ? `Build around ${prefilledReceiveAsset.player_name}`
              : "Choose a target, then anchor price before adding assets"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm leading-6 text-muted-foreground">
        {prefilledSendAsset || prefilledReceiveAsset ? (
          <p>
            This command-center offer is queued with a concrete send and receive
            side. Evaluate the score before sending, then adjust the balancing
            asset if the counterparty needs a cleaner close.
          </p>
        ) : prefilledPlayerAsset ? (
          <p>
            The recommendation target is queued as your receive side once the
            roster context resolves. Start with a fair-value liquid asset or a
            tier-down plus a pick, then evaluate before sending.
          </p>
        ) : (
          <p>
            Open a command-center or opportunity CTA for a prefilled target, or
            select a counterparty and add a player you want to receive.
          </p>
        )}
        <div className="grid gap-2 md:grid-cols-3">
          <p>
            <span className="font-semibold text-foreground">Send shape:</span>{" "}
            liquid player, pick, or tier-down package.
          </p>
          <p>
            <span className="font-semibold text-foreground">Receive shape:</span>{" "}
            target player plus optional balancing asset.
          </p>
          <p>
            <span className="font-semibold text-foreground">Pitch angle:</span>{" "}
            solve the other manager&apos;s roster need, not your model score.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

export function CoreDealBoard({
  userRosterName,
  counterpartyRosterName,
  counterpartyRosterId,
  thirdPartyCount,
  queryTarget,
  userSends,
  userReceives,
  leagueId,
  pickValuesByKey,
  onSetActiveTarget,
  onRemoveUserAsset,
}: {
  userRosterName: string | null
  counterpartyRosterName: string | null
  counterpartyRosterId: number
  thirdPartyCount: number
  queryTarget: QueryTarget
  userSends: TradeAsset[]
  userReceives: TradeAsset[]
  leagueId: string
  pickValuesByKey: Map<string, PickValue>
  onSetActiveTarget: (target: QueryTarget) => void
  onRemoveUserAsset: (bucket: AssetBucket, index: number) => void
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
      <Card className="border-primary/25">
        <CardHeader>
          <CardTitle>{userRosterName ? `${userRosterName} • Your Team` : "Your Team View"}</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Build your send and receive package from your roster’s perspective.
          </p>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <AssetBucketPanel
            title="You Send"
            subtitle="Assets leaving your roster."
            buttonLabel="Add to Send Side"
            isActive={queryTarget.kind === "user" && queryTarget.bucket === "send"}
            assets={userSends}
            leagueId={leagueId}
            pickValuesByKey={pickValuesByKey}
            onSelect={() => onSetActiveTarget({ kind: "user", bucket: "send" })}
            onRemove={(index) => onRemoveUserAsset("send", index)}
          />
          <AssetBucketPanel
            title="You Receive"
            subtitle="Assets you gain from the full deal."
            buttonLabel="Add to Receive Side"
            isActive={queryTarget.kind === "user" && queryTarget.bucket === "receive"}
            assets={userReceives}
            leagueId={leagueId}
            pickValuesByKey={pickValuesByKey}
            onSelect={() => onSetActiveTarget({ kind: "user", bucket: "receive" })}
            onRemove={(index) => onRemoveUserAsset("receive", index)}
          />
        </CardContent>
      </Card>

      <Card className="border-dashed border-border/45">
        <CardHeader>
          <CardTitle>
            {counterpartyRosterName
              ? `${counterpartyRosterName} • Primary Counterparty`
              : "Primary Counterparty"}
          </CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            This opponent still drives manager exploit scoring for the core swap.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Manager exploit scoring anchors to{" "}
            {counterpartyRosterName ?? `roster ${counterpartyRosterId || "?"}`}. Reroutes
            and package outputs also include each extra roster with its own scored leg.
          </p>
          <div className="rounded-xl border border-border/45 bg-card/45 p-4">
            <p className="terminal-label text-muted-foreground">Deal Shape</p>
            <p className="mt-2 text-sm font-semibold">
              {thirdPartyCount ? `2 core teams + ${thirdPartyCount} extra` : "2 core teams"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Extra teams get sidecar market scores and participant-specific package
              explanations alongside your core swap.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export function ThirdPartyTradeCards({
  trades,
  queryTarget,
  rosterNameById,
  rosterOptions,
  leagueId,
  pickValuesByKey,
  onSetActiveTarget,
  onUpdateTrade,
  onRemoveTrade,
  onRemoveAsset,
}: {
  trades: ThirdPartyTradeDraft[]
  queryTarget: QueryTarget
  rosterNameById: Map<number, string>
  rosterOptions: TradeRosterResult[]
  leagueId: string
  pickValuesByKey: Map<string, PickValue>
  onSetActiveTarget: (target: QueryTarget) => void
  onUpdateTrade: (
    tradeId: string,
    updater: (trade: ThirdPartyTradeDraft) => ThirdPartyTradeDraft,
  ) => void
  onRemoveTrade: (tradeId: string) => void
  onRemoveAsset: (tradeId: string, bucket: AssetBucket, index: number) => void
}) {
  if (!trades.length) {
    return null
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="terminal-label text-muted-foreground">Multi-Team Legs</p>
          <p className="text-sm text-muted-foreground">
            Track what each extra roster sends into and receives from the deal.
          </p>
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        {trades.map((trade, index) => {
          const isActiveTrade =
            queryTarget.kind === "third-party" && queryTarget.tradeId === trade.clientId

          return (
            <Card
              key={trade.clientId}
              className={
                isActiveTrade
                  ? "border-warning/70"
                  : "border-dashed border-border/45"
              }
            >
              <CardHeader className="flex flex-row items-start justify-between gap-4">
                <div className="space-y-1">
                  <CardTitle>
                    {trade.rosterId > 0
                      ? `${rosterNameById.get(trade.rosterId) ?? `Roster ${trade.rosterId}`} • Third Team ${index + 1}`
                      : `Third Team ${index + 1}`}
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Score this participant&apos;s send and receive leg for package and
                    reroute explanations.
                  </p>
                </div>
                <Button size="sm" variant="ghost" onClick={() => onRemoveTrade(trade.clientId)}>
                  Remove
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                <RosterField
                  label="Third Team Roster"
                  value={trade.rosterId}
                  onChange={(value) =>
                    onUpdateTrade(trade.clientId, (current) => ({
                      ...current,
                      rosterId: value,
                    }))
                  }
                  options={rosterOptions}
                  placeholder="Select the extra team"
                  emptyLabel={
                    leagueId.trim().length > 0 ? "No rosters available" : "Select a league first"
                  }
                />
                <div className="grid gap-4 md:grid-cols-2">
                  <AssetBucketPanel
                    title="Team Sends"
                    subtitle="Assets this roster contributes."
                    buttonLabel="Add Outgoing Assets"
                    isActive={
                      queryTarget.kind === "third-party" &&
                      queryTarget.tradeId === trade.clientId &&
                      queryTarget.bucket === "send"
                    }
                    assets={trade.sends}
                    leagueId={leagueId}
                    pickValuesByKey={pickValuesByKey}
                    onSelect={() =>
                      onSetActiveTarget({
                        kind: "third-party",
                        tradeId: trade.clientId,
                        bucket: "send",
                      })
                    }
                    onRemove={(assetIndex) =>
                      onRemoveAsset(trade.clientId, "send", assetIndex)
                    }
                  />
                  <AssetBucketPanel
                    title="Team Receives"
                    subtitle="Assets this roster ends up with."
                    buttonLabel="Add Incoming Assets"
                    isActive={
                      queryTarget.kind === "third-party" &&
                      queryTarget.tradeId === trade.clientId &&
                      queryTarget.bucket === "receive"
                    }
                    assets={trade.receives}
                    leagueId={leagueId}
                    pickValuesByKey={pickValuesByKey}
                    onSelect={() =>
                      onSetActiveTarget({
                        kind: "third-party",
                        tradeId: trade.clientId,
                        bucket: "receive",
                      })
                    }
                    onRemove={(assetIndex) =>
                      onRemoveAsset(trade.clientId, "receive", assetIndex)
                    }
                  />
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

export function TradeAssetSearchCard({
  title,
  description,
  queryText,
  activeRosterId,
  canSearchAssets,
  hasScopedRoster,
  queryTarget,
  leagueId,
  playerResults,
  playerSearchSuccess,
  pickOptions,
  onQueryTextChange,
  onAddPlayer,
  onAddPick,
}: {
  title: string
  description: string
  queryText: string
  activeRosterId: number | undefined
  canSearchAssets: boolean
  hasScopedRoster: boolean
  queryTarget: QueryTarget
  leagueId: string
  playerResults: PlayerSearchResult[] | undefined
  playerSearchSuccess: boolean
  pickOptions: PickSearchResult[]
  onQueryTextChange: (value: string) => void
  onAddPlayer: (player: PlayerSearchResult) => void
  onAddPick: (pick: PickSearchResult) => void
}) {
  const trimmedQuery = queryText.trim()

  return (
    <Card className="border-dashed bg-card/70">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <input
          value={queryText}
          onChange={(event) => onQueryTextChange(event.target.value)}
          className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
          placeholder={
            activeRosterId
              ? "Leave blank to browse the roster, or type to filter players..."
              : "Search players or picks..."
          }
          disabled={!canSearchAssets}
        />

        {leagueId.trim().length > 0 && !hasScopedRoster ? (
          <p className="rounded-lg border border-destructive/25 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {queryTarget.kind === "user"
              ? "Your team has not been identified for this league yet."
              : "Select the third team roster before searching its outgoing assets."}
          </p>
        ) : null}

        {playerResults?.length ? (
          <div className="space-y-2">
            <p className="terminal-label text-muted-foreground">
              {trimmedQuery.length >= 2 ? "Player Results" : "Roster Players"}
            </p>
            <div className="flex flex-wrap gap-2">
              {playerResults.map((player) => (
                <Button
                  key={`${player.player_id}-${player.roster_id}`}
                  variant="outline"
                  size="sm"
                  onClick={() => onAddPlayer(player)}
                >
                  {player.full_name} ({player.position})
                  {activeRosterId ? "" : ` • ${player.roster_name}`}
                </Button>
              ))}
            </div>
          </div>
        ) : null}

        {trimmedQuery.length >= 2 && playerSearchSuccess && !playerResults?.length ? (
          <p className="text-sm text-muted-foreground">No players matched this target.</p>
        ) : null}

        {activeRosterId && playerSearchSuccess && trimmedQuery.length === 0 && !playerResults?.length ? (
          <p className="text-sm text-muted-foreground">
            No roster players were available for this team.
          </p>
        ) : null}

        {pickOptions.length ? (
          <div className="space-y-2">
            <p className="terminal-label text-muted-foreground">Picks</p>
            <div className="flex flex-wrap gap-2">
              {pickOptions.map((pick) => (
                <Button
                  key={`${pick.current_owner_id}-${pick.pick_year}-${pick.round}`}
                  variant="outline"
                  size="sm"
                  onClick={() => onAddPick(pick)}
                >
                  {pick.current_owner_name}&apos;s {pick.pick_year} R{pick.round}
                </Button>
              ))}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
