import { useEffect, useMemo, useState } from "react"

import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import type {
  DashboardLeagueSummary,
  PickValue,
  PickSearchResult,
  PlayerSearchResult,
  ThirdPartyTrade,
  TradeAsset,
  TradeEvaluation,
  TradeRosterResult,
} from "@/api/types"
import { dashboardSummaryOptions, pickValuesOptions } from "@/api/queries"
import { AssetChip } from "@/components/trade/AssetChip"
import { EvaluationOutputPanel } from "@/components/trade/EvaluationOutputPanel"
import { PackageBuilderPanel } from "@/components/trade/PackageBuilderPanel"
import { RerouteSheet } from "@/components/trade/RerouteSheet"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type AssetBucket = "send" | "receive"

type QueryTarget =
  | { kind: "user"; bucket: AssetBucket }
  | { kind: "third-party"; tradeId: string; bucket: AssetBucket }

interface ThirdPartyTradeDraft {
  clientId: string
  rosterId: number
  sends: TradeAsset[]
  receives: TradeAsset[]
}

async function fetchJson<T>(path: string) {
  const response = await fetch(`/api${path}`)
  if (!response.ok) throw new Error(`Request failed: ${path}`)
  return (await response.json()) as T
}

function createThirdPartyTradeDraft(): ThirdPartyTradeDraft {
  return {
    clientId: Math.random().toString(36).slice(2, 10),
    rosterId: 0,
    sends: [],
    receives: [],
  }
}

function assetKey(asset: TradeAsset) {
  if (asset.asset_type === "player") {
    return `player:${asset.player_id ?? "unknown"}`
  }
  return `pick:${asset.pick_owner_roster_id ?? "unknown"}:${asset.pick_year ?? "unknown"}:${asset.pick_round ?? "unknown"}`
}

function appendUniqueAsset(assets: TradeAsset[], asset: TradeAsset) {
  if (assets.some((current) => assetKey(current) === assetKey(asset))) {
    return assets
  }
  return [...assets, asset]
}

function toPlayerAsset(player: PlayerSearchResult): TradeAsset {
  return {
    asset_type: "player",
    player_id: player.player_id,
    player_name: player.full_name,
    player_position: player.position,
  }
}

function toPickAsset(pick: PickSearchResult): TradeAsset {
  return {
    asset_type: "pick",
    pick_owner_roster_id: pick.original_owner_id,
    pick_owner_name: pick.original_owner_name,
    pick_year: pick.pick_year,
    pick_round: pick.round,
    projected_slot: pick.projected_slot,
  }
}

function pickValueKeyFromAsset(asset: TradeAsset) {
  return `${asset.pick_owner_roster_id ?? 0}:${asset.pick_year ?? 0}:${asset.pick_round ?? 0}`
}

function pickValueKeyFromValue(pickValue: PickValue) {
  return `${pickValue.pick.pick_owner_roster_id}:${pickValue.pick.pick_year}:${pickValue.pick.pick_round}`
}

function toRequestAsset(asset: TradeAsset): TradeAsset {
  return {
    asset_type: asset.asset_type,
    player_id: asset.player_id ?? null,
    pick_owner_roster_id: asset.pick_owner_roster_id ?? null,
    pick_year: asset.pick_year ?? null,
    pick_round: asset.pick_round ?? null,
    projected_slot: asset.projected_slot ?? null,
  }
}

function toThirdPartyTrade(trade: ThirdPartyTradeDraft): ThirdPartyTrade {
  return {
    roster_id: trade.rosterId,
    sends: trade.sends.map(toRequestAsset),
    receives: trade.receives.map(toRequestAsset),
  }
}

function assetDetail(asset: TradeAsset) {
  if (asset.asset_type === "player") {
    return asset.player_position ?? undefined
  }
  return asset.projected_slot ?? undefined
}

function AssetBucketPanel({
  title,
  subtitle,
  buttonLabel,
  isActive,
  assets,
  pickValuesByKey,
  onSelect,
  onRemove,
}: {
  title: string
  subtitle: string
  buttonLabel: string
  isActive: boolean
  assets: TradeAsset[]
  pickValuesByKey: Map<string, PickValue>
  onSelect: () => void
  onRemove: (index: number) => void
}) {
  return (
    <div className="rounded-xl border border-border/70 bg-background/70 p-4">
      <div className="space-y-1">
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
      <div className="mt-4 min-h-11">
        {assets.length ? (
          <div className="flex flex-wrap gap-2">
            {assets.map((asset, index) => (
              <AssetChip
                key={`${assetKey(asset)}-${index}`}
                asset={asset}
                detail={assetDetail(asset)}
                pickValue={
                  asset.asset_type === "pick"
                    ? pickValuesByKey.get(pickValueKeyFromAsset(asset))
                    : undefined
                }
                onRemove={() => onRemove(index)}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No assets added yet.</p>
        )}
      </div>
      <Button
        className="mt-4"
        variant={isActive ? "default" : "outline"}
        onClick={onSelect}
      >
        {buttonLabel}
      </Button>
    </div>
  )
}

function LeagueField({
  value,
  onChange,
  options,
}: {
  value: string
  onChange: (value: string) => void
  options: DashboardLeagueSummary[]
}) {
  const hasOptions = options.length > 0

  return (
    <label className="space-y-2">
      <span className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
        League
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={!hasOptions}
        className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm disabled:cursor-not-allowed disabled:opacity-60"
      >
        <option value="">
          {hasOptions ? "Select a league" : "No leagues available"}
        </option>
        {options.map((option) => (
          <option key={option.league_id} value={option.league_id}>
            {option.league_name} ({option.league_id})
          </option>
        ))}
      </select>
    </label>
  )
}

function RosterField({
  label,
  value,
  onChange,
  options,
  placeholder,
  emptyLabel,
}: {
  label: string
  value: number
  onChange: (value: number) => void
  options: TradeRosterResult[]
  placeholder: string
  emptyLabel: string
}) {
  const hasOptions = options.length > 0

  return (
    <label className="space-y-2">
      <span className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </span>
      <select
        value={value || ""}
        onChange={(event) => onChange(Number(event.target.value) || 0)}
        disabled={!hasOptions}
        className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm disabled:cursor-not-allowed disabled:opacity-60"
      >
        <option value="">{hasOptions ? placeholder : emptyLabel}</option>
        {options.map((option) => (
          <option key={option.roster_id} value={option.roster_id}>
            {option.roster_name} (Roster {option.roster_id})
          </option>
        ))}
      </select>
    </label>
  )
}

export const Route = createFileRoute("/trades")({
  validateSearch: (search: Record<string, unknown>) => ({
    leagueId: typeof search.leagueId === "string" ? search.leagueId : undefined,
  }),
  component: TradeEvaluatorPage,
})

function TradeEvaluatorPage() {
  const search = Route.useSearch()
  const [leagueId, setLeagueId] = useState(search.leagueId ?? "")
  const [counterpartyRosterId, setCounterpartyRosterId] = useState(0)
  const [thirdPartyTrades, setThirdPartyTrades] = useState<ThirdPartyTradeDraft[]>([])
  const [queryText, setQueryText] = useState("")
  const [queryTarget, setQueryTarget] = useState<QueryTarget>({
    kind: "user",
    bucket: "send",
  })
  const [showReroutes, setShowReroutes] = useState(false)
  const [showPackage, setShowPackage] = useState(false)
  const [userSends, setUserSends] = useState<TradeAsset[]>([])
  const [userReceives, setUserReceives] = useState<TradeAsset[]>([])
  const leaguesQuery = useQuery(dashboardSummaryOptions)
  const leagueOptions = leaguesQuery.data ?? []
  const selectedLeague = useMemo(
    () => leagueOptions.find((option) => option.league_id === leagueId) ?? null,
    [leagueId, leagueOptions],
  )
  const userRosterId = selectedLeague?.user_roster_id ?? 0
  const rostersQuery = useQuery({
    queryKey: ["trade", "rosters", leagueId],
    queryFn: () => {
      const params = new URLSearchParams({ league_id: leagueId })
      return fetchJson<TradeRosterResult[]>(`/trade/rosters?${params.toString()}`)
    },
    enabled: leagueId.trim().length > 0,
  })
  const rosterOptions = rostersQuery.data ?? []
  const rosterNameById = useMemo(
    () => new Map(rosterOptions.map((option) => [option.roster_id, option.roster_name])),
    [rosterOptions],
  )
  const counterpartyOptions = useMemo(
    () => rosterOptions.filter((option) => option.roster_id !== userRosterId),
    [rosterOptions, userRosterId],
  )

  useEffect(() => {
    if (!counterpartyOptions.length) {
      if (counterpartyRosterId !== 0) {
        setCounterpartyRosterId(0)
      }
      return
    }

    if (!counterpartyOptions.some((option) => option.roster_id === counterpartyRosterId)) {
      setCounterpartyRosterId(counterpartyOptions[0]?.roster_id ?? 0)
    }
  }, [counterpartyOptions, counterpartyRosterId])

  const activeThirdParty =
    queryTarget.kind === "third-party"
      ? thirdPartyTrades.find((trade) => trade.clientId === queryTarget.tradeId) ?? null
      : null

  const activeThirdPartyIndex =
    queryTarget.kind === "third-party"
      ? thirdPartyTrades.findIndex((trade) => trade.clientId === queryTarget.tradeId)
      : -1

  const activeRosterId =
    queryTarget.bucket === "send"
      ? queryTarget.kind === "user"
        ? userRosterId
        : activeThirdParty?.rosterId
      : queryTarget.kind === "user"
        ? counterpartyRosterId || undefined
        : undefined

  const searchNeedsRoster = queryTarget.bucket === "send"
  const hasScopedRoster = !searchNeedsRoster || Boolean(activeRosterId && activeRosterId > 0)
  const canSearchAssets = leagueId.trim().length > 0 && hasScopedRoster
  const activeRosterName =
    activeRosterId && activeRosterId > 0 ? rosterNameById.get(activeRosterId) : undefined
  const userRosterName =
    userRosterId > 0 ? rosterNameById.get(userRosterId) ?? `Roster ${userRosterId}` : null
  const counterpartyRosterName =
    counterpartyRosterId > 0
      ? rosterNameById.get(counterpartyRosterId) ?? `Roster ${counterpartyRosterId}`
      : null

  const searchTitle =
    queryTarget.kind === "user"
      ? queryTarget.bucket === "send"
        ? "Add to Your Send Side"
        : "Add to Your Receive Side"
      : queryTarget.bucket === "send"
        ? `Add to Third Team ${activeThirdPartyIndex + 1} Send Side`
        : `Add to Third Team ${activeThirdPartyIndex + 1} Receive Side`

  const searchDescription =
    !hasScopedRoster
      ? leagueId.trim().length === 0
        ? "Select a league to start building the trade."
        : queryTarget.kind === "user"
          ? "Your team could not be identified for this league."
          : "Select a roster for this extra team before searching its outgoing assets."
      : activeRosterId
        ? `Showing ${activeRosterName ?? `roster ${activeRosterId}`} assets. Leave the search blank to browse the full roster.`
        : "Search runs league-wide so you can model incoming legs from any team."

  const playerSearchQuery = useQuery({
    queryKey: [
      "trade",
      "players",
      leagueId,
      queryText,
      activeRosterId ?? "all",
      queryTarget.kind,
      queryTarget.bucket,
      activeThirdParty?.clientId ?? null,
    ],
    queryFn: () => {
      const params = new URLSearchParams({
        league_id: leagueId,
        q: queryText.trim(),
      })
      if (activeRosterId) {
        params.set("roster_id", String(activeRosterId))
      }
      return fetchJson<PlayerSearchResult[]>(`/trade/players/search?${params.toString()}`)
    },
    enabled: canSearchAssets && (Boolean(activeRosterId) || queryText.trim().length >= 2),
  })

  const pickSearchQuery = useQuery({
    queryKey: [
      "trade",
      "picks",
      leagueId,
      activeRosterId ?? "all",
      queryTarget.kind,
      queryTarget.bucket,
      activeThirdParty?.clientId ?? null,
    ],
    queryFn: () => {
      const params = new URLSearchParams({ league_id: leagueId })
      if (activeRosterId) {
        params.set("roster_id", String(activeRosterId))
      }
      return fetchJson<PickSearchResult[]>(`/trade/picks/search?${params.toString()}`)
    },
    enabled: canSearchAssets,
  })
  const pickValuesQuery = useQuery(
    pickValuesOptions(leagueId, {
      targetManagerId: counterpartyRosterId > 0 ? counterpartyRosterId : undefined,
    }),
  )
  const pickValuesByKey = useMemo(
    () =>
      new Map(
        (pickValuesQuery.data ?? []).map((pickValue) => [
          pickValueKeyFromValue(pickValue),
          pickValue,
        ]),
      ),
    [pickValuesQuery.data],
  )

  const currentRequest = useMemo(
    () => ({
      league_id: leagueId.trim(),
      user_roster_id: userRosterId,
      counterparty_roster_id: counterpartyRosterId > 0 ? counterpartyRosterId : null,
      user_sends: userSends.map(toRequestAsset),
      user_receives: userReceives.map(toRequestAsset),
      third_party_trades: thirdPartyTrades
        .filter(
          (trade) =>
            trade.rosterId > 0 &&
            (trade.sends.length > 0 || trade.receives.length > 0),
        )
        .map(toThirdPartyTrade),
      include_reroutes: true,
      include_package: true,
    }),
    [
      counterpartyRosterId,
      leagueId,
      thirdPartyTrades,
      userReceives,
      userRosterId,
      userSends,
    ],
  )

  const evaluationMutation = useMutation({
    mutationFn: async (request: typeof currentRequest) => {
      const response = await fetch("/api/trade/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      })
      if (!response.ok) throw new Error("Trade evaluation failed")
      return (await response.json()) as TradeEvaluation
    },
  })

  const handleLeagueChange = (nextLeagueId: string) => {
    setLeagueId(nextLeagueId)
    setCounterpartyRosterId(0)
    setThirdPartyTrades([])
    setQueryText("")
    setQueryTarget({ kind: "user", bucket: "send" })
    setShowReroutes(false)
    setShowPackage(false)
    setUserSends([])
    setUserReceives([])
    evaluationMutation.reset()
  }

  const evaluation = evaluationMutation.data
  const pickOptions = useMemo(
    () =>
      activeRosterId
        ? pickSearchQuery.data ?? []
        : pickSearchQuery.data?.slice(0, 24) ?? [],
    [activeRosterId, pickSearchQuery.data],
  )

  const setActiveTarget = (target: QueryTarget) => {
    setQueryTarget(target)
    setQueryText("")
  }

  const addThirdPartyTrade = () => {
    const nextTrade = createThirdPartyTradeDraft()
    setThirdPartyTrades((current) => [...current, nextTrade])
    setActiveTarget({ kind: "third-party", tradeId: nextTrade.clientId, bucket: "send" })
  }

  const updateThirdPartyTrade = (
    tradeId: string,
    updater: (trade: ThirdPartyTradeDraft) => ThirdPartyTradeDraft,
  ) => {
    setThirdPartyTrades((current) =>
      current.map((trade) => (trade.clientId === tradeId ? updater(trade) : trade)),
    )
  }

  const removeThirdPartyTrade = (tradeId: string) => {
    setThirdPartyTrades((current) => current.filter((trade) => trade.clientId !== tradeId))
    if (queryTarget.kind === "third-party" && queryTarget.tradeId === tradeId) {
      setActiveTarget({ kind: "user", bucket: "send" })
    }
  }

  const addAsset = (asset: TradeAsset) => {
    if (queryTarget.kind === "user") {
      if (queryTarget.bucket === "send") {
        setUserSends((current) => appendUniqueAsset(current, asset))
        return
      }
      setUserReceives((current) => appendUniqueAsset(current, asset))
      return
    }

    updateThirdPartyTrade(queryTarget.tradeId, (trade) => ({
      ...trade,
      sends:
        queryTarget.bucket === "send"
          ? appendUniqueAsset(trade.sends, asset)
          : trade.sends,
      receives:
        queryTarget.bucket === "receive"
          ? appendUniqueAsset(trade.receives, asset)
          : trade.receives,
    }))
  }

  const removeUserAsset = (bucket: AssetBucket, index: number) => {
    if (bucket === "send") {
      setUserSends((current) => current.filter((_, assetIndex) => assetIndex !== index))
      return
    }
    setUserReceives((current) => current.filter((_, assetIndex) => assetIndex !== index))
  }

  const removeThirdPartyAsset = (
    tradeId: string,
    bucket: AssetBucket,
    index: number,
  ) => {
    updateThirdPartyTrade(tradeId, (trade) => ({
      ...trade,
      sends:
        bucket === "send"
          ? trade.sends.filter((_, assetIndex) => assetIndex !== index)
          : trade.sends,
      receives:
        bucket === "receive"
          ? trade.receives.filter((_, assetIndex) => assetIndex !== index)
          : trade.receives,
    }))
  }

  const canEvaluate =
    leagueId.trim().length > 0 &&
    userRosterId > 0 &&
    counterpartyRosterId > 0 &&
    userSends.length > 0 &&
    userReceives.length > 0 &&
    thirdPartyTrades.every(
      (trade) =>
        trade.rosterId > 0 ||
        (trade.sends.length === 0 && trade.receives.length === 0),
    )

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="space-y-2">
          <CardTitle>Evaluate Trade</CardTitle>
          <p className="max-w-3xl text-sm text-muted-foreground">
            Build your outgoing and incoming package first, then layer in extra teams for
            multi-team trades. The seven dimensions stay anchored to your net swap and the
            primary counterparty profile.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 xl:grid-cols-[repeat(2,minmax(0,1fr))_auto]">
            <LeagueField value={leagueId} onChange={handleLeagueChange} options={leagueOptions} />
            <RosterField
              label="Primary Counterparty"
              value={counterpartyRosterId}
              onChange={setCounterpartyRosterId}
              options={counterpartyOptions}
              placeholder="Select the other team"
              emptyLabel={
                leagueId.trim().length > 0 ? "No other rosters available" : "Select a league first"
              }
            />
            <div className="flex items-end">
              <Button className="w-full xl:w-auto" variant="outline" onClick={addThirdPartyTrade}>
                Add Third Team
              </Button>
            </div>
          </div>

          {leagueId.trim().length > 0 && selectedLeague && userRosterId === 0 ? (
            <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-900 dark:border-amber-700/40 dark:bg-amber-950/30 dark:text-amber-200">
              Your team could not be identified for this league, so trade evaluation is disabled.
            </p>
          ) : null}

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
            <Card className="border-l-2 border-l-primary">
              <CardHeader>
                <CardTitle>{userRosterName ? `${userRosterName} • Your Team` : "Your Team View"}</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <AssetBucketPanel
                  title="You Send"
                  subtitle="Assets leaving your roster."
                  buttonLabel="Add to Send Side"
                  isActive={queryTarget.kind === "user" && queryTarget.bucket === "send"}
                  assets={userSends}
                  pickValuesByKey={pickValuesByKey}
                  onSelect={() => setActiveTarget({ kind: "user", bucket: "send" })}
                  onRemove={(index) => removeUserAsset("send", index)}
                />
                <AssetBucketPanel
                  title="You Receive"
                  subtitle="Assets you gain from the full deal."
                  buttonLabel="Add to Receive Side"
                  isActive={queryTarget.kind === "user" && queryTarget.bucket === "receive"}
                  assets={userReceives}
                  pickValuesByKey={pickValuesByKey}
                  onSelect={() => setActiveTarget({ kind: "user", bucket: "receive" })}
                  onRemove={(index) => removeUserAsset("receive", index)}
                />
              </CardContent>
            </Card>

            <Card className="border-dashed">
              <CardHeader>
                <CardTitle>
                  {counterpartyRosterName
                    ? `${counterpartyRosterName} • Primary Counterparty`
                    : "Primary Counterparty"}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Manager exploit scoring, reroutes, and package framing still anchor to{" "}
                  {counterpartyRosterName ?? `roster ${counterpartyRosterId || "?"}`}. Your
                  receive buckets can still pull assets from any team in a multi-team deal.
                </p>
                <div className="rounded-xl border border-border/70 bg-background/70 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                    Deal Shape
                  </p>
                  <p className="mt-2 text-sm font-semibold">
                    {thirdPartyTrades.length
                      ? `2 core teams + ${thirdPartyTrades.length} extra`
                      : "2 core teams"}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Extra teams are included in the request payload even though scoring remains
                    user-centric today.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {thirdPartyTrades.length ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                    Multi-Team Legs
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Track what each extra roster sends into and receives from the deal.
                  </p>
                </div>
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                {thirdPartyTrades.map((trade, index) => {
                  const isActiveTrade =
                    queryTarget.kind === "third-party" && queryTarget.tradeId === trade.clientId

                  return (
                    <Card
                      key={trade.clientId}
                      className={
                        isActiveTrade
                          ? "border-amber-400/70 shadow-[0_18px_42px_-28px_rgba(217,119,6,0.55)]"
                          : "border-dashed"
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
                            Capture the sidecar leg without changing the primary evaluation lens.
                          </p>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => removeThirdPartyTrade(trade.clientId)}
                        >
                          Remove
                        </Button>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <RosterField
                          label="Third Team Roster"
                          value={trade.rosterId}
                          onChange={(value) =>
                            updateThirdPartyTrade(trade.clientId, (current) => ({
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
                            pickValuesByKey={pickValuesByKey}
                            onSelect={() =>
                              setActiveTarget({
                                kind: "third-party",
                                tradeId: trade.clientId,
                                bucket: "send",
                              })
                            }
                            onRemove={(assetIndex) =>
                              removeThirdPartyAsset(trade.clientId, "send", assetIndex)
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
                            pickValuesByKey={pickValuesByKey}
                            onSelect={() =>
                              setActiveTarget({
                                kind: "third-party",
                                tradeId: trade.clientId,
                                bucket: "receive",
                              })
                            }
                            onRemove={(assetIndex) =>
                              removeThirdPartyAsset(trade.clientId, "receive", assetIndex)
                            }
                          />
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>
          ) : null}

          <Card className="border-dashed bg-card/70">
            <CardHeader>
              <CardTitle>{searchTitle}</CardTitle>
              <p className="text-sm text-muted-foreground">{searchDescription}</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <input
                value={queryText}
                onChange={(event) => setQueryText(event.target.value)}
                className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
                placeholder={
                  activeRosterId
                    ? "Leave blank to browse the roster, or type to filter players..."
                    : "Search players or picks..."
                }
                disabled={!canSearchAssets}
              />

              {leagueId.trim().length > 0 && !hasScopedRoster ? (
                <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-900 dark:border-amber-700/40 dark:bg-amber-950/30 dark:text-amber-200">
                  {queryTarget.kind === "user"
                    ? "Your team has not been identified for this league yet."
                    : "Select the third team roster before searching its outgoing assets."}
                </p>
              ) : null}

              {playerSearchQuery.data?.length ? (
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                    {queryText.trim().length >= 2 ? "Player Results" : "Roster Players"}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {playerSearchQuery.data.map((player) => (
                      <Button
                        key={`${player.player_id}-${player.roster_id}`}
                        variant="outline"
                        size="sm"
                        onClick={() => addAsset(toPlayerAsset(player))}
                      >
                        {player.full_name} ({player.position})
                        {activeRosterId ? "" : ` • ${player.roster_name}`}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : null}

              {queryText.trim().length >= 2 &&
              playerSearchQuery.isSuccess &&
              !playerSearchQuery.data?.length ? (
                <p className="text-sm text-muted-foreground">
                  No players matched this target.
                </p>
              ) : null}

              {activeRosterId &&
              playerSearchQuery.isSuccess &&
              queryText.trim().length === 0 &&
              !playerSearchQuery.data?.length ? (
                <p className="text-sm text-muted-foreground">
                  No roster players were available for this team.
                </p>
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
                        onClick={() => addAsset(toPickAsset(pick))}
                      >
                        {pick.current_owner_name}&apos;s {pick.pick_year} R{pick.round}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              className="w-full sm:w-auto"
              disabled={!canEvaluate || evaluationMutation.isPending}
              onClick={() => {
                setShowPackage(false)
                setShowReroutes(false)
                evaluationMutation.mutate(currentRequest)
              }}
            >
              {evaluationMutation.isPending ? "Evaluating..." : "Evaluate"}
            </Button>
            {thirdPartyTrades.length ? (
              <p className="max-w-2xl text-xs text-muted-foreground">
                Multi-team legs are sent with the request, but the current scorecard still
                evaluates your send/receive package and the primary counterparty manager profile.
              </p>
            ) : null}
          </div>

          {evaluationMutation.isError ? (
            <p className="text-sm text-red-600">
              Trade evaluation failed. Check the selected league and rosters, then try again.
            </p>
          ) : null}
        </CardContent>
      </Card>

      {evaluation ? (
        <>
          <EvaluationOutputPanel
            evaluation={evaluation}
            userSends={userSends}
            userReceives={userReceives}
            pickValuesByKey={pickValuesByKey}
            counterpartyName={counterpartyRosterName}
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
