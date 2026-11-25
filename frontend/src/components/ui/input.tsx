import type { ComponentPropsWithRef, ReactNode } from "react";

import styles from "./input.module.css";

type InputProps = ComponentPropsWithRef<"input"> & {
  sizeVariant?: "md" | "lg";
  invalid?: boolean;
  iconLeft?: ReactNode;
  suffix?: ReactNode;
};

export function Input({
  sizeVariant = "lg",
  invalid = false,
  iconLeft,
  suffix,
  className,
  ...rest
}: InputProps) {
  const classes = [styles.field, sizeVariant === "md" ? styles.md : styles.lg, className]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes} data-invalid={invalid || undefined}>
      {iconLeft ? <span className={styles.icon}>{iconLeft}</span> : null}
      <input {...rest} className={styles.input} aria-invalid={invalid || undefined} />
      {suffix ? <span className={styles.suffix}>{suffix}</span> : null}
    </div>
  );
}
