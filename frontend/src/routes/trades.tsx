import { useMemo, useState } from "react"

import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import type {
  PickSearchResult,
  PlayerSearchResult,
  TradeAsset,
  TradeEvaluation,
} from "@/api/types"
import { AssetChip } from "@/components/trade/AssetChip"
import { EvaluationOutputPanel } from "@/components/trade/EvaluationOutputPanel"
import { PackageBuilderPanel } from "@/components/trade/PackageBuilderPanel"
import { RerouteSheet } from "@/components/trade/RerouteSheet"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

async function fetchJson<T>(path: string) {
  const response = await fetch(`/api${path}`)
  if (!response.ok) throw new Error(`Request failed: ${path}`)
  return (await response.json()) as T
}

export const Route = createFileRoute("/trades")({
  validateSearch: (search: Record<string, unknown>) => ({
    leagueId: typeof search.leagueId === "string" ? search.leagueId : undefined,
  }),
  component: TradesPlaceholderPage,
})

function TradesPlaceholderPage() {
  const search = Route.useSearch()
  const [leagueId, setLeagueId] = useState(search.leagueId ?? "")
  const [userRosterId, setUserRosterId] = useState(1)
  const [counterpartyRosterId, setCounterpartyRosterId] = useState(2)
  const [queryText, setQueryText] = useState("")
  const [queryTarget, setQueryTarget] = useState<"user-send" | "user-receive">(
    "user-send",
  )
  const [userSends, setUserSends] = useState<TradeAsset[]>([])
  const [userReceives, setUserReceives] = useState<TradeAsset[]>([])
  const [showReroutes, setShowReroutes] = useState(false)
  const [showPackage, setShowPackage] = useState(false)

  const activeRosterId =
    queryTarget === "user-send" ? userRosterId : counterpartyRosterId
  const playerSearchQuery = useQuery({
    queryKey: ["trade", "players", leagueId, queryText, activeRosterId],
    queryFn: () =>
      fetchJson<PlayerSearchResult[]>(
        `/trade/players/search?league_id=${leagueId}&q=${encodeURIComponent(queryText)}&roster_id=${activeRosterId}`,
      ),
    enabled: leagueId.length > 0 && queryText.trim().length >= 2,
  })
  const pickSearchQuery = useQuery({
    queryKey: ["trade", "picks", leagueId, activeRosterId],
    queryFn: () =>
      fetchJson<PickSearchResult[]>(
        `/trade/picks/search?league_id=${leagueId}&roster_id=${activeRosterId}`,
      ),
    enabled: leagueId.length > 0,
  })

  const evaluationMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/trade/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          league_id: leagueId,
          user_roster_id: userRosterId,
          counterparty_roster_id: counterpartyRosterId,
          user_sends: userSends,
          user_receives: userReceives,
          third_party_trades: [],
          include_reroutes: true,
          include_package: true,
        }),
      })
      if (!response.ok) throw new Error("Trade evaluation failed")
      return (await response.json()) as TradeEvaluation
    },
  })

  const evaluation = evaluationMutation.data

  const pickOptions = useMemo(
    () => pickSearchQuery.data?.slice(0, 4) ?? [],
    [pickSearchQuery.data],
  )

  const addAsset = (asset: TradeAsset) => {
    if (queryTarget === "user-send") {
      setUserSends((current) => [...current, asset])
      return
    }
    setUserReceives((current) => [...current, asset])
  }

  const removeAsset = (list: "send" | "receive", index: number) => {
    if (list === "send") {
      setUserSends((current) => current.filter((_, assetIndex) => assetIndex !== index))
      return
    }
    setUserReceives((current) => current.filter((_, assetIndex) => assetIndex !== index))
  }

  const canEvaluate =
    leagueId.trim().length > 0 && userSends.length > 0 && userReceives.length > 0

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Evaluate Trade</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <label className="space-y-2">
              <span className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                League ID
              </span>
              <input
                value={leagueId}
                onChange={(event) => setLeagueId(event.target.value)}
                className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
                placeholder="league_x"
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                Your Roster ID
              </span>
              <input
                type="number"
                value={userRosterId}
                onChange={(event) => setUserRosterId(Number(event.target.value))}
                className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                Counterparty Roster ID
              </span>
              <input
                type="number"
                value={counterpartyRosterId}
                onChange={(event) => setCounterpartyRosterId(Number(event.target.value))}
                className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
              />
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="border-l-2 border-l-primary">
              <CardHeader>
                <CardTitle>Your Team</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                    You send
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {userSends.map((asset, index) => (
                      <AssetChip
                        key={`${asset.asset_type}-${asset.player_id ?? asset.pick_round}-${index}`}
                        asset={asset}
                        detail={asset.asset_type === "pick" ? asset.projected_slot ?? undefined : undefined}
                        onRemove={() => removeAsset("send", index)}
                      />
                    ))}
                  </div>
                </div>
                <Button variant="outline" onClick={() => setQueryTarget("user-send")}>
                  Add to Send Side
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Counterparty</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                    You receive
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {userReceives.map((asset, index) => (
                      <AssetChip
                        key={`${asset.asset_type}-${asset.player_id ?? asset.pick_round}-${index}`}
                        asset={asset}
                        detail={asset.asset_type === "pick" ? asset.projected_slot ?? undefined : undefined}
                        onRemove={() => removeAsset("receive", index)}
                      />
                    ))}
                  </div>
                </div>
                <Button variant="outline" onClick={() => setQueryTarget("user-receive")}>
                  Add to Receive Side
                </Button>
              </CardContent>
            </Card>
          </div>

          <Card className="border-dashed">
            <CardHeader>
              <CardTitle>
                {queryTarget === "user-send" ? "Add to Your Send Side" : "Add to Your Receive Side"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <input
                value={queryText}
                onChange={(event) => setQueryText(event.target.value)}
                className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
                placeholder="Search players or picks..."
              />
              {playerSearchQuery.data?.length ? (
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                    Player results
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {playerSearchQuery.data.map((player) => (
                      <Button
                        key={`${player.player_id}-${player.roster_id}`}
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          addAsset({ asset_type: "player", player_id: player.player_id })
                        }
                      >
                        {player.full_name} ({player.position})
                      </Button>
                    ))}
                  </div>
                </div>
              ) : null}
              {pickOptions.length ? (
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                    Picks
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {pickOptions.map((pick) => (
                      <Button
                        key={`${pick.current_owner_id}-${pick.pick_year}-${pick.round}`}
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          addAsset({
                            asset_type: "pick",
                            pick_owner_roster_id: pick.current_owner_id,
                            pick_year: pick.pick_year,
                            pick_round: pick.round,
                            projected_slot: pick.projected_slot,
                          })
                        }
                      >
                        {pick.current_owner_name}'s {pick.pick_year} R{pick.round}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Button
            className="w-full sm:w-auto"
            disabled={!canEvaluate || evaluationMutation.isPending}
            onClick={() => {
              setShowPackage(false)
              setShowReroutes(false)
              evaluationMutation.mutate()
            }}
          >
            {evaluationMutation.isPending ? "Evaluating..." : "Evaluate"}
          </Button>

          {evaluationMutation.isError ? (
            <p className="text-sm text-red-600">
              Trade evaluation failed. Check the league and roster IDs, then try again.
            </p>
          ) : null}
        </CardContent>
      </Card>

      {evaluation ? (
        <>
          <EvaluationOutputPanel
            evaluation={evaluation}
            onOpenReroutes={() => setShowReroutes(true)}
            onOpenPackage={() => setShowPackage(true)}
          />
          {showPackage ? <PackageBuilderPanel packageBuilder={evaluation.package} /> : null}
          <RerouteSheet
            open={showReroutes}
            reroutes={evaluation.reroutes}
            onClose={() => setShowReroutes(false)}
          />
        </>
      ) : null}
    </div>
  )
}
