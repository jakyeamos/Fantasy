import { useEffect, useMemo, useState } from "react"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import type {
  PickSearchResult,
  PlayerSearchResult,
  TradeAsset,
  TradeEvaluation,
  TradeFollowUpEventRequest,
  TradeRosterResult,
} from "@/api/types"
import {
  dashboardSummaryOptions,
  pickValuesOptions,
  postJson,
  tradeFollowUpsOptions,
} from "@/api/queries"
import { EvaluationOutputPanel } from "@/components/trade/EvaluationOutputPanel"
import { PackageBuilderPanel } from "@/components/trade/PackageBuilderPanel"
import { RerouteSheet } from "@/components/trade/RerouteSheet"
import { LeagueField, RosterField } from "@/components/trade/TradeBuilderFields"
import { TradeFollowUpPanel } from "@/components/trade/TradeFollowUpPanel"
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
import { nameOnlyPrefillText, validateTradeSearch } from "@/lib/tradeSearchParams"
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
  const [counterpartyRosterId, setCounterpartyRosterId] = useState(search.counterpartyRosterId ?? 0)
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
  const queryClient = useQueryClient()
  const leaguesQuery = useQuery(dashboardSummaryOptions)
  const leagueOptions = leaguesQuery.data ?? []
  const inferredLeagueId =
    search.leagueId ??
    leagueOptions.find((option) => option.user_roster_id === search.userRosterId)?.league_id ??
    ""
  const selectedLeague = useMemo(
    () => leagueOptions.find((option) => option.league_id === leagueId) ?? null,
    [leagueId, leagueOptions],
  )
  const userRosterId = search.userRosterId ?? selectedLeague?.user_roster_id ?? 0
  const tradeFollowUpsQuery = useQuery(tradeFollowUpsOptions(leagueId))
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
  const { prefilledPlayerAsset, prefilledSendAsset, prefilledReceiveAsset } = useTradePrefill({
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
  const nameOnlyPrefill = nameOnlyPrefillText(search)

  useEffect(() => {
    if (!search.leagueId && inferredLeagueId && inferredLeagueId !== leagueId) {
      setLeagueId(inferredLeagueId)
    }
  }, [inferredLeagueId, leagueId, search.leagueId])

  const nameOnlyPrefillQuery = useQuery({
    queryKey: ["trade", "prefill", "name", leagueId, nameOnlyPrefill],
    queryFn: async () => {
      const params = new URLSearchParams({
        league_id: leagueId,
        q: nameOnlyPrefill ?? "",
      })
      return fetchJson<PlayerSearchResult[]>(`/trade/players/search?${params.toString()}`)
    },
    enabled:
      Boolean(nameOnlyPrefill) &&
      !prefilledPlayerAsset &&
      !prefilledSendAsset &&
      !prefilledReceiveAsset &&
      leagueId.trim().length > 0,
  })

  useEffect(() => {
    const targetName = nameOnlyPrefill?.toLowerCase()
    if (!targetName || userRosterId <= 0) {
      return
    }
    const resolved = (nameOnlyPrefillQuery.data ?? []).find(
      (player) => player.full_name.toLowerCase() === targetName,
    )
    if (!resolved) {
      return
    }
    const asset = toPlayerAsset(resolved)
    if (search.sendPlayerName && !search.receivePlayerName && !search.targetPlayerName) {
      setUserSends((current) => appendUniqueAsset(current, asset))
      setQueryTarget({ kind: "user", bucket: "send" })
      return
    }
    if (resolved.roster_id !== userRosterId) {
      setCounterpartyRosterId(resolved.roster_id)
    }
    setUserReceives((current) => appendUniqueAsset(current, asset))
    setQueryTarget({ kind: "user", bucket: "receive" })
  }, [
    nameOnlyPrefill,
    nameOnlyPrefillQuery.data,
    search.receivePlayerName,
    search.sendPlayerName,
    search.targetPlayerName,
    setCounterpartyRosterId,
    userRosterId,
  ])

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
      ? (thirdPartyTrades.find((trade) => trade.clientId === queryTarget.tradeId) ?? null)
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
    userRosterId > 0 ? (rosterNameById.get(userRosterId) ?? `Roster ${userRosterId}`) : null
  const counterpartyRosterName =
    counterpartyRosterId > 0
      ? (rosterNameById.get(counterpartyRosterId) ?? `Roster ${counterpartyRosterId}`)
      : null

  const searchTitle =
    queryTarget.kind === "user"
      ? queryTarget.bucket === "send"
        ? "Add to Your Send Side"
        : "Add to Your Receive Side"
      : queryTarget.bucket === "send"
        ? `Add to Third Team ${activeThirdPartyIndex + 1} Send Side`
        : `Add to Third Team ${activeThirdPartyIndex + 1} Receive Side`

  const searchDescription = !hasScopedRoster
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
          (trade) => trade.rosterId > 0 && (trade.sends.length > 0 || trade.receives.length > 0),
        )
        .map(toThirdPartyTrade),
      include_reroutes: true,
      include_package: true,
    }),
    [counterpartyRosterId, leagueId, thirdPartyTrades, userReceives, userRosterId, userSends],
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
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["trade", "follow-ups", leagueId] })
    },
  })

  const followUpMutation = useMutation({
    mutationFn: async ({
      decisionId,
      request,
    }: {
      decisionId: string
      request: TradeFollowUpEventRequest
    }) =>
      postJson(
        `/trade/follow-ups/${encodeURIComponent(decisionId)}?league_id=${encodeURIComponent(leagueId)}`,
        request,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["trade", "follow-ups", leagueId] })
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
      activeRosterId ? (pickSearchQuery.data ?? []) : (pickSearchQuery.data?.slice(0, 24) ?? []),
    [activeRosterId, pickSearchQuery.data],
  )

  const setActiveTarget = (target: QueryTarget) => {
    setQueryTarget(target)
    setQueryText("")
  }

  const addThirdPartyTrade = () => {
    const nextTrade = createThirdPartyTradeDraft()
    setThirdPartyTrades((current) => [...current, nextTrade])
    setActiveTarget({
      kind: "third-party",
      tradeId: nextTrade.clientId,
      bucket: "send",
    })
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
      sends: queryTarget.bucket === "send" ? appendUniqueAsset(trade.sends, asset) : trade.sends,
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

  const removeThirdPartyAsset = (tradeId: string, bucket: AssetBucket, index: number) => {
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
      (trade) => trade.rosterId > 0 || (trade.sends.length === 0 && trade.receives.length === 0),
    )
  const showSuggestedStart =
    leagueId.trim().length > 0 && userSends.length === 0 && userReceives.length === 0

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader className="space-y-2">
          <p className="terminal-label text-primary/85">
            Prepared action · manual execution boundary
          </p>
          <CardTitle className="text-3xl">Trade Preparation</CardTitle>
          <p className="max-w-3xl text-sm text-muted-foreground">
            Build the outgoing and incoming package, attach the manager pitch, and inspect the
            evidence before deciding whether to send. This surface prepares a trade; it never
            submits one.
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
                Multi-team legs return sidecar scores that feed participant-specific reroutes and
                package explanations.
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

      {leagueId.trim().length > 0 ? (
        <>
          <TradeFollowUpPanel
            data={tradeFollowUpsQuery.data}
            isLoading={tradeFollowUpsQuery.isLoading}
            pendingDecisionId={
              followUpMutation.isPending ? (followUpMutation.variables?.decisionId ?? null) : null
            }
            onEvent={async (decisionId, request) => {
              await followUpMutation.mutateAsync({ decisionId, request })
            }}
          />
          {followUpMutation.isError ? (
            <p className={`text-sm ${textToneClasses.destructive}`}>
              Trade Lab check-in failed. The original decision is unchanged; try the event again.
            </p>
          ) : null}
        </>
      ) : null}

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
