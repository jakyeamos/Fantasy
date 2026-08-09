import type {
  PickSearchResult,
  PickValue,
  PlayerSearchResult,
  ThirdPartyTrade,
  TradeAsset,
} from "@/api/types"

export interface ThirdPartyTradeDraft {
  clientId: string
  rosterId: number
  sends: TradeAsset[]
  receives: TradeAsset[]
}

export function createThirdPartyTradeDraft(): ThirdPartyTradeDraft {
  return {
    clientId: Math.random().toString(36).slice(2, 10),
    rosterId: 0,
    sends: [],
    receives: [],
  }
}

export function assetKey(asset: TradeAsset): string {
  if (asset.asset_type === "player") {
    return `player:${asset.player_id ?? "unknown"}`
  }
  return `pick:${asset.pick_owner_roster_id ?? "unknown"}:${asset.pick_year ?? "unknown"}:${asset.pick_round ?? "unknown"}`
}

export function appendUniqueAsset(assets: TradeAsset[], asset: TradeAsset): TradeAsset[] {
  if (assets.some((current) => assetKey(current) === assetKey(asset))) {
    return assets
  }
  return [...assets, asset]
}

export function toPlayerAsset(player: PlayerSearchResult): TradeAsset {
  return {
    asset_type: "player",
    player_id: player.player_id,
    player_name: player.full_name,
    player_position: player.position,
  }
}

export function toPickAsset(pick: PickSearchResult): TradeAsset {
  return {
    asset_type: "pick",
    pick_owner_roster_id: pick.original_owner_id,
    pick_owner_name: pick.original_owner_name,
    pick_year: pick.pick_year,
    pick_round: pick.round,
    projected_slot: pick.projected_slot,
  }
}

export function pickValueKeyFromAsset(asset: TradeAsset): string {
  return `${asset.pick_owner_roster_id ?? 0}:${asset.pick_year ?? 0}:${asset.pick_round ?? 0}`
}

export function pickValueKeyFromValue(pickValue: PickValue): string {
  return `${pickValue.pick.pick_owner_roster_id}:${pickValue.pick.pick_year}:${pickValue.pick.pick_round}`
}

export function toRequestAsset(asset: TradeAsset): TradeAsset {
  return {
    asset_type: asset.asset_type,
    player_id: asset.player_id ?? null,
    pick_owner_roster_id: asset.pick_owner_roster_id ?? null,
    pick_year: asset.pick_year ?? null,
    pick_round: asset.pick_round ?? null,
    projected_slot: asset.projected_slot ?? null,
  }
}

export function toThirdPartyTrade(trade: ThirdPartyTradeDraft): ThirdPartyTrade {
  return {
    roster_id: trade.rosterId,
    sends: trade.sends.map(toRequestAsset),
    receives: trade.receives.map(toRequestAsset),
  }
}

export function assetDetail(asset: TradeAsset): string | undefined {
  if (asset.asset_type === "player") {
    return asset.player_position ?? undefined
  }
  return asset.projected_slot ?? undefined
}
