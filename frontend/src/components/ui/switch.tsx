import styles from "./switch.module.css";

type SwitchProps = {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  hint?: string;
  disabled?: boolean;
};

export function Switch({ checked, onChange, label, hint, disabled = false }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      className={styles.root}
      onClick={() => onChange(!checked)}
      disabled={disabled}
    >
      <span className={styles.text}>
        <span className={styles.label}>{label}</span>
        {hint ? <span className={styles.hint}>{hint}</span> : null}
      </span>
      <span className={checked ? `${styles.track} ${styles.on}` : styles.track} aria-hidden="true">
        <span className={styles.thumb} />
      </span>
    </button>
  );
}
