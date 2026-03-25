import * as React from "react"

import { cn } from "@/lib/utils"

export function RadioGroup({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div role="radiogroup" className={cn("grid gap-2", className)} {...props} />
}

export const RadioGroupItem = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type = "radio", ...props }, ref) => (
  <input
    ref={ref}
    type={type}
    className={cn(
      "mt-0.5 h-4 w-4 shrink-0 accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
      className,
    )}
    {...props}
  />
))

RadioGroupItem.displayName = "RadioGroupItem"
