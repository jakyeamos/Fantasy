import { useState } from "react"

import { ChevronDown, ChevronUp } from "lucide-react"

import type { SimilarPlayer } from "@/api/types"

export function SimilarPlayersSection({
  players,
}: {
  players: SimilarPlayer[]
}) {
  const [open, setOpen] = useState(false)

  if (players.length === 0) {
    return null
  }

  return (
    <div className="mt-3">
      <button
        type="button"
        className="flex items-center gap-1.5 text-left"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
      >
        <span className="terminal-label text-muted-foreground">
          SIMILAR PLAYERS ({players.length})
        </span>
        {open ? (
          <ChevronUp className="size-3 text-muted-foreground" />
        ) : (
          <ChevronDown className="size-3 text-muted-foreground" />
        )}
      </button>

      {open ? (
        <div className="mt-2 space-y-2 transition-all duration-150 ease-out">
          {players.map((player) => (
            <div
              key={player.player_id}
              className="flex items-start justify-between gap-3"
            >
              <div>
                <p className="text-sm font-bold text-foreground">
                  {player.player_name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {player.context}
                </p>
              </div>
              <span className="font-mono text-xs text-muted-foreground">
                {(player.similarity_score * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
