import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Info,
  ShieldX,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";

import { DataTable, type Column } from "../components/ui/data-table";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { KpiStrip } from "../components/ui/kpi-strip";
import { PageHeader } from "../components/ui/page-header";
import { Panel } from "../components/ui/panel";
import { Skeleton } from "../components/ui/skeleton";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { cx } from "../lib/cx";
import { formatCount } from "../lib/format";
import { hasPermission } from "../lib/permission";
import styles from "./vacancy.module.css";

const text = copy.vacancy;

type Level = "high" | "medium" | "low" | "none";

type Alert = {
  job_profile_id: number;
  job_name: string;
  headcount: number;
  matched: number;
  passed: number;
  vacancy: number;
  pass_rate: number;
  alert: Level;
  threshold: number;
};

type NearMiss = {
  parsed_resume_id: number;
  name: string;
  total_score: number;
  threshold: number;
  gap: number;
  hard_failed: boolean;
  fail_items: string[];
  missing_skills: string[];
  reason: string;
};

type Qualified = {
  parsed_resume_id: number;
  name: string;
  abilities: Record<string, number | null>;
};

type Reserve = {
  job_profile_id: number;
  job_name: string;
  threshold: number;
  margin: number;
  near_miss: NearMiss[];
  qualified_pool: Qualified[];
};

type PageData<T> = { items: T[]; total: number; page: number; page_size: number };

type MatchRow = { id: number; parsed_resume_id: number };

const LEVEL_ICON: Record<Level, LucideIcon> = {
  high: AlertTriangle,
  medium: AlertCircle,
  low: Info,
  none: CheckCircle2,
};

export default function VacancyPage() {
  const { me } = useAuth();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const canView = hasPermission(me, "job:view");

  useEffect(() => {
    track("page_view", { page: "vacancy" });
  }, []);

  const alerts = useQuery({
    queryKey: ["vacancy-alerts"],
    queryFn: () => request<Alert[]>("/job-profiles/alerts"),
    enabled: canView,
  });

  useEffect(() => {
    if (!alerts.data?.length) return;
    if (selectedId !== null && alerts.data.some((item) => item.job_profile_id === selectedId)) return;
    setSelectedId(alerts.data[0].job_profile_id);
  }, [alerts.data, selectedId]);

  const selected = alerts.data?.find((item) => item.job_profile_id === selectedId) ?? null;

  const reserve = useQuery({
    queryKey: ["vacancy-reserve", selectedId],
    queryFn: () => request<Reserve>(`/job-profiles/${selectedId}/reserve`),
    enabled: canView && selectedId !== null,
  });

  const matchRows = useQuery({
    queryKey: ["vacancy-matches", selectedId],
    queryFn: () => request<PageData<MatchRow>>(`/matching/lists?job_profile_id=${selectedId}&page_size=200`),
    enabled: canView && selectedId !== null,
  });

  const matchIdByResume = useMemo(
    () => new Map((matchRows.data?.items ?? []).map((row) => [row.parsed_resume_id, row.id])),
    [matchRows.data],
  );

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

  if (alerts.isError) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.title} sub={text.sub} />
        </div>
        <ErrorState
          title={text.loadError}
          detail={alerts.error instanceof ApiError ? alerts.error.message : text.loadErrorHint}
          retryLabel={text.retry}
          onRetry={() => void alerts.refetch()}
        />
      </div>
    );
  }

  const rows = alerts.data ?? [];
  const shortage = rows.filter((item) => item.vacancy > 0).length;
  const totalVacancy = rows.reduce((sum, item) => sum + item.vacancy, 0);
  const highCount = rows.filter((item) => item.alert === "high").length;
  const allClear = rows.length > 0 && rows.every((item) => item.alert === "none");

  const nearColumns: Column<NearMiss>[] = [
    {
      key: "name",
      header: text.nearColumns.name,
      render: (row) => {
        const matchId = matchIdByResume.get(row.parsed_resume_id);
        return matchId ? (
          <Link className={styles.nameLink} to={`/matching/${matchId}?job=${selectedId}`}>
            {row.name}
          </Link>
        ) : (
          <span className={styles.strong}>{row.name}</span>
        );
      },
    },
    {
      key: "score",
      header: text.nearColumns.score,
      align: "right",
      width: "calc(var(--space-5xl) + var(--space-md))",
      render: (row) => <span className={styles.score}>{row.total_score.toFixed(1)}</span>,
    },
    {
      key: "gap",
      header: text.nearColumns.gap,
      width: "calc(var(--space-5xl) + var(--space-lg))",
      render: (row) => text.gapText(row.gap),
    },
    {
      key: "blocked",
      header: text.nearColumns.blocked,
      render: (row) => {
        const parts = [
          row.hard_failed ? text.blockedHard : null,
          ...row.fail_items,
          ...row.missing_skills,
        ].filter((item): item is string => Boolean(item));
        return parts.length ? parts.join("、") : text.scoreBelow;
      },
      hideOnTablet: true,
    },
  ];

  const qualifiedColumns: Column<Qualified>[] = [
    {
      key: "name",
      header: text.qualifiedColumns.name,
      width: "calc(var(--space-5xl) * 2)",
      render: (row) => <span className={styles.strong}>{row.name}</span>,
    },
    {
      key: "abilities",
      header: text.qualifiedColumns.abilities,
      render: (row) => (
        <span className={styles.abilities}>
          {Object.entries(row.abilities).map(([dim, value]) => (
            <span className={styles.ability} key={dim}>
              {dim} <strong>{value ?? copy.common.empty}</strong>
            </span>
          ))}
        </span>
      ),
    },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader title={text.title} sub={text.sub} />
      </div>

      <KpiStrip
        label={text.title}
        loading={alerts.isPending}
        items={[
          { label: text.kpi.jobs, value: rows.length, unit: text.kpi.unitJob },
          { label: text.kpi.shortage, value: shortage, unit: text.kpi.unitJob },
          { label: text.kpi.vacancy, value: totalVacancy, unit: text.kpi.unitPerson },
          { label: text.kpi.high, value: highCount, unit: text.kpi.unitJob, note: highCount > 0 ? text.kpi.highNote : undefined },
        ]}
      />

      {alerts.isPending ? (
        <div className={styles.loadingGrid}>
          <div className={styles.skeletonColumn}>
            <Skeleton className={styles.cardSkeleton} />
            <Skeleton className={styles.cardSkeleton} />
            <Skeleton className={styles.cardSkeleton} />
          </div>
          <Skeleton className={styles.panelSkeleton} />
        </div>
      ) : rows.length === 0 ? (
        <EmptyState title={text.noAlerts} hint={text.noAlertsHint} />
      ) : (
        <>
          {allClear ? (
            <p className={styles.allClear}>
              <CheckCircle2 size={16} strokeWidth={1.75} aria-hidden />
              {text.allClear}
            </p>
          ) : null}

          <div className={styles.layout}>
            <section className={styles.alerts} aria-label={text.alertsTitle}>
              <div className={styles.alertsHead}>
                <h2 className={styles.alertsTitle}>{text.alertsTitle}</h2>
                <p className={styles.alertsMeta}>{text.alertsMeta}</p>
              </div>
              <p className={styles.alertsNote}>{text.cardsNote}</p>
              {rows.map((item) => {
                const Icon = LEVEL_ICON[item.alert];
                const active = item.job_profile_id === selectedId;
                return (
                  <button
                    key={item.job_profile_id}
                    type="button"
                    className={cx(styles.card, active && styles.cardSelected)}
                    aria-pressed={active}
                    onClick={() => setSelectedId(item.job_profile_id)}
                  >
                    <span className={styles.cardTop}>
                      <span className={styles.cardName}>{item.job_name}</span>
                      <span className={styles.level} data-level={item.alert}>
                        <Icon size={12} strokeWidth={2} aria-hidden />
                        {text.level[item.alert]}
                      </span>
                    </span>
                    <span className={styles.stats}>
                      <span className={styles.stat}>
                        <span className={styles.statLabel}>{text.card.headcount}</span>
                        <span className={styles.statValue}>{formatCount(item.headcount)}</span>
                      </span>
                      <span className={styles.stat}>
                        <span className={styles.statLabel}>{text.card.passed}</span>
                        <span className={styles.statValue}>{formatCount(item.passed)}</span>
                      </span>
                      <span className={styles.stat}>
                        <span className={styles.statLabel}>{text.card.vacancy}</span>
                        <span className={cx(styles.statValue, item.vacancy > 0 && styles.statWarn)}>
                          {formatCount(item.vacancy)}
                        </span>
                      </span>
                    </span>
                    <span className={styles.cardFoot} title={text.passRateNote}>
                      {text.card.threshold} {item.threshold} · {text.card.passRate} {item.pass_rate.toFixed(1)}%
                    </span>
                  </button>
                );
              })}
            </section>

            <div className={styles.reserve}>
              {selected ? (
                <Panel
                  title={text.reserveTitle(selected.job_name)}
                  meta={reserve.data ? text.reserveMeta(reserve.data.margin) : undefined}
                  className={styles.glassTable}
                  flush
                >
                  {reserve.isError ? (
                    <div className={styles.stateWrap}>
                      <ErrorState
                        title={text.loadError}
                        detail={reserve.error instanceof ApiError ? reserve.error.message : text.loadErrorHint}
                        retryLabel={text.retry}
                        onRetry={() => void reserve.refetch()}
                      />
                    </div>
                  ) : reserve.isPending ? (
                    <div className={styles.reserveLoading}>
                      <Skeleton className={styles.reserveSkeleton} />
                      <Skeleton className={styles.reserveSkeleton} />
                      <Skeleton className={styles.reserveSkeleton} />
                    </div>
                  ) : reserve.data.near_miss.length === 0 && reserve.data.qualified_pool.length === 0 ? (
                    <div className={styles.reserveEmptyWrap}>
                      <EmptyState title={text.reserveEmpty} hint={text.reserveEmptyHint} />
                    </div>
                  ) : (
                    <>
                      <div className={styles.section}>
                        <h3 className={styles.sectionTitle}>{text.nearTitle}</h3>
                        <p className={styles.sectionHint}>{text.nearHint}</p>
                        <DataTable
                          caption={text.nearTitle}
                          columns={nearColumns}
                          rows={reserve.data.near_miss}
                          rowKey={(row) => row.parsed_resume_id}
                          empty={<p className={styles.tableEmpty}>{text.nearEmpty}</p>}
                        />
                      </div>
                      <div className={cx(styles.section, styles.sectionDivided)}>
                        <h3 className={styles.sectionTitle}>{text.qualifiedTitle}</h3>
                        <p className={styles.sectionHint}>{text.qualifiedHint}</p>
                        <DataTable
                          caption={text.qualifiedTitle}
                          columns={qualifiedColumns}
                          rows={reserve.data.qualified_pool}
                          rowKey={(row) => row.parsed_resume_id}
                          empty={<p className={styles.tableEmpty}>{text.qualifiedEmpty}</p>}
                        />
                      </div>
                    </>
                  )}
                </Panel>
              ) : null}

              <section className={styles.legend} aria-labelledby="vacancy-legend">
                <h3 className={styles.legendTitle} id="vacancy-legend">{text.legendTitle}</h3>
                <ul className={styles.legendList}>
                  {(["high", "medium", "low", "none"] as Level[]).map((level) => (
                    <li className={styles.legendRow} key={level}>
                      <span className={styles.level} data-level={level}>{text.level[level]}</span>
                      <span className={styles.legendRule}>{text.legend[level]}</span>
                    </li>
                  ))}
                </ul>
                <p className={styles.legendNote}>{text.legendNote}</p>
              </section>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
