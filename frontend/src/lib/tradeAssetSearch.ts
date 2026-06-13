export type AssetBucket = "send" | "receive"

export type QueryTarget =
  | { kind: "user"; bucket: AssetBucket }
  | { kind: "third-party"; tradeId: string; bucket: AssetBucket }

export function resolveTradeAssetRosterId({
  queryTarget,
  userRosterId,
  counterpartyRosterId,
  activeThirdPartyRosterId,
}: {
  queryTarget: QueryTarget
  userRosterId: number
  counterpartyRosterId: number
  activeThirdPartyRosterId?: number | null
}): number | undefined {
  if (queryTarget.kind === "user") {
    const rosterId =
      queryTarget.bucket === "send" ? userRosterId : counterpartyRosterId
    return rosterId > 0 ? rosterId : undefined
  }

  if (queryTarget.bucket === "send" && activeThirdPartyRosterId) {
    return activeThirdPartyRosterId > 0 ? activeThirdPartyRosterId : undefined
  }

  return undefined
}
