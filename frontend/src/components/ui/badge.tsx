import { cn } from "@/lib/utils"

type BadgeVariant = "default" | "secondary" | "outline"

const variantClasses: Record<BadgeVariant, string> = {
  default: "border border-primary/30 bg-primary/14 text-primary",
  secondary: "border border-accent/20 bg-accent/10 text-accent",
  outline: "border border-border/60 bg-transparent text-muted-foreground",
}

export function Badge({
  className,
  variant = "default",
  children,
}: {
  className?: string
  variant?: BadgeVariant
  children: React.ReactNode
}) {
  return (
    <span
      className={cn(
        "font-label inline-flex items-center rounded-md px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em]",
        variantClasses[variant],
        className,
      )}
    >
      {children}
    </span>
  )
}
