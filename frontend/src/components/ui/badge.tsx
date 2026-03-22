import { cn } from "@/lib/utils"

type BadgeVariant = "default" | "secondary" | "outline"

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-primary text-primary-foreground",
  secondary: "bg-secondary text-secondary-foreground",
  outline: "border border-border bg-transparent text-muted-foreground",
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
        "inline-flex items-center rounded-full px-2.5 py-1 text-[12px] font-medium",
        variantClasses[variant],
        className,
      )}
    >
      {children}
    </span>
  )
}
