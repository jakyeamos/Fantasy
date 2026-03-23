import type { TradeHistoryEntry } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function formatDate(value: string | null) {
  if (!value) return "Unknown"
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    year: "numeric",
  })
}

export function DossierTradeHistoryTab({
  trades,
}: {
  trades: TradeHistoryEntry[]
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Trade History</CardTitle>
      </CardHeader>
      <CardContent>
        {trades.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No trade history found for this manager.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                <tr>
                  <th className="px-2 py-2">Date</th>
                  <th className="px-2 py-2">Assets Sent</th>
                  <th className="px-2 py-2">Assets Received</th>
                  <th className="px-2 py-2 text-right">Value Delta</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => (
                  <tr key={trade.transaction_id} className="border-t border-border/60">
                    <td className="px-2 py-3 text-xs text-muted-foreground">
                      {formatDate(trade.date)}
                    </td>
                    <td className="px-2 py-3 text-sm">
                      {trade.sent_assets.join(", ")}
                    </td>
                    <td className="px-2 py-3 text-sm">
                      {trade.received_assets.join(", ")}
                    </td>
                    <td
                      className={`px-2 py-3 text-right text-xs ${
                        trade.value_delta >= 0
                          ? "text-green-600 dark:text-green-400"
                          : "text-red-600 dark:text-red-400"
                      }`}
                    >
                      {trade.value_delta > 0 ? "+" : ""}
                      {trade.value_delta.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
