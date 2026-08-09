import type { ProspectModelOutput, RookieTier } from "@/api/types"
import { RookiePlayerCard } from "@/components/rookie/RookiePlayerCard"
import { TierDivider } from "@/components/rookie/TierDivider"

const AVAILABILITY_THRESHOLD = 0.5

export function TierGroup({
  tier,
  selectedSlot,
  prospectMap,
  isModelLoading = false,
}: {
  tier: RookieTier
  selectedSlot?: string
  prospectMap?: Map<string, ProspectModelOutput>
  isModelLoading?: boolean
}) {
  return (
    <div>
      <TierDivider label={tier.label} playerCount={tier.players.length} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tier.players.map((player) => (
          <RookiePlayerCard
            key={player.player_id}
            player={player}
            modelOutput={prospectMap?.get(player.player_id) ?? null}
            isModelLoading={isModelLoading}
            selectedSlot={selectedSlot}
            isAvailableAtSlot={
              selectedSlot
                ? (player.available_probability_by_slot[selectedSlot] ?? 0) >=
                  AVAILABILITY_THRESHOLD
                : false
            }
          />
        ))}
      </div>
    </div>
  )
}
