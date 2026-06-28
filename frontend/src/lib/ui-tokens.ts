import type { CalendarState } from "@/api/types"

export const badgeToneClasses = {
  primary: "border-primary/25 bg-primary/10 text-primary",
  accent: "border-accent/20 bg-accent/10 text-accent-foreground",
  success: "border-success/25 bg-success-surface text-success",
  warning: "border-warning/25 bg-warning-surface text-warning",
  attention: "border-attention/25 bg-attention-surface text-attention",
  info: "border-info/25 bg-info-surface text-info",
  strategy: "border-strategy/25 bg-strategy-surface text-strategy",
  destructive: "border-destructive/25 bg-destructive-surface text-destructive",
  neutral: "border-border/40 bg-card/45 text-muted-foreground",
} as const

export const surfaceToneClasses = {
  primary: "border-primary/25 bg-primary/10",
  success: "border-success/25 bg-success-surface",
  warning: "border-warning/25 bg-warning-surface",
  attention: "border-attention/25 bg-attention-surface",
  info: "border-info/25 bg-info-surface",
  strategy: "border-strategy/25 bg-strategy-surface",
  destructive: "border-destructive/25 bg-destructive-surface",
  neutral: "border-border/40 bg-card/45",
} as const

export const textToneClasses = {
  primary: "text-primary",
  success: "text-success",
  warning: "text-warning",
  attention: "text-attention",
  info: "text-info",
  strategy: "text-strategy",
  destructive: "text-destructive",
  neutral: "text-muted-foreground",
} as const

export const seasonBadgeClasses: Record<CalendarState, string> = {
  startup: "bg-season-startup-surface text-season-startup",
  preseason: "bg-season-preseason-surface text-season-preseason",
  early_season: "bg-season-early-surface text-season-early",
  trade_deadline: "bg-season-deadline-surface text-season-deadline",
  playoffs: "bg-season-playoffs-surface text-season-playoffs",
  rookie_fever: "bg-season-rookie-surface text-season-rookie",
  post_combine: "bg-season-combine-surface text-season-combine",
  post_nfl_draft: "bg-season-draft-surface text-season-draft",
}
