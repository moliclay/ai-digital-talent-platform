type BrandMarkProps = {
  size?: number;
  className?: string;
};

export function BrandMark({ size = 22, className }: BrandMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 22 22"
      fill="none"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <rect x="1.5" y="12.5" width="5" height="8" rx="1" fill="var(--text-tertiary)" />
      <rect x="8.5" y="8.5" width="5" height="12" rx="1" fill="var(--text-secondary)" />
      <rect x="15.5" y="1.5" width="5" height="19" rx="1" fill="var(--data-series-1)" />
    </svg>
  );
}
