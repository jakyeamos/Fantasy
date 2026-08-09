import type { RecommendationCard as RecommendationCardType } from "@/api/types"
import { RecommendationCard } from "@/components/recommendations/RecommendationCard"

export function RecommendationCardList({
  cards,
  onCta,
}: {
  cards: RecommendationCardType[]
  onCta?: (card: RecommendationCardType) => void
}) {
  if (cards.length === 0) {
    return (
      <div className="rounded-lg border border-border/40 bg-card/45 px-3 py-2 text-sm text-muted-foreground">
        No recommendation cards are available yet.
      </div>
    )
  }

  const orderedCards = [...cards].sort(
    (left, right) => left.priority_rank - right.priority_rank,
  )

  return (
    <div className="space-y-3">
      {orderedCards.map((card, index) => (
        <RecommendationCard
          key={`${card.recommendation_type}-${card.priority_rank}-${index}`}
          card={card}
          onCta={onCta}
        />
      ))}
    </div>
  )
}
