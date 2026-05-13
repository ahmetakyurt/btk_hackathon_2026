import Link from "next/link";

interface LogoProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  showText?: boolean;
  linkToHome?: boolean;
}

export function Logo({
  className = "",
  size = "md",
  showText = true,
  linkToHome = true,
}: LogoProps) {
  const sizeClasses = {
    sm: "h-6 w-6",
    md: "h-8 w-8",
    lg: "h-10 w-10",
  };

  const textSizeClasses = {
    sm: "text-base",
    md: "text-xl",
    lg: "text-2xl",
  };

  const content = (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {/* Logo Icon - Stylized "O" with price graph element */}
      <div className={`relative ${sizeClasses[size]}`}>
        <svg
          viewBox="0 0 40 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full"
        >
          {/* Outer circle */}
          <circle
            cx="20"
            cy="20"
            r="18"
            stroke="currentColor"
            strokeWidth="2.5"
            className="text-foreground"
          />
          {/* Inner rising graph line */}
          <path
            d="M10 26L16 20L22 24L30 12"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-accent"
          />
          {/* Dot at the end */}
          <circle cx="30" cy="12" r="2.5" fill="currentColor" className="text-accent" />
        </svg>
      </div>
      {showText && (
        <div className="flex flex-col leading-none">
          <span
            className={`font-semibold tracking-tight text-foreground ${textSizeClasses[size]}`}
          >
            OptiPrice
          </span>
          <span className="text-[10px] font-medium tracking-widest uppercase text-muted-foreground">
            AI
          </span>
        </div>
      )}
    </div>
  );

  if (linkToHome) {
    return (
      <Link href="/" className="hover:opacity-80 transition-opacity">
        {content}
      </Link>
    );
  }

  return content;
}
