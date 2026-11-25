import type { ComponentPropsWithRef, MouseEventHandler, ReactNode } from "react";

import styles from "./button.module.css";

type ButtonProps = ComponentPropsWithRef<"button"> & {
  variant?: "primary" | "secondary" | "ghost" | "destructive";
  size?: "md" | "lg";
  loading?: boolean;
  fullWidth?: boolean;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
};

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  fullWidth = false,
  iconLeft,
  iconRight,
  children,
  className,
  disabled,
  onClick,
  type = "button",
  ...rest
}: ButtonProps) {
  const handleClick: MouseEventHandler<HTMLButtonElement> = (event) => {
    if (loading || disabled) {
      event.preventDefault();
      return;
    }
    onClick?.(event);
  };

  const classes = [styles.button, styles[variant], styles[size], fullWidth ? styles.full : "", className]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      {...rest}
      type={type}
      className={classes}
      disabled={disabled}
      aria-disabled={disabled || loading || undefined}
      aria-busy={loading || undefined}
      data-loading={loading || undefined}
      onClick={handleClick}
    >
      {loading ? <span className={styles.spinner} aria-hidden="true" /> : iconLeft}
      <span className={styles.label}>{children}</span>
      {iconRight}
    </button>
  );
}
