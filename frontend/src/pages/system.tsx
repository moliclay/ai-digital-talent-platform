import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldX } from "lucide-react";

import { Badge } from "../components/ui/badge";
import { DataTable, type Column } from "../components/ui/data-table";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { PageHeader } from "../components/ui/page-header";
import { Pagination } from "../components/ui/pagination";
import { Panel } from "../components/ui/panel";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { formatCount, formatDateTime } from "../lib/format";
import { hasPermission } from "../lib/permission";
import styles from "./system.module.css";

const text = copy.system;
const PAGE_SIZE = 20;

type User = {
  id: number;
  username: string;
  real_name: string;
  department_name: string;
  email: string;
  status: string;
};

type Role = {
  id: number;
  code: string;
  name: string;
  data_scope: string;
  description: string;
};

type Log = {
  id: number;
  username: string;
  module: string;
  action: string;
  method: string;
  path: string;
  status: string;
  duration_ms: number;
  created_at: string;
};

type PageData<T> = { items: T[]; total: number; page: number; page_size: number };

type TabKey = "users" | "roles" | "logs";

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "users", label: text.tabs.users },
  { key: "roles", label: text.tabs.roles },
  { key: "logs", label: text.tabs.logs },
];

export default function SystemPage() {
  const { me } = useAuth();
  const [tab, setTab] = useState<TabKey>("users");
  const [usersPage, setUsersPage] = useState(1);
  const [logsPage, setLogsPage] = useState(1);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const canView = hasPermission(me, "sys:view");

  useEffect(() => {
    track("page_view", { page: "system" });
  }, []);

  const users = useQuery({
    queryKey: ["sys-users", usersPage],
    queryFn: () => request<PageData<User>>(`/system/users?page=${usersPage}&page_size=${PAGE_SIZE}`),
    enabled: canView && tab === "users",
  });

  const roles = useQuery({
    queryKey: ["sys-roles"],
    queryFn: () => request<Role[]>("/system/roles"),
    enabled: canView && tab === "roles",
  });

  const logs = useQuery({
    queryKey: ["sys-logs", logsPage],
    queryFn: () =>
      request<PageData<Log>>(`/system/operation-logs?page=${logsPage}&page_size=${PAGE_SIZE}`),
    enabled: canView && tab === "logs",
  });

  if (!canView) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.title} sub={text.sub} />
        </div>
        <EmptyState
          icon={<ShieldX size={20} strokeWidth={1.75} />}
          title={text.noPermissionTitle}
          hint={text.noPermissionHint}
        />
      </div>
    );
  }

  function handleTabKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % TABS.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + TABS.length) % TABS.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = TABS.length - 1;
    else return;
    event.preventDefault();
    setTab(TABS[next].key);
    tabRefs.current[next]?.focus();
  }

  const userColumns: Column<User>[] = [
    { key: "username", header: text.userColumns.username, render: (row) => <span className={styles.strong}>{row.username}</span> },
    { key: "name", header: text.userColumns.name, render: (row) => row.real_name },
    { key: "department", header: text.userColumns.department, render: (row) => row.department_name, hideOnTablet: true },
    { key: "email", header: text.userColumns.email, render: (row) => <span className={styles.ellipsis} title={row.email}>{row.email}</span>, hideOnTablet: true },
    {
      key: "status",
      header: text.userColumns.status,
      width: "calc(var(--space-5xl) + var(--space-2xl))",
      render: (row) => (
        <Badge tone={row.status === "active" ? "success" : "neutral"}>
          {row.status === "active" ? text.statusActive : text.statusDisabled}
        </Badge>
      ),
    },
  ];

  const roleColumns: Column<Role>[] = [
    { key: "name", header: text.roleColumns.name, render: (row) => <span className={styles.strong}>{row.name}</span> },
    { key: "code", header: text.roleColumns.code, render: (row) => <code className={styles.code}>{row.code}</code> },
    {
      key: "scope",
      header: text.roleColumns.scope,
      render: (row) => text.scope[row.data_scope as keyof typeof text.scope] ?? row.data_scope,
    },
    { key: "description", header: text.roleColumns.description, render: (row) => row.description || copy.common.empty },
  ];

  const logColumns: Column<Log>[] = [
    {
      key: "time",
      header: text.logColumns.time,
      width: "calc(var(--space-5xl) * 3)",
      render: (row) => (
        <time dateTime={row.created_at.replace(" ", "T")}>{formatDateTime(row.created_at)}</time>
      ),
    },
    {
      key: "username",
      header: text.logColumns.username,
      width: "calc(var(--space-5xl) * 2)",
      render: (row) => row.username || <span className={styles.muted}>{text.unknownUser}</span>,
    },
    { key: "module", header: text.logColumns.module, width: "calc(var(--space-5xl) + var(--space-md))", render: (row) => row.module, hideOnTablet: true },
    {
      key: "action",
      header: text.logColumns.action,
      width: "calc(var(--space-5xl) + var(--space-md))",
      render: (row) => {
        if (row.path.endsWith("/auth/login")) return text.actions.login;
        return text.actions[row.action as keyof typeof text.actions] ?? row.action;
      },
    },
    { key: "method", header: text.logColumns.method, width: "calc(var(--space-5xl))", render: (row) => row.method, hideOnTablet: true },
    {
      key: "path",
      header: text.logColumns.path,
      render: (row) => <span className={styles.ellipsis} title={row.path}>{row.path}</span>,
      hideOnTablet: true,
    },
    {
      key: "status",
      header: text.logColumns.status,
      width: "calc(var(--space-5xl) + var(--space-2xs))",
      render: (row) => (
        <Badge tone={row.status === "success" ? "success" : "error"}>
          {row.status === "success" ? text.logSuccess : text.logFailed}
        </Badge>
      ),
    },
    {
      key: "duration",
      header: text.logColumns.duration,
      width: "calc(var(--space-5xl) + var(--space-md))",
      render: (row) => `${formatCount(row.duration_ms)} ${copy.common.ms}`,
      hideOnTablet: true,
    },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader title={text.title} sub={text.sub} />
      </div>

      <div className={styles.tabs} role="tablist" aria-label={text.title}>
        {TABS.map((item, index) => (
          <button
            key={item.key}
            ref={(element) => {
              tabRefs.current[index] = element;
            }}
            type="button"
            role="tab"
            id={`tab-${item.key}`}
            aria-selected={tab === item.key}
            aria-controls={`panel-${item.key}`}
            tabIndex={tab === item.key ? 0 : -1}
            className={tab === item.key ? `${styles.tab} ${styles.tabActive}` : styles.tab}
            onClick={() => setTab(item.key)}
            onKeyDown={(event) => handleTabKey(event, index)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "users" ? (
        <div role="tabpanel" id="panel-users" aria-labelledby="tab-users" tabIndex={0}>
          <Panel
            title={text.tabs.users}
            meta={users.data ? text.usersMeta(users.data.total) : undefined}
            className={styles.glassTable}
            flush
          >
            {users.isError ? (
              <div className={styles.stateWrap}>
                <ErrorState
                  title={text.loadError}
                  detail={users.error instanceof ApiError ? users.error.message : text.loadErrorHint}
                  retryLabel={text.retry}
                  onRetry={() => void users.refetch()}
                />
              </div>
            ) : (
              <>
                <DataTable
                  caption={text.tabs.users}
                  columns={userColumns}
                  rows={users.data?.items ?? []}
                  rowKey={(row) => row.id}
                  loading={users.isPending}
                  skeletonRows={5}
                  empty={<div className={styles.emptyWrap}><EmptyState title={text.usersEmpty} /></div>}
                />
                {(users.data?.total ?? 0) > PAGE_SIZE ? (
                  <div className={styles.pagination}>
                    <Pagination
                      page={usersPage}
                      pageSize={PAGE_SIZE}
                      total={users.data?.total ?? 0}
                      onChange={setUsersPage}
                      label={text.usersMeta(users.data?.total ?? 0)}
                    />
                  </div>
                ) : null}
              </>
            )}
          </Panel>
        </div>
      ) : null}

      {tab === "roles" ? (
        <div role="tabpanel" id="panel-roles" aria-labelledby="tab-roles" tabIndex={0}>
          <Panel
            title={text.tabs.roles}
            meta={roles.data ? text.rolesMeta(roles.data.length) : undefined}
            className={styles.glassTable}
            flush
          >
            {roles.isError ? (
              <div className={styles.stateWrap}>
                <ErrorState
                  title={text.loadError}
                  detail={roles.error instanceof ApiError ? roles.error.message : text.loadErrorHint}
                  retryLabel={text.retry}
                  onRetry={() => void roles.refetch()}
                />
              </div>
            ) : (
              <DataTable
                caption={text.tabs.roles}
                columns={roleColumns}
                rows={roles.data ?? []}
                rowKey={(row) => row.id}
                loading={roles.isPending}
                skeletonRows={4}
                empty={<div className={styles.emptyWrap}><EmptyState title={text.rolesEmpty} /></div>}
              />
            )}
          </Panel>
        </div>
      ) : null}

      {tab === "logs" ? (
        <div role="tabpanel" id="panel-logs" aria-labelledby="tab-logs" tabIndex={0}>
          <Panel
            title={text.tabs.logs}
            meta={logs.data ? text.logsMeta(logs.data.total) : undefined}
            className={styles.glassTable}
            flush
          >
            {logs.isError ? (
              <div className={styles.stateWrap}>
                <ErrorState
                  title={text.loadError}
                  detail={logs.error instanceof ApiError ? logs.error.message : text.loadErrorHint}
                  retryLabel={text.retry}
                  onRetry={() => void logs.refetch()}
                />
              </div>
            ) : (
              <>
                <DataTable
                  caption={text.tabs.logs}
                  columns={logColumns}
                  rows={logs.data?.items ?? []}
                  rowKey={(row) => row.id}
                  loading={logs.isPending}
                  skeletonRows={8}
                  empty={<div className={styles.emptyWrap}><EmptyState title={text.logsEmpty} /></div>}
                />
                <p className={styles.note}>{text.logsNote}</p>
                {(logs.data?.total ?? 0) > PAGE_SIZE ? (
                  <div className={styles.pagination}>
                    <Pagination
                      page={logsPage}
                      pageSize={PAGE_SIZE}
                      total={logs.data?.total ?? 0}
                      onChange={setLogsPage}
                      label={text.logsMeta(logs.data?.total ?? 0)}
                    />
                  </div>
                ) : null}
              </>
            )}
          </Panel>
        </div>
      ) : null}
    </div>
  );
}
