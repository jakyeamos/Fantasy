import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

import type { DirectionReadBand } from "@/api/types"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatModelLabel(value: string | null | undefined) {
  if (!value) return value
  if (!/[_-]/.test(value)) return value

  return value
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

export function directionReadBadgeVariant(directionRead: DirectionReadBand) {
  if (directionRead === "Clear") return "default"
  if (directionRead === "Leaning") return "secondary"
  return "outline"
}
