import type { TradeAsset } from "@/api/types"

export interface TradeRouteSearch {
  leagueId?: string
  userRosterId?: number
  counterpartyRosterId?: number
  targetPlayerId?: string
  targetPlayerName?: string
  targetPlayerPosition?: string
  targetPlayerRosterId?: number
  sendPlayerId?: string
  sendPlayerName?: string
  sendPlayerPosition?: string
  receivePlayerId?: string
  receivePlayerName?: string
  receivePlayerPosition?: string
}

function numberParam(value: unknown): number | undefined {
  if (typeof value === "number") return value
  if (typeof value === "string") return Number(value) || undefined
  return undefined
}

function rawStringParam(key: string): string | undefined {
  if (typeof window === "undefined") {
    return undefined
  }
  return new URLSearchParams(window.location.search).get(key) ?? undefined
}

function stringParam(search: Record<string, unknown>, key: string): string | undefined {
  const value = search[key]
  if (typeof value === "string") return value
  if (typeof value === "number") return rawStringParam(key) ?? String(value)
  return undefined
}

export function validateTradeSearch(
  search: Record<string, unknown>,
): TradeRouteSearch {
  return {
    leagueId: stringParam(search, "leagueId"),
    userRosterId: numberParam(search.userRosterId),
    counterpartyRosterId: numberParam(search.counterpartyRosterId),
    targetPlayerId: stringParam(search, "targetPlayerId"),
    targetPlayerName: stringParam(search, "targetPlayerName"),
    targetPlayerPosition: stringParam(search, "targetPlayerPosition"),
    targetPlayerRosterId: numberParam(search.targetPlayerRosterId),
    sendPlayerId: stringParam(search, "sendPlayerId"),
    sendPlayerName: stringParam(search, "sendPlayerName"),
    sendPlayerPosition: stringParam(search, "sendPlayerPosition"),
    receivePlayerId: stringParam(search, "receivePlayerId"),
    receivePlayerName: stringParam(search, "receivePlayerName"),
    receivePlayerPosition: stringParam(search, "receivePlayerPosition"),
  }
}

export function searchPlayerAsset(
  playerId: string | undefined,
  playerName: string | undefined,
  playerPosition: string | undefined,
): TradeAsset | null {
  if (!playerId || !playerName) {
    return null
  }
  return {
    asset_type: "player",
    player_id: playerId,
    player_name: playerName,
    player_position: playerPosition ?? null,
  }
}

export function nameOnlyPrefillText(search: TradeRouteSearch): string | null {
  if (!search.targetPlayerId && search.targetPlayerName) {
    return search.targetPlayerName
  }
  if (!search.receivePlayerId && search.receivePlayerName) {
    return search.receivePlayerName
  }
  if (!search.sendPlayerId && search.sendPlayerName) {
    return search.sendPlayerName
  }
  return null
}
