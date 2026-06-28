import { useEffect, useMemo, useState } from "react"

import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import type {
  PickSearchResult,
  PlayerSearchResult,
  TradeAsset,
  TradeEvaluation,
  TradeRosterResult,
} from "@/api/types"
import { dashboardSummaryOptions, pickValuesOptions } from "@/api/queries"
import { EvaluationOutputPanel } from "@/components/trade/EvaluationOutputPanel"
import { PackageBuilderPanel } from "@/components/trade/PackageBuilderPanel"
import { RerouteSheet } from "@/components/trade/RerouteSheet"
import { LeagueField, RosterField } from "@/components/trade/TradeBuilderFields"
import {
  CoreDealBoard,
  SuggestedOfferStartCard,
  ThirdPartyTradeCards,
  TradeAssetSearchCard,
} from "@/components/trade/TradeRouteSections"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  resolveTradeAssetRosterId,
  type AssetBucket,
  type QueryTarget,
} from "@/lib/tradeAssetSearch"
import {
  appendUniqueAsset,
  createThirdPartyTradeDraft,
  pickValueKeyFromValue,
  toPickAsset,
  toPlayerAsset,
  toRequestAsset,
  toThirdPartyTrade,
  type ThirdPartyTradeDraft,
} from "@/lib/tradeRouteHelpers"
import { textToneClasses } from "@/lib/ui-tokens"
import { validateTradeSearch } from "@/lib/tradeSearchParams"
import { useTradePrefill } from "@/lib/useTradePrefill"

async function fetchJson<T>(path: string) {
  const response = await fetch(`/api${path}`)
  if (!response.ok) throw new Error(`Request failed: ${path}`)
  return (await response.json()) as T
}

export const Route = createFileRoute("/trades")({
  validateSearch: validateTradeSearch,
  component: TradeEvaluatorPage,
})

function TradeEvaluatorPage() {
  const search = Route.useSearch()
  const [leagueId, setLeagueId] = useState(search.leagueId ?? "")
  const [counterpartyRosterId, setCounterpartyRosterId] = useState(
    search.counterpartyRosterId ?? 0,
  )
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
  const userRosterId = search.userRosterId ?? selectedLeague?.user_roster_id ?? 0
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
  const { prefilledPlayerAsset, prefilledSendAsset, prefilledReceiveAsset } =
    useTradePrefill({
    search,
    leagueId,
    counterpartyRosterId,
    setCounterpartyRosterId,
    setLeagueId,
    setQueryTarget,
    setUserReceives,
    setUserSends,
    userRosterId,
  })

  useEffect(() => {
    if (rostersQuery.isLoading) {
      return
    }

    if (!counterpartyOptions.length) {
      if (counterpartyRosterId !== 0 && !search.counterpartyRosterId) {
        setCounterpartyRosterId(0)
      }
      return
    }

    if (
      !search.counterpartyRosterId &&
      !counterpartyOptions.some((option) => option.roster_id === counterpartyRosterId)
    ) {
      setCounterpartyRosterId(counterpartyOptions[0]?.roster_id ?? 0)
    }
  }, [
    counterpartyOptions,
    counterpartyRosterId,
    rostersQuery.isLoading,
    search.counterpartyRosterId,
  ])

  const activeThirdParty =
    queryTarget.kind === "third-party"
      ? thirdPartyTrades.find((trade) => trade.clientId === queryTarget.tradeId) ?? null
      : null

  const activeThirdPartyIndex =
    queryTarget.kind === "third-party"
      ? thirdPartyTrades.findIndex((trade) => trade.clientId === queryTarget.tradeId)
      : -1

  const activeRosterId = resolveTradeAssetRosterId({
    queryTarget,
    userRosterId,
    counterpartyRosterId,
    activeThirdPartyRosterId: activeThirdParty?.rosterId,
  })

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
  const showSuggestedStart =
    leagueId.trim().length > 0 && userSends.length === 0 && userReceives.length === 0

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader className="space-y-2">
          <p className="terminal-label text-primary/85">Deal intelligence</p>
          <CardTitle className="text-3xl">Evaluate Trade</CardTitle>
          <p className="max-w-3xl text-sm text-muted-foreground">
            Build your outgoing and incoming package first, then layer in extra teams for
            multi-team trades. The seven dimensions stay anchored to your net swap, while
            reroutes and package framing can explain each participant's path through the deal.
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
            <p className="rounded-lg border border-destructive/25 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              Your team could not be identified for this league, so trade evaluation is disabled.
            </p>
          ) : null}

          {showSuggestedStart ? (
            <SuggestedOfferStartCard
              prefilledPlayerAsset={prefilledPlayerAsset}
              prefilledSendAsset={prefilledSendAsset}
              prefilledReceiveAsset={prefilledReceiveAsset}
            />
          ) : null}

          <CoreDealBoard
            userRosterName={userRosterName}
            counterpartyRosterName={counterpartyRosterName}
            counterpartyRosterId={counterpartyRosterId}
            thirdPartyCount={thirdPartyTrades.length}
            queryTarget={queryTarget}
            userSends={userSends}
            userReceives={userReceives}
            leagueId={leagueId}
            pickValuesByKey={pickValuesByKey}
            onSetActiveTarget={setActiveTarget}
            onRemoveUserAsset={removeUserAsset}
          />

          <ThirdPartyTradeCards
            trades={thirdPartyTrades}
            queryTarget={queryTarget}
            rosterNameById={rosterNameById}
            rosterOptions={rosterOptions}
            leagueId={leagueId}
            pickValuesByKey={pickValuesByKey}
            onSetActiveTarget={setActiveTarget}
            onUpdateTrade={updateThirdPartyTrade}
            onRemoveTrade={removeThirdPartyTrade}
            onRemoveAsset={removeThirdPartyAsset}
          />

          <TradeAssetSearchCard
            title={searchTitle}
            description={searchDescription}
            queryText={queryText}
            activeRosterId={activeRosterId}
            canSearchAssets={canSearchAssets}
            hasScopedRoster={hasScopedRoster}
            queryTarget={queryTarget}
            leagueId={leagueId}
            playerResults={playerSearchQuery.data}
            playerSearchSuccess={playerSearchQuery.isSuccess}
            pickOptions={pickOptions}
            onQueryTextChange={setQueryText}
            onAddPlayer={(player) => addAsset(toPlayerAsset(player))}
            onAddPick={(pick) => addAsset(toPickAsset(pick))}
          />

          <div className="flex flex-wrap items-center gap-3 border-t border-border/40 pt-2">
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
                Multi-team legs return sidecar scores that feed participant-specific reroutes
                and package explanations.
              </p>
            ) : null}
          </div>

          {evaluationMutation.isError ? (
            <p className={`text-sm ${textToneClasses.destructive}`}>
              Trade evaluation failed. Check the selected league and rosters, then try again.
            </p>
          ) : null}
        </CardContent>
      </Card>

      {evaluation ? (
        <>
          <EvaluationOutputPanel
            evaluation={evaluation}
            leagueId={leagueId}
            userSends={userSends}
            userReceives={userReceives}
            pickValuesByKey={pickValuesByKey}
            counterpartyName={counterpartyRosterName}
            rosterNamesById={rosterNameById}
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
