import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  Check,
  Eye,
  EyeOff,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { BrandMark } from "../components/brand-mark";
import { ThemeToggle } from "../components/ui/theme-toggle";
import { copy } from "../content/copy";
import { ApiError, landingPath } from "../lib/api";
import { track } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import "../styles/glass.css";
import styles from "./login.module.css";

const text = copy.login;

type FormError = { title: string; detail?: string };

function CountUp({ value }: { value: string }) {
  const target = Number(value);
  const [display, setDisplay] = useState(() => {
    if (!Number.isFinite(target)) return value;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    return reduce ? value : "0";
  });

  useEffect(() => {
    if (!Number.isFinite(target)) {
      setDisplay(value);
      return;
    }
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setDisplay(value);
      return;
    }
    const rawDuration = getComputedStyle(document.documentElement).getPropertyValue("--motion-count");
    const duration = Number.parseFloat(rawDuration) || 900;
    const decimals = value.includes(".") ? value.split(".")[1].length : 0;
    let frame = 0;
    const started = performance.now();
    setDisplay((0).toFixed(decimals));
    const tick = (now: number) => {
      const progress = Math.min(1, (now - started) / duration);
      const eased = 1 - (1 - progress) ** 4;
      setDisplay((target * eased).toFixed(decimals));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, value]);

  return <>{display}</>;
}

export default function LoginPage() {
  const { me, login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<FormError | null>(null);

  useEffect(() => {
    track("page_view", { page: "login" });
  }, []);

  const rawReturnTo = params.get("returnTo");
  const returnTo =
    rawReturnTo && rawReturnTo.startsWith("/") && !rawReturnTo.startsWith("//") ? rawReturnTo : "";

  if (me) return <Navigate to={returnTo || landingPath(me)} replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    if (!username.trim() || !password) {
      setError({ title: text.errors.empty });
      return;
    }
    if (username.trim().length > 64) {
      setError({ title: text.errors.usernameTooLong });
      return;
    }
    if (password.length > 128) {
      setError({ title: text.errors.passwordTooLong });
      return;
    }

    track("login_submit", { page: "login" });
    setBusy(true);
    setError(null);
    try {
      const current = await login(username.trim(), password);
      const target = returnTo || landingPath(current);
      track("login_success", { page: "login", role: current.user.roles[0] ?? "", redirect: target });
      navigate(target, { replace: true });
    } catch (cause) {
      const status = cause instanceof ApiError ? cause.status : 0;
      const code = cause instanceof ApiError ? cause.code : 0;
      track("login_failure", { page: "login", status, code });
      if (cause instanceof ApiError && cause.status === 401) {
        setError({ title: text.errors.badCredentials, detail: cause.message });
      } else if (cause instanceof ApiError && cause.status === 403) {
        setError({ title: text.errors.disabled, detail: cause.message });
      } else if (cause instanceof ApiError) {
        setError({ title: text.errors.generic, detail: cause.message });
      } else {
        setError({ title: text.errors.offline });
      }
    } finally {
      setBusy(false);
    }
  }

  function fillAccount(name: string) {
    setUsername(name);
    setPassword("123456");
    setError(null);
  }

  return (
    <div className={styles.shell}>
      <a className="skip-link" href="#login-main">
        {text.skipToForm}
      </a>

      <div className={styles.backdrop} aria-hidden="true">
        <span className={`${styles.orb} ${styles.orbOne}`} />
        <span className={`${styles.orb} ${styles.orbTwo}`} />
        <span className={`${styles.orb} ${styles.orbThree}`} />
        <span className={styles.noise} />
      </div>

      <header className={styles.header}>
        <div className={styles.brand}>
          <BrandMark size={26} />
          <div>
            <div className={styles.wordmark}>{copy.app.wordmark}</div>
            <div className={styles.brandSub}>{copy.app.tagline}</div>
          </div>
        </div>
        <div className={styles.headerActions}>
          <div className={`${styles.secureBadge} glass`}>
            <ShieldCheck size={15} strokeWidth={2} aria-hidden="true" />
            <span>{text.secureBadge}</span>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className={styles.main} id="login-main">
        <section className={styles.hero}>
          <p className={styles.tag}>
            <Sparkles size={14} strokeWidth={2} aria-hidden="true" />
            {text.eyebrow}
          </p>

          <h1 className={styles.title}>
            {text.titleLine1}
            <br />
            <span className={styles.accentText}>{text.titleLine2}</span>
          </h1>

          <p className={styles.lede}>
            {text.ledeLine1}
            <br />
            {text.ledeLine2}
          </p>

          <ul className={styles.features}>
            {text.features.map((feature) => (
              <li key={feature}>
                <span className={styles.checkIcon} aria-hidden="true">
                  <Check size={13} strokeWidth={2.5} />
                </span>
                {feature}
              </li>
            ))}
          </ul>

          <dl className={styles.stats}>
            {text.stats.map((stat) => (
              <div className={styles.stat} key={stat.label}>
                <dt className={styles.statLabel}>{stat.label}</dt>
                <dd className={styles.statValue}>
                  <CountUp value={stat.value} />
                </dd>
              </div>
            ))}
          </dl>

          <div className={styles.previewWrap} aria-hidden="true">
            <div className={`${styles.preview} glass lv2`}>
            <div className={styles.previewHead}>
              <span className={styles.previewTitle}>{text.preview.title}</span>
              <span className={styles.previewSample}>{text.preview.sample}</span>
            </div>
            <div className={styles.previewBody}>
              <div className={styles.previewWho}>
                <strong>{text.preview.name}</strong>
                <span>{text.preview.job}</span>
              </div>
              <div className={styles.previewScore}>
                {text.preview.score}
                <span>/ {text.preview.scoreMax}</span>
                <em className={styles.previewPass}>{text.preview.status}</em>
              </div>
            </div>
            <div className={styles.previewTrack}>
              <span className={styles.previewFill} />
              <span className={styles.previewTick} />
            </div>
              <div className={styles.previewFoot}>
                <span>{text.preview.thresholdLabel} {text.preview.threshold} · {text.preview.note}</span>
              </div>
            </div>
          </div>
        </section>

        <section className={styles.panelWrap} aria-labelledby="login-title">
          <div className={`${styles.panel} glass lv2`}>
            <div className={styles.panelHead}>
              <span className={styles.panelIcon} aria-hidden="true">
                <ShieldCheck size={18} strokeWidth={2} />
              </span>
              <div>
                <h2 id="login-title" className={styles.panelTitle}>
                  {text.panelTitle}
                </h2>
                <p className={styles.panelSub}>{text.panelSub}</p>
              </div>
            </div>

            <form className={styles.form} onSubmit={handleSubmit} noValidate>
              {error ? (
                <div className={styles.formError} role="alert">
                  <AlertCircle size={16} aria-hidden="true" />
                  <div>
                    <p className={styles.errorTitle}>{error.title}</p>
                    {error.detail ? <p className={styles.errorDetail}>{error.detail}</p> : null}
                  </div>
                </div>
              ) : null}

              <div className={styles.field}>
                <label className={styles.label} htmlFor="username">
                  {text.username}
                </label>
                <input
                  id="username"
                  className={styles.input}
                  name="username"
                  autoComplete="username"
                  spellCheck={false}
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder={text.usernamePlaceholder}
                  disabled={busy}
                />
              </div>

              <div className={styles.field}>
                <label className={styles.label} htmlFor="password">
                  {text.password}
                </label>
                <div className={styles.inputWrap}>
                  <input
                    id="password"
                    className={`${styles.input} ${styles.inputWithAction}`}
                    name="password"
                    type={visible ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    disabled={busy}
                  />
                  <button
                    type="button"
                    className={styles.reveal}
                    aria-label={visible ? text.hidePassword : text.showPassword}
                    aria-pressed={visible}
                    onClick={() => setVisible((value) => !value)}
                  >
                    {visible ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
                  </button>
                </div>
              </div>

              <button type="submit" className={styles.submit} disabled={busy} aria-busy={busy}>
                <span>{busy ? text.submitting : text.submit}</span>
                {busy ? null : <ArrowRight size={17} strokeWidth={2} aria-hidden="true" />}
              </button>
            </form>

            <div className={styles.demo}>
              <div className={styles.demoHead}>
                <span>{text.demoTitle}</span>
                <span className={styles.demoHint}>{text.demoHint}</span>
              </div>
              <div className={styles.demoGrid}>
                {text.demoAccounts.map((account) => (
                  <button
                    key={account.username}
                    type="button"
                    className={styles.account}
                    onClick={() => fillAccount(account.username)}
                    aria-label={`填入演示账号 ${account.username}`}
                  >
                    <span className={styles.accountText}>
                      <span className={styles.accountName}>{account.username}</span>
                      <span className={styles.accountRole}>{account.role}</span>
                    </span>
                    <ArrowRight size={14} strokeWidth={2} aria-hidden="true" />
                  </button>
                ))}
              </div>
              <p className={styles.demoNote}>{text.loginHint}</p>
            </div>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>{text.footer}</footer>
    </div>
  );
}
