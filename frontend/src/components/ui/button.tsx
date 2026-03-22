import * as React from "react"

import { cn } from "@/lib/utils"

type ButtonVariant = "default" | "secondary" | "outline" | "ghost" | "link"
type ButtonSize = "default" | "sm" | "lg"

const variantClasses: Record<ButtonVariant, string> = {
  default: "bg-primary text-primary-foreground hover:opacity-90",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  outline: "border bg-card text-foreground hover:bg-muted/60",
  ghost: "text-foreground hover:bg-muted/60",
  link: "text-primary underline-offset-4 hover:underline",
}

const sizeClasses: Record<ButtonSize, string> = {
  default: "h-11 px-4 py-2",
  sm: "h-9 px-3 py-2 text-sm",
  lg: "h-12 px-5 py-3",
}

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  ),
)

Button.displayName = "Button"
