import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check, Download, ShieldX, X } from "lucide-react";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { PageHeader } from "../components/ui/page-header";
import { Panel } from "../components/ui/panel";
import { ScoreBar } from "../components/ui/score-bar";
import { Skeleton } from "../components/ui/skeleton";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { downloadWithAuth } from "../lib/download";
import { formatPercent, formatScore } from "../lib/format";
import styles from "./match-detail.module.css";

const text = copy.matchDetail;

type Condition = {
  key: string;
  op: string;
  value: unknown;
  ok: boolean;
};

type Dimension = {
  key: string;
  label: string;
  score: number;
  weight: number;
};

type AbilityRow = {
  dim: string;
  baseline: number;
  actual: number | null;
  ratio: number;
};

type DetailBlock = {
  conditions: Condition[];
  dimensions: Dimension[];
  weights: Record<string, number>;
  threshold: number;
  required_skills: string[];
  hit_skills: string[];
  missing_skills: string[];
  hard_failed: boolean;
  fail_items: string[];
  base_score: number;
  ability_used: boolean;
  ability_detail: AbilityRow[];
};

type MatchDetail = {
  id: number;
  name: string;
  phone: string;
  email: string;
  education: string;
  major: string;
  skills: string[];
  years_experience: number;
  strengths: string;
  total_score: number;
  passing_threshold: number;
  passed: boolean;
  reason: string;
  job_profile_name: string;
  filename: string;
  attachment_url: string;
  resume_content: string;
  manually_fixed: boolean;
  detail: DetailBlock;
};

const OP_KEY: Record<string, keyof typeof text.op> = {
  ">=": "gte",
  ">": "gt",
  "<=": "lte",
  "<": "lt",
  contains: "contains",
  "==": "eq",
  "=": "eq",
};

const EMPTY_DETAIL: DetailBlock = {
  conditions: [],
  dimensions: [],
  weights: {},
  threshold: 0,
  required_skills: [],
  hit_skills: [],
  missing_skills: [],
  hard_failed: false,
  fail_items: [],
  base_score: 0,
  ability_used: false,
  ability_detail: [],
};

function expectedText(condition: Condition): string {
  const value = condition.value;
  if (Array.isArray(value)) return value.map(String).join("、");
  if (value === null || value === undefined) return copy.common.empty;
  if (condition.key === "工作年限" || condition.key === "experience" || condition.key === "年限") {
    return text.years(Number(value));
  }
  return String(value);
}

function actualText(condition: Condition, data: MatchDetail): string {
  if (condition.key === "学历" || condition.key === "education") {
    return data.education || copy.common.unknown;
  }
  if (condition.key === "工作年限" || condition.key === "experience" || condition.key === "年限") {
    return text.years(data.years_experience ?? 0);
  }
  if (condition.key === "技能" || condition.key === "skills") {
    if (!data.skills.length) return copy.common.empty;
    if (data.skills.length > 3) {
      return `${data.skills.slice(0, 3).join("、")} ${text.skillMore(data.skills.length)}`;
    }
    return data.skills.join("、");
  }
  return copy.common.empty;
}

export default function MatchDetailPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const job = searchParams.get("job");
  const [downloading, setDownloading] = useState(false);
  const [notice, setNotice] = useState("");
  const [resumeOpen, setResumeOpen] = useState(false);

  const query = useQuery({
    queryKey: ["match-detail", id],
    queryFn: () => request<MatchDetail>(`/matching/${id}`),
    enabled: Boolean(id),
  });

  const resumePreview = (query.data?.resume_content ?? "").slice(0, 120).trimEnd();

  useEffect(() => {
    track("page_view", { page: "match-detail" });
  }, []);

  function goBack() {
    navigate(job ? `/matching?job=${job}` : "/matching");
  }

  async function download() {
    if (!query.data?.attachment_url) return;
    try {
      setDownloading(true);
      setNotice("");
      await downloadWithAuth(query.data.attachment_url, query.data.filename);
    } catch {
      setNotice(text.downloadError);
    } finally {
      setDownloading(false);
    }
  }

  if (query.isError) {
    const error = query.error;
    if (error instanceof ApiError && (error.status === 404 || error.status === 403)) {
      const notFound = error.status === 404;
      return (
        <div className={styles.page}>
          <div className={styles.pageHead}>
            <PageHeader title={text.loadingTitle} actions={<Button variant="secondary" onClick={goBack}>{text.back}</Button>} />
          </div>
          <EmptyState
            icon={notFound ? undefined : <ShieldX size={20} strokeWidth={1.75} />}
            title={notFound ? text.notFoundTitle : text.forbiddenTitle}
            hint={notFound ? text.notFoundHint : text.forbiddenHint}
            action={
              <Button variant="secondary" onClick={goBack}>
                {text.back}
              </Button>
            }
          />
        </div>
      );
    }
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.loadingTitle} actions={<Button variant="secondary" onClick={goBack}>{text.back}</Button>} />
        </div>
        <ErrorState
          title={text.loadError}
          detail={error instanceof ApiError ? error.message : text.loadErrorHint}
          retryLabel={text.retry}
          onRetry={() => void query.refetch()}
        />
      </div>
    );
  }

  if (query.isPending) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.loadingTitle} actions={<Button variant="secondary" onClick={goBack}>{text.back}</Button>} />
        </div>
        <div className={styles.skeletonStack}>
          <Skeleton width="full" height="title" />
          <Skeleton width="full" />
          <Skeleton width="wide" />
        </div>
      </div>
    );
  }

  const data = query.data;
  const block = data.detail ?? EMPTY_DETAIL;
  const dimensions = block.dimensions ?? [];
  const conditions = block.conditions ?? [];
  const required = block.required_skills ?? [];
  const hits = block.hit_skills ?? [];
  const abilities = block.ability_detail ?? [];
  const hasFile = Boolean(data.attachment_url);

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader
          title={text.title(data.name || copy.common.unknown)}
          sub={text.sub(data.job_profile_name, data.filename)}
          actions={
            <>
              <Button variant="secondary" onClick={goBack}>
                <ArrowLeft size={16} strokeWidth={1.75} aria-hidden="true" />
                {text.back}
              </Button>
              {hasFile ? (
                <Button variant="primary" loading={downloading} onClick={() => void download()}>
                  <Download size={16} strokeWidth={1.75} aria-hidden="true" />
                  {text.download}
                </Button>
              ) : null}
            </>
          }
        />
      </div>

      {notice ? (
        <p className={styles.bannerError} role="status">
          {notice}
        </p>
      ) : null}

      {data.manually_fixed ? (
        <p className={styles.bannerWarn} role="status">
          {text.manualFixed}
        </p>
      ) : null}

      <div className={styles.columns}>
        <div className={styles.main}>
          <Panel title={text.conclusion} className={styles.glassPanel}>
            <div className={styles.verdict}>
              <div className={styles.verdictScore}>
                <ScoreBar
                  value={data.total_score}
                  threshold={data.passing_threshold}
                  label={text.scoreLabel}
                  unit={text.scoreUnit}
                />
                <div className={styles.verdictBadge}>
                  <Badge tone={data.passed ? "success" : "neutral"}>
                    {data.passed ? (
                      <Check size={12} strokeWidth={2} aria-hidden="true" />
                    ) : (
                      <X size={12} strokeWidth={2} aria-hidden="true" />
                    )}
                    {data.passed ? copy.matching.pass : copy.matching.fail}
                  </Badge>
                </div>
              </div>
              <div className={styles.verdictText}>
                <p className={styles.reason}>{data.reason || copy.common.empty}</p>
                {block.hard_failed ? <p className={styles.hardNote}>{text.hardNote}</p> : null}
              </div>
            </div>
          </Panel>

          <Panel title={text.hardTitle} meta={text.hardMeta} className={styles.glassTable} flush>
            {conditions.length === 0 ? (
              <p className={styles.note}>{text.noConditions}</p>
            ) : (
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">{text.conditionColumns.key}</th>
                    <th scope="col">{text.conditionColumns.actual}</th>
                    <th scope="col">{text.conditionColumns.expected}</th>
                    <th scope="col" className={styles.alignEnd}>
                      {text.conditionColumns.result}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {conditions.map((condition, index) => (
                    <tr key={`${condition.key}-${index}`}>
                      <td className={styles.strong}>{condition.key}</td>
                      <td>{actualText(condition, data)}</td>
                      <td>
                        {text.op[OP_KEY[condition.op] ?? "gte"] ?? condition.op} {expectedText(condition)}
                      </td>
                      <td className={styles.alignEnd}>
                        <span className={condition.ok ? styles.resultOk : styles.resultFail}>
                          {condition.ok ? (
                            <Check size={14} strokeWidth={2} aria-hidden="true" />
                          ) : (
                            <X size={14} strokeWidth={2} aria-hidden="true" />
                          )}
                          {condition.ok ? text.ok : text.fail}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>

          <Panel title={text.scoringTitle} meta={text.scoringMeta} className={styles.glassTable} flush>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">{text.scoringColumns.dimension}</th>
                  <th scope="col" className={styles.alignEnd}>
                    {text.scoringColumns.score}
                  </th>
                  <th scope="col" className={styles.alignEnd}>
                    {text.scoringColumns.weight}
                  </th>
                  <th scope="col" className={styles.alignEnd}>
                    {text.scoringColumns.contribution}
                  </th>
                </tr>
              </thead>
              <tbody>
                {dimensions
                  .filter((dimension) => dimension.weight > 0)
                  .map((dimension) => (
                    <tr key={dimension.key}>
                      <td className={styles.strong}>{dimension.label}</td>
                      <td className={styles.alignEnd}>{formatScore(dimension.score)}</td>
                      <td className={styles.alignEnd}>{formatPercent(dimension.weight, 1)}%</td>
                      <td className={styles.alignEnd}>
                        {formatScore(dimension.score * dimension.weight)}
                      </td>
                    </tr>
                  ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={3}>{text.base}</td>
                  <td className={styles.alignEnd}>{formatScore(block.base_score)}</td>
                </tr>
                <tr>
                  <td colSpan={3}>{text.final}</td>
                  <td className={styles.alignEnd}>{formatScore(data.total_score)}</td>
                </tr>
              </tfoot>
            </table>
            {dimensions.some((dimension) => dimension.weight === 0) ? (
              <p className={styles.tableNote}>
                {text.zeroWeight(
                  dimensions
                    .filter((dimension) => dimension.weight === 0)
                    .map((dimension) => dimension.label)
                    .join("、"),
                )}
              </p>
            ) : null}
          </Panel>
        </div>

        <aside className={styles.aside}>
          <Panel title={text.infoTitle} className={styles.glassPanel}>
            <dl className={styles.info}>
              <div>
                <dt>{text.info.education}</dt>
                <dd>{data.education || copy.common.unknown}</dd>
              </div>
              <div>
                <dt>{text.info.major}</dt>
                <dd>{data.major || copy.common.unknown}</dd>
              </div>
              <div>
                <dt>{text.info.years}</dt>
                <dd>{text.years(data.years_experience ?? 0)}</dd>
              </div>
              <div>
                <dt>{text.info.phone}</dt>
                <dd>{data.phone || copy.common.unknown}</dd>
              </div>
              <div>
                <dt>{text.info.email}</dt>
                <dd className={styles.break}>{data.email || copy.common.unknown}</dd>
              </div>
              <div>
                <dt>{text.info.file}</dt>
                <dd className={styles.break}>{data.filename || copy.common.unknown}</dd>
              </div>
              <div>
                <dt>{text.info.source}</dt>
                <dd>
                  <Badge tone={data.manually_fixed ? "warning" : "neutral"}>
                    {data.manually_fixed ? text.sourceManual : text.sourceParsed}
                  </Badge>
                </dd>
              </div>
            </dl>
          </Panel>

          <Panel title={text.abilityTitle} meta={text.abilityMeta} className={styles.glassPanel}>
            {!block.ability_used ? (
              <p className={styles.note}>{text.abilityNone}</p>
            ) : abilities.length === 0 ? (
              <p className={styles.note}>{text.abilityNoProfile}</p>
            ) : (
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">{text.abilityColumns.dim}</th>
                    <th scope="col" className={styles.alignEnd}>
                      {text.abilityColumns.baseline}
                    </th>
                    <th scope="col" className={styles.alignEnd}>
                      {text.abilityColumns.actual}
                    </th>
                    <th scope="col" className={styles.alignEnd}>
                      {text.abilityColumns.ratio}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {abilities.map((row) => (
                    <tr key={row.dim}>
                      <td className={styles.strong}>{row.dim}</td>
                      <td className={styles.alignEnd}>{formatScore(row.baseline)}</td>
                      <td className={styles.alignEnd}>{row.actual === null ? copy.common.empty : formatScore(row.actual)}</td>
                      <td className={styles.alignEnd}>{formatPercent(row.ratio, 1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>

          <Panel title={text.skillsTitle} meta={text.skillsMeta(hits.length, required.length)} className={styles.glassPanel}>
            {required.length === 0 ? (
              <p className={styles.note}>{text.noSkills}</p>
            ) : (
              <ul className={styles.chips}>
                {required.map((skill) => {
                  const hit = hits.includes(skill);
                  return (
                    <li
                      key={skill}
                      className={hit ? styles.chipHit : styles.chipMiss}
                      aria-label={`${skill}：${hit ? text.hitLabel : text.missingLabel}`}
                    >
                      {hit ? (
                        <Check size={12} strokeWidth={2} aria-hidden="true" />
                      ) : (
                        <X size={12} strokeWidth={2} aria-hidden="true" />
                      )}
                      {skill}
                    </li>
                  );
                })}
              </ul>
            )}
          </Panel>

          <Panel
            title={text.resumeTitle}
            meta={text.resumeMeta(data.resume_content.length)}
            className={styles.glassPanel}
            actions={
              data.resume_content ? (
                <Button variant="ghost" onClick={() => setResumeOpen((open) => !open)}>
                  {resumeOpen ? text.collapse : text.expand}
                </Button>
              ) : undefined
            }
          >
            {data.resume_content ? (
              <pre
                className={resumeOpen ? styles.resume : styles.resumePreview}
                tabIndex={0}
                aria-label={text.resumeTitle}
              >
                {resumeOpen ? data.resume_content : `${resumePreview}…`}
              </pre>
            ) : (
              <p className={styles.note}>{text.resumeEmpty}</p>
            )}
          </Panel>
        </aside>
      </div>
    </div>
  );
}
