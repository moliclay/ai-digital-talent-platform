import type { ComponentPropsWithRef } from "react";

import { cx } from "../../lib/cx";
import styles from "./textarea.module.css";

export function Textarea({ className, ...rest }: ComponentPropsWithRef<"textarea">) {
  return <textarea className={cx(styles.textarea, className)} {...rest} />;
}
