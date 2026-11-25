import { Moon, Sun } from "lucide-react";

import { copy } from "../../content/copy";
import { useTheme } from "../../lib/theme";
import { IconButton } from "./icon-button";
import styles from "./theme-toggle.module.css";

export function ThemeToggle() {
  const { isDark, toggle } = useTheme();
  const label = isDark ? copy.theme.toLight : copy.theme.toDark;

  return (
    <IconButton label={label} onClick={toggle} aria-pressed={isDark} className={styles.toggle}>
      {isDark ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
    </IconButton>
  );
}
