import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface CyberButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
  children: ReactNode;
}

export function CyberButton({ className, variant = "primary", children, ...props }: CyberButtonProps) {
  return (
    <button
      className={cn(
        "cyber-button",
        variant === "secondary" && "cyber-button-secondary",
        className
      )}
      {...props}
    >
      <span className="relative z-10 uppercase tracking-widest">{children}</span>
      <div className="absolute inset-0 bg-white/5 opacity-0 hover:opacity-100 transition-opacity" />
    </button>
  );
}
