import * as React from "react";
import { cn } from "@/lib/utils";

interface CyberButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "accent" | "ghost";
}

export const CyberButton = React.forwardRef<HTMLButtonElement, CyberButtonProps>(
  ({ className, variant = "primary", children, ...props }, ref) => {
    
    const baseStyles = "relative px-6 py-3 font-display font-bold tracking-widest uppercase transition-all duration-300 overflow-hidden group disabled:opacity-50 disabled:cursor-not-allowed";
    
    const variants = {
      primary: "bg-background text-primary border-2 border-primary hover:bg-primary hover:text-primary-foreground box-glow",
      secondary: "bg-background text-secondary border-2 border-secondary hover:bg-secondary hover:text-secondary-foreground box-glow-pink",
      accent: "bg-background text-accent border-2 border-accent hover:bg-accent hover:text-accent-foreground",
      ghost: "text-muted-foreground hover:text-primary hover:bg-primary/10 border border-transparent hover:border-primary/50",
    };

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], className)}
        {...props}
      >
        <span className="relative z-10">{children}</span>
        {/* Glitch element on hover */}
        {variant !== "ghost" && (
          <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:-translate-y-full transition-transform duration-500 ease-in-out z-0" />
        )}
      </button>
    );
  }
);
CyberButton.displayName = "CyberButton";
