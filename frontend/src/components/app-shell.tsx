import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  ClipboardCheck,
  Circle,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Search,
  Settings,
  SlidersHorizontal,
  UserRound,
  Waypoints,
} from "lucide-react";

import { BrandMark } from "./brand-mark";
import { ResumeDetailHost } from "./resume-detail-host";
import { IconButton } from "./ui/icon-button";
import { ThemeToggle } from "./ui/theme-toggle";
import { copy } from "../content/copy";
import type { MenuItem } from "../lib/api";
import { useAuth } from "../lib/auth";
import { canUseChat } from "../lib/chat-api";
import { initials } from "../lib/format";
import { hasPermission } from "../lib/permission";
import styles from "./app-shell.module.css";
import "../styles/glass-app.css";

const ICONS: Record<string, typeof Circle> = {
  "/dashboard": LayoutDashboard,
  "/chat": MessageSquare,
  "/resumes": FileText,
  "/job-profiles": SlidersHorizontal,
  "/matching": Waypoints,
  "/vacancy": AlertTriangle,
  "/semantic": Search,
  "/talent-profiles": UserRound,
  "/exams": ClipboardCheck,
  "/system": Settings,
};

const ROUTE_PERMISSIONS: Array<{ prefix: string; code: string }> = [
  { prefix: "/dashboard", code: "dashboard:view" },
  { prefix: "/resumes", code: "resume:view" },
  { prefix: "/job-profiles", code: "job:view" },
  { prefix: "/matching", code: "match:view" },
  { prefix: "/talent-profiles", code: "talent:view" },
  { prefix: "/exams", code: "exam:view" },
  { prefix: "/vacancy", code: "job:view" },
  { prefix: "/semantic", code: "resume:view" },
  { prefix: "/training", code: "train:view" },
  { prefix: "/system", code: "sys:view" },
];

function requiredPermission(pathname: string) {
  return ROUTE_PERMISSIONS.find((route) => pathname === route.prefix || pathname.startsWith(`${route.prefix}/`))?.code;
}

const GROUPS: Array<{ label: string; paths: string[] }> = [
  { label: "工作", paths: ["/dashboard", "/chat", "/resumes", "/job-profiles", "/matching", "/vacancy", "/semantic"] },
  { label: "人才", paths: ["/talent-profiles", "/exams"] },
  { label: "系统", paths: ["/system"] },
];

/** 已经做完的路由；其余菜单先落到 /soon，避免链接跳到不存在的页面。 */
const IMPLEMENTED = new Set<string>([
  "/dashboard",
  "/chat",
  "/resumes",
  "/job-profiles",
  "/matching",
  "/talent-profiles",
  "/exams",
  "/system",
  "/vacancy",
  "/semantic",
  "/training",
]);

export function AppShell() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const navRef = useRef<HTMLElement | null>(null);
  const glassMode =
    pathname === "/dashboard" ||
    pathname === "/chat" ||
    pathname === "/resumes" ||
    pathname === "/talent-profiles" ||
    pathname === "/job-profiles" ||
    pathname === "/matching" ||
    pathname.startsWith("/matching/") ||
    pathname === "/exams" ||
    /^\/exams\/[^/]+\/take$/.test(pathname) ||
    pathname.startsWith("/exams/result/") ||
    pathname === "/system" ||
    pathname === "/vacancy" ||
    pathname === "/semantic" ||
    pathname === "/training" ||
    pathname === "/403" ||
    pathname === "/soon";
  const glassMatchDetail = pathname.startsWith("/matching/");

  useLayoutEffect(() => {
    document.body.classList.toggle("glass-route", glassMode);
    return () => document.body.classList.remove("glass-route");
  }, [glassMode]);

  useEffect(() => {
    const nav = navRef.current;
    if (!nav) return;
    if (nav.scrollWidth <= nav.clientWidth) return;
    const active = nav.querySelector<HTMLElement>('a[aria-current="page"]');
    if (!active) return;
    const target = active.offsetLeft - (nav.clientWidth - active.offsetWidth) / 2;
    nav.scrollTo({ left: Math.max(0, target), behavior: "smooth" });
  }, [pathname]);

  const groups = useMemo(() => {
    if (!me) return [];
    const menus = me.menus.filter((menu) => menu.allowed);
    const extra: MenuItem[] = [
      ...(canUseChat(me) ? [{ id: -3, name: "ChatAI 人才助手", path: "/chat", icon: "chat", permission_code: "", allowed: true }] : []),
      ...(hasPermission(me, "job:view")
        ? [{ id: -1, name: copy.vacancy.title, path: "/vacancy", icon: "alert", permission_code: "job:view", allowed: true }]
        : []),
      ...(hasPermission(me, "resume:view")
        ? [{ id: -2, name: copy.semantic.title, path: "/semantic", icon: "search", permission_code: "resume:view", allowed: true }]
        : []),
    ];
    const used = new Set<string>();
    const result = GROUPS.map((group) => {
      const items = group.paths
        .map((path) => menus.find((menu) => menu.path === path) ?? extra.find((menu) => menu.path === path))
        .filter((menu): menu is MenuItem => Boolean(menu));
      items.forEach((menu) => used.add(menu.path));
      return { label: group.label, items };
    }).filter((group) => group.items.length > 0);

    const rest = menus.filter((menu) => !used.has(menu.path));
    if (rest.length > 0) result.push({ label: "其他", items: rest });
    return result;
  }, [me]);

  if (!me) return null;

  const required = requiredPermission(pathname);
  if ((pathname === "/chat" && !canUseChat(me)) || (required && !hasPermission(me, required))) {
    return <Navigate to="/403" replace />;
  }

  const roleLabel = me.user.roles.map((role) => copy.roles[role] ?? role).join(" / ");

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div
      className={
        glassMode
          ? `${styles.shell} glass-app${pathname === "/talent-profiles" ? " glass-talent" : ""}${
              glassMatchDetail ? " glass-match-detail" : ""
            }`
          : styles.shell
      }
    >
      {glassMode ? (
        <div className="glass-app-backdrop" aria-hidden="true">
          <span className="glass-app-blob glass-app-blob-a" />
          <span className="glass-app-blob glass-app-blob-b" />
          <span className="glass-app-blob glass-app-blob-c" />
        </div>
      ) : null}

      <a className="skip-link" href="#main">
        {copy.shell.skipToMain}
      </a>

      <aside className={glassMode ? `${styles.aside} glass-side` : styles.aside}>
        <div className={styles.brand}>
          <BrandMark />
          <div className={styles.brandText}>
            <div className={styles.wordmark}>{copy.app.wordmark}</div>
            <div className={styles.dept}>{me.user.department_name || copy.shell.noDept}</div>
          </div>
        </div>

        <nav
          ref={navRef}
          className={glassMode ? `${styles.nav} glass-nav` : styles.nav}
          aria-label={copy.shell.navLabel}
        >
          {groups.map((group) => (
            <div className={styles.group} key={group.label}>
              <div className={styles.groupLabel}>{group.label}</div>
              {group.items.map((menu) => {
                const Icon = ICONS[menu.path] ?? Circle;
                const to = IMPLEMENTED.has(menu.path)
                  ? menu.path
                  : `/soon?menu=${encodeURIComponent(menu.name)}`;
                return (
                  <NavLink
                    key={menu.id}
                    to={to}
                    className={({ isActive }) =>
                      [
                        styles.link,
                        glassMode ? "glass-nav-link" : "",
                        isActive ? styles.active : "",
                      ]
                        .filter(Boolean)
                        .join(" ")
                    }
                    title={menu.name}
                    aria-label={menu.name}
                  >
                    <Icon className={styles.linkIcon} size={16} strokeWidth={1.75} aria-hidden="true" />
                    <span className={styles.linkText}>{menu.name}</span>
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        <div className={styles.footer}>
          <div className={styles.account}>
            <span className={styles.avatar} aria-hidden="true">
              {initials(me.user.real_name)}
            </span>
            <div className={styles.accountText}>
              <div className={styles.accountName}>{me.user.real_name}</div>
              <div className={styles.accountRole}>{roleLabel}</div>
            </div>
            <ThemeToggle />
            <IconButton label={copy.actions.logout} onClick={handleLogout}>
              <LogOut size={16} strokeWidth={1.75} aria-hidden="true" />
            </IconButton>
          </div>
        </div>
      </aside>

      <main className={glassMode ? `${styles.main} glass-main` : styles.main} id="main">
        <div className={glassMode ? `${styles.content} glass-content` : styles.content}>
          <Outlet />
        </div>
        <ResumeDetailHost />
      </main>
    </div>
  );
}
