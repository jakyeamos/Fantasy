import { useEffect, useMemo, useRef, type Dispatch, type SetStateAction } from "react"

import type { TradeAsset } from "@/api/types"
import type { QueryTarget } from "@/lib/tradeAssetSearch"
import { appendUniqueAsset } from "@/lib/tradeRouteHelpers"
import { searchPlayerAsset, type TradeRouteSearch } from "@/lib/tradeSearchParams"

export function useTradePrefill({
  search,
  leagueId,
  setLeagueId,
  counterpartyRosterId,
  setCounterpartyRosterId,
  userRosterId,
  setUserSends,
  setUserReceives,
  setQueryTarget,
}: {
  search: TradeRouteSearch
  leagueId: string
  setLeagueId: Dispatch<SetStateAction<string>>
  counterpartyRosterId: number
  setCounterpartyRosterId: Dispatch<SetStateAction<number>>
  userRosterId: number
  setUserSends: Dispatch<SetStateAction<TradeAsset[]>>
  setUserReceives: Dispatch<SetStateAction<TradeAsset[]>>
  setQueryTarget: Dispatch<SetStateAction<QueryTarget>>
}) {
  const prefillKeyRef = useRef<string | null>(null)
  const prefilledPlayerAsset = useMemo(
    () =>
      searchPlayerAsset(
        search.targetPlayerId,
        search.targetPlayerName,
        search.targetPlayerPosition,
      ),
    [search.targetPlayerId, search.targetPlayerName, search.targetPlayerPosition],
  )
  const prefilledSendAsset = useMemo(
    () =>
      searchPlayerAsset(
        search.sendPlayerId,
        search.sendPlayerName,
        search.sendPlayerPosition,
      ),
    [search.sendPlayerId, search.sendPlayerName, search.sendPlayerPosition],
  )
  const prefilledReceiveAsset = useMemo(
    () =>
      searchPlayerAsset(
        search.receivePlayerId,
        search.receivePlayerName,
        search.receivePlayerPosition,
      ),
    [search.receivePlayerId, search.receivePlayerName, search.receivePlayerPosition],
  )
  const prefillTargetRosterId =
    search.targetPlayerRosterId ?? search.counterpartyRosterId ?? 0

  useEffect(() => {
    if (search.leagueId && search.leagueId !== leagueId) {
      setLeagueId(search.leagueId)
      prefillKeyRef.current = null
    }
    if (
      search.counterpartyRosterId &&
      search.counterpartyRosterId !== counterpartyRosterId
    ) {
      setCounterpartyRosterId(search.counterpartyRosterId)
    }
  }, [
    counterpartyRosterId,
    leagueId,
    search.counterpartyRosterId,
    search.leagueId,
    setCounterpartyRosterId,
    setLeagueId,
  ])

  useEffect(() => {
    if (prefilledSendAsset || prefilledReceiveAsset) {
      const prefillKey = [
        leagueId,
        userRosterId,
        counterpartyRosterId,
        prefilledSendAsset?.player_id ?? "",
        prefilledReceiveAsset?.player_id ?? "",
      ].join(":")
      if (prefillKeyRef.current === prefillKey || userRosterId <= 0) {
        return
      }

      prefillKeyRef.current = prefillKey
      if (prefilledSendAsset) {
        setUserSends((current) => appendUniqueAsset(current, prefilledSendAsset))
      }
      if (prefilledReceiveAsset) {
        setUserReceives((current) => appendUniqueAsset(current, prefilledReceiveAsset))
      }
      if (counterpartyRosterId > 0) {
        setQueryTarget({ kind: "user", bucket: "receive" })
      }
      return
    }

    if (!prefilledPlayerAsset || !prefillTargetRosterId || userRosterId <= 0) {
      return
    }

    const prefillKey = [
      leagueId,
      userRosterId,
      prefillTargetRosterId,
      prefilledPlayerAsset.player_id,
    ].join(":")
    if (prefillKeyRef.current === prefillKey) {
      return
    }

    prefillKeyRef.current = prefillKey
    if (prefillTargetRosterId === userRosterId) {
      setUserSends((current) => appendUniqueAsset(current, prefilledPlayerAsset))
      setQueryTarget({ kind: "user", bucket: "send" })
      return
    }

    setCounterpartyRosterId(prefillTargetRosterId)
    setUserReceives((current) => appendUniqueAsset(current, prefilledPlayerAsset))
    setQueryTarget({ kind: "user", bucket: "receive" })
  }, [
    counterpartyRosterId,
    leagueId,
    prefilledPlayerAsset,
    prefilledReceiveAsset,
    prefilledSendAsset,
    prefillTargetRosterId,
    setCounterpartyRosterId,
    setQueryTarget,
    setUserReceives,
    setUserSends,
    userRosterId,
  ])

  return {
    prefilledPlayerAsset,
    prefilledSendAsset,
    prefilledReceiveAsset,
  }
}
