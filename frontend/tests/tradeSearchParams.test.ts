import assert from "node:assert/strict"

import { validateTradeSearch } from "../src/lib/tradeSearchParams"

const previousWindow = globalThis.window

Object.defineProperty(globalThis, "window", {
  configurable: true,
  value: {
    location: {
      search:
        "?leagueId=1312030505352298496&userRosterId=1&counterpartyRosterId=12&receivePlayerId=421&receivePlayerName=Matthew+Stafford&receivePlayerPosition=QB&targetPlayerId=421&targetPlayerName=Matthew+Stafford&targetPlayerPosition=QB",
    },
  },
})

assert.deepEqual(
  validateTradeSearch({
    leagueId: 1312030505352298500,
    userRosterId: 1,
    counterpartyRosterId: 12,
    receivePlayerId: 421,
    receivePlayerName: "Matthew Stafford",
    receivePlayerPosition: "QB",
    targetPlayerId: 421,
    targetPlayerName: "Matthew Stafford",
    targetPlayerPosition: "QB",
  }),
  {
    leagueId: "1312030505352298496",
    userRosterId: 1,
    counterpartyRosterId: 12,
    receivePlayerId: "421",
    receivePlayerName: "Matthew Stafford",
    receivePlayerPosition: "QB",
    targetPlayerId: "421",
    targetPlayerName: "Matthew Stafford",
    targetPlayerPosition: "QB",
    targetPlayerRosterId: undefined,
    sendPlayerId: undefined,
    sendPlayerName: undefined,
    sendPlayerPosition: undefined,
  },
)

if (previousWindow === undefined) {
  Reflect.deleteProperty(globalThis, "window")
} else {
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: previousWindow,
  })
}
