import type { TradeHistoryEntry } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { textToneClasses } from "@/lib/ui-tokens"

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
        <p className="mt-2 text-sm text-muted-foreground">
          Historical deal outcomes for this manager’s trade record.
        </p>
      </CardHeader>
      <CardContent>
        {trades.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No trade history found for this manager.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border/40">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-card/45 text-xs uppercase tracking-label text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Assets Sent</th>
                  <th className="px-4 py-3">Assets Received</th>
                  <th className="px-4 py-3 text-right">Value Delta</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => (
                  <tr key={trade.transaction_id} className="border-t border-border/40">
                    <td className="px-4 py-4 text-xs text-muted-foreground">
                      {formatDate(trade.date)}
                    </td>
                    <td className="px-4 py-4 text-sm">
                      {trade.sent_assets.join(", ")}
                    </td>
                    <td className="px-4 py-4 text-sm">
                      {trade.received_assets.join(", ")}
                    </td>
                    <td
                      className={`px-4 py-4 text-right font-mono text-xs ${
                        trade.value_delta >= 0
                          ? textToneClasses.success
                          : textToneClasses.destructive
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
