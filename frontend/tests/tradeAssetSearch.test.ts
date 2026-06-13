import assert from "node:assert/strict"

import { resolveTradeAssetRosterId } from "../src/lib/tradeAssetSearch"

assert.equal(
  resolveTradeAssetRosterId({
    queryTarget: { kind: "user", bucket: "send" },
    userRosterId: 1,
    counterpartyRosterId: 2,
  }),
  1,
)

assert.equal(
  resolveTradeAssetRosterId({
    queryTarget: { kind: "user", bucket: "receive" },
    userRosterId: 1,
    counterpartyRosterId: 2,
  }),
  2,
)

assert.equal(
  resolveTradeAssetRosterId({
    queryTarget: { kind: "third-party", tradeId: "third", bucket: "send" },
    userRosterId: 1,
    counterpartyRosterId: 2,
    activeThirdPartyRosterId: 3,
  }),
  3,
)

assert.equal(
  resolveTradeAssetRosterId({
    queryTarget: { kind: "third-party", tradeId: "third", bucket: "receive" },
    userRosterId: 1,
    counterpartyRosterId: 2,
    activeThirdPartyRosterId: 3,
  }),
  undefined,
)
