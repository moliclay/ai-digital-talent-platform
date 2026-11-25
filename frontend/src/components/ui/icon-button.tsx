import type { ComponentPropsWithRef, ReactNode } from "react";

import styles from "./icon-button.module.css";

type IconButtonProps = ComponentPropsWithRef<"button"> & {
  label: string;
  variant?: "ghost" | "secondary";
  size?: "md" | "lg";
  children: ReactNode;
};

export function IconButton({
  label,
  variant = "ghost",
  size = "md",
  children,
  className,
  type = "button",
  ...rest
}: IconButtonProps) {
  const classes = [styles.button, styles[variant], styles[size], className]
    .filter(Boolean)
    .join(" ");

  return (
    <button {...rest} type={type} className={classes} aria-label={label} title={label}>
      {children}
    </button>
  );
}
