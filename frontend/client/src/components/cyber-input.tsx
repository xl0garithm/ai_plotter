import * as React from "react";
import { cn } from "@/lib/utils";

interface CyberInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const CyberInput = React.forwardRef<HTMLInputElement, CyberInputProps>(
  ({ className, label, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-2 w-full">
        {label && (
          <label className="text-xs font-display tracking-widest text-primary/80 uppercase">
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            className={cn(
              "w-full bg-background border-b-2 border-primary/50 px-4 py-3 text-foreground font-mono",
              "focus:outline-none focus:border-primary focus:bg-primary/5 transition-all duration-300",
              "placeholder:text-muted-foreground/50",
              className
            )}
            {...props}
          />
          {/* Decorative corner accents */}
          <div className="absolute top-0 left-0 w-2 h-[2px] bg-primary" />
          <div className="absolute top-0 left-0 w-[2px] h-2 bg-primary" />
        </div>
      </div>
    );
  }
);
CyberInput.displayName = "CyberInput";
