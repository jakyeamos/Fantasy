import * as React from "react"

import { cn } from "@/lib/utils"

type ButtonVariant = "default" | "secondary" | "outline" | "ghost" | "link"
type ButtonSize = "default" | "sm" | "lg"

const variantClasses: Record<ButtonVariant, string> = {
  default:
    "border border-primary/45 bg-primary text-primary-foreground shadow-[0_0_24px_-12px_rgba(123,208,255,0.85)] hover:bg-primary/90",
  secondary:
    "border border-secondary/40 bg-secondary/80 text-secondary-foreground hover:bg-secondary",
  outline:
    "border border-border/70 bg-card/60 text-foreground hover:border-primary/35 hover:bg-card/95",
  ghost: "text-muted-foreground hover:bg-muted/70 hover:text-foreground",
  link: "text-primary hover:text-foreground",
}

const sizeClasses: Record<ButtonSize, string> = {
  default: "h-11 px-4 py-2 text-[11px]",
  sm: "h-8 px-3 py-2 text-[10px]",
  lg: "h-12 px-5 py-3 text-[12px]",
}

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

export function buttonClasses({
  className,
  variant = "default",
  size = "default",
}: {
  className?: string
  variant?: ButtonVariant
  size?: ButtonSize
}) {
  return cn(
    "font-label inline-flex items-center justify-center gap-2 rounded-md uppercase tracking-[0.16em] shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60 disabled:pointer-events-none disabled:opacity-50",
    variantClasses[variant],
    sizeClasses[size],
    className,
  )
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={buttonClasses({ className, variant, size })}
      {...props}
    />
  ),
)

Button.displayName = "Button"
