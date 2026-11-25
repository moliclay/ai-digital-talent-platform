import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Modal } from "../../components/ui/modal";
import { ErrorState } from "../../components/ui/error-state";
import { FormField } from "../../components/ui/form-field";
import { Input } from "../../components/ui/input";
import { Skeleton } from "../../components/ui/skeleton";
import { Textarea } from "../../components/ui/textarea";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import { downloadWithAuth } from "../../lib/download";
import { formatDateTime, formatDuration } from "../../lib/format";
import { ExamStateBadge } from "../../components/exam-state-badge";
import type { OnboardResult, ResumeDetail } from "./types";
import styles from "./detail-modal.module.css";

const text = copy.resumes;

type FormState = {
  name: string;
  phone: string;
  email: string;
  gender: string;
  age: string;
  education: string;
  major: string;
  years: string;
  skills: string;
  strengths: string;
};

function toForm(detail: ResumeDetail): FormState {
  return {
    name: detail.name ?? "",
    phone: detail.phone ?? "",
    email: detail.email ?? "",
    gender: detail.gender ?? "",
    age: detail.age === null || detail.age === undefined ? "" : String(detail.age),
    education: detail.education ?? "",
    major: detail.major ?? "",
    years: String(detail.years_experience ?? 0),
    skills: (detail.skills ?? []).join("，"),
    strengths: detail.strengths ?? "",
  };
}

type DetailModalProps = {
  open: boolean;
  resumeId: number | null;
  onClose: () => void;
  canEdit: boolean;
  onSaved: () => void;
  onOpenResume?: (resumeId: number) => void;
};

export function DetailModal({ open, resumeId, onClose, canEdit, onSaved, onOpenResume }: DetailModalProps) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; message: string } | null>(null);
  const [onboardOpen, setOnboardOpen] = useState(false);
  const [onboardBusy, setOnboardBusy] = useState(false);
  const [onboardError, setOnboardError] = useState("");
  const [onboardResult, setOnboardResult] = useState<OnboardResult | null>(null);
  const [copied, setCopied] = useState<"account" | "password" | null>(null);

  const detail = useQuery({
    queryKey: ["resume-detail", resumeId],
    queryFn: () => request<ResumeDetail>(`/resumes/${resumeId}`),
    enabled: open && resumeId !== null,
  });

  useEffect(() => {
    setEditing(false);
    setForm(null);
    setNotice(null);
    setOnboardOpen(false);
    setOnboardError("");
    setOnboardResult(null);
    setCopied(null);
  }, [resumeId, open]);

  useEffect(() => {
    if (detail.data && !editing) setForm(toForm(detail.data));
  }, [detail.data, editing]);

  const data = detail.data;

  function startEdit() {
    if (data?.identity?.is_current === false) return;
    if (data) setForm(toForm(data));
    setEditing(true);
    setNotice(null);
  }

  async function save() {
    if (!data || !form) return;
    const years = Number(form.years);
    if (!Number.isInteger(years) || years < 0) {
      setNotice({ tone: "error", message: text.yearsInvalid });
      return;
    }
    setSaving(true);
    setNotice(null);
    try {
      await request(`/resumes/${data.id}`, {
        method: "PATCH",
        body: {
          name: form.name.trim(),
          phone: form.phone.trim(),
          email: form.email.trim(),
          gender: form.gender.trim(),
          age: form.age.trim() ? Number(form.age) : undefined,
          education: form.education.trim(),
          major: form.major.trim(),
          years_experience: years,
          skills: form.skills,
          strengths: form.strengths.trim(),
        },
      });
      await detail.refetch();
      onSaved();
      setEditing(false);
      setNotice({ tone: "ok", message: text.saved });
    } catch (error) {
      setNotice({
        tone: "error",
        message: error instanceof ApiError ? error.message : text.saveError,
      });
    } finally {
      setSaving(false);
    }
  }

  async function download() {
    if (!data) return;
    try {
      await downloadWithAuth(data.attachment_url, data.filename);
    } catch {
      setNotice({ tone: "error", message: text.downloadError });
    }
  }

  async function confirmOnboard() {
    if (!data) return;
    setOnboardBusy(true);
    setOnboardError("");
    try {
      const result = await request<OnboardResult>(`/resumes/${data.id}/onboard`, {
        method: "POST",
        body: {},
      });
      setOnboardOpen(false);
      setOnboardResult(result);
      await detail.refetch();
      onSaved();
    } catch (error) {
      setOnboardError(error instanceof ApiError ? error.message : text.onboard.error);
    } finally {
      setOnboardBusy(false);
    }
  }

  async function copySecret(value: string, key: "account" | "password") {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(key);
    } catch {
      setCopied(null);
    }
  }

  const statusLabel = data ? text.status[data.status] ?? data.status : "";
  const identity = data?.identity;
  const examSummary = data?.exam_summary;
  const canOnboard = Boolean(canEdit && data && !data.employee_user_id && data.phone && identity?.is_current !== false);

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={data ? text.detailTitle(data.name) : text.title}
      description={
        data ? (
          <span className={styles.meta}>
            <span>{text.detailMeta(data.filename)}</span>
            <Badge tone={data.status === "completed" ? "success" : "neutral"}>{statusLabel}</Badge>
            {data.manually_fixed ? <Badge tone="info">{text.fixBadge}</Badge> : null}
          </span>
        ) : undefined
      }
      footer={
        editing ? (
          <>
            <Button variant="secondary" onClick={() => setEditing(false)} disabled={saving}>
              {copy.common.cancel}
            </Button>
            <Button variant="primary" onClick={() => void save()} loading={saving}>
              {text.save}
            </Button>
          </>
        ) : (
          <>
            <Button variant="secondary" onClick={onClose}>
              {copy.common.close}
            </Button>
            {canEdit && data && data.identity?.is_current !== false ? (
              <Button variant="primary" onClick={startEdit}>
                {text.edit}
              </Button>
            ) : null}
          </>
        )
      }
    >
      {detail.isError ? (
        <ErrorState
          title={text.detailError}
          detail={detail.error instanceof ApiError ? detail.error.message : undefined}
          retryLabel={text.retry}
          onRetry={() => void detail.refetch()}
        />
      ) : detail.isPending || !data ? (
        <div className={styles.skeleton}>
          <Skeleton width="short" height="title" />
          <Skeleton width="full" />
          <Skeleton width="wide" />
          <Skeleton width="half" />
        </div>
      ) : (
        <div className={styles.body}>
          <div className={styles.layout}>
            <div className={styles.main}>
          {notice ? (
            <p
              className={notice.tone === "ok" ? styles.noticeOk : styles.noticeError}
              role={notice.tone === "error" ? "alert" : "status"}
            >
              {notice.message}
            </p>
          ) : null}

          <div className={styles.actions}>
            <Button variant="ghost" onClick={() => void download()}>
              {text.download}
            </Button>
          </div>

          {editing && form ? (
            <>
              <p className={styles.hint}>{text.editHint}</p>
              <div className={styles.grid}>
                {(
                  [
                    ["name", text.fields.name],
                    ["phone", text.fields.phone],
                    ["email", text.fields.email],
                    ["gender", text.fields.gender],
                    ["age", text.fields.age],
                    ["education", text.fields.education],
                    ["major", text.fields.major],
                    ["years", text.fields.years],
                  ] as Array<[keyof FormState, string]>
                ).map(([key, label]) => (
                  <FormField key={key} id={`resume-${key}`} label={label}>
                    <Input
                      id={`resume-${key}`}
                      value={form[key]}
                      onChange={(event) => setForm({ ...form, [key]: event.target.value })}
                      disabled={saving}
                      inputMode={key === "age" || key === "years" ? "numeric" : undefined}
                    />
                  </FormField>
                ))}
              </div>
              <FormField id="resume-skills" label={text.fields.skills} hint={text.skillsHint}>
                <Input
                  id="resume-skills"
                  value={form.skills}
                  onChange={(event) => setForm({ ...form, skills: event.target.value })}
                  disabled={saving}
                />
              </FormField>
              <FormField id="resume-strengths" label={text.fields.strengths}>
                <Textarea
                  id="resume-strengths"
                  value={form.strengths}
                  rows={4}
                  onChange={(event) => setForm({ ...form, strengths: event.target.value })}
                  disabled={saving}
                />
              </FormField>
            </>
          ) : (
            <>
              <dl className={styles.defs}>
                <div>
                  <dt>{text.fields.education}</dt>
                  <dd>{data.education || copy.common.unknown}</dd>
                </div>
                <div>
                  <dt>{text.fields.major}</dt>
                  <dd>{data.major || copy.common.unknown}</dd>
                </div>
                <div>
                  <dt>{text.fields.years}</dt>
                  <dd>{text.years(data.years_experience ?? 0)}</dd>
                </div>
                <div>
                  <dt>{text.fields.phone}</dt>
                  <dd>{data.phone || copy.common.unknown}</dd>
                </div>
                <div>
                  <dt>{text.fields.email}</dt>
                  <dd>{data.email || copy.common.unknown}</dd>
                </div>
                <div>
                  <dt>{text.fields.gender}</dt>
                  <dd>{data.gender || copy.common.unknown}</dd>
                </div>
                <div>
                  <dt>{text.fields.age}</dt>
                  <dd>{data.age ?? copy.common.unknown}</dd>
                </div>
              </dl>

              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>{text.fields.skills}</h3>
                {data.skills.length === 0 ? (
                  <p className={styles.hint}>{copy.common.empty}</p>
                ) : (
                  <div className={styles.skills}>
                    {data.skills.map((skill) => (
                      <Badge tone="neutral" key={skill}>
                        {skill}
                      </Badge>
                    ))}
                  </div>
                )}
              </section>

              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>{text.fields.strengths}</h3>
                <p className={styles.text}>{data.strengths || copy.common.empty}</p>
              </section>

              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>{text.logsTitle}</h3>
                {data.logs.length === 0 ? (
                  <p className={styles.hint}>{text.noLogs}</p>
                ) : (
                  <ul className={styles.logs}>
                    {data.logs.map((log, index) => (
                      <li className={styles.log} key={`${log.created_at}-${index}`}>
                        <div className={styles.logHead}>
                          <span>{text.logStatus[log.status] ?? log.status}</span>
                          <span className={styles.logTime}>{formatDateTime(log.created_at)}</span>
                        </div>
                        <p className={styles.logMessage}>{log.message}</p>
                        <span className={styles.logMeta}>{text.logDuration(formatDuration(log.duration_ms))}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <details className={styles.original}>
                <summary className={styles.summary}>{text.originalTitle}</summary>
                <pre className={styles.pre}>{data.resume_content || text.originalEmpty}</pre>
              </details>
            </>
          )}
            </div>

            {!editing ? (
              <aside className={styles.side} aria-label="身份、测评与转正">
                <section className={styles.sideSection}>
                  <h3 className={styles.sideTitle}>{text.identity.title}</h3>
                  {identity?.key ? (
                    <p className={styles.sideMeta}>
                      {text.identity.key}：{identity.key}
                    </p>
                  ) : null}
                  {identity?.is_current === false && identity.superseded_by ? (
                    <div className={styles.oldBanner}>
                      <span>{text.identity.supersededBanner}</span>
                      <Button variant="ghost" onClick={() => onOpenResume?.(identity.superseded_by!)}>
                        {text.identity.viewCurrent}
                      </Button>
                    </div>
                  ) : null}
                  {identity?.siblings?.length ? (
                    <ul className={styles.versions}>
                      {identity.siblings.map((sibling) => (
                        <li className={styles.version} key={sibling.parsed_resume_id}>
                          <button
                            type="button"
                            className={styles.versionButton}
                            disabled={sibling.is_current || !onOpenResume}
                            onClick={() => onOpenResume?.(sibling.parsed_resume_id)}
                          >
                            <span className={styles.versionName}>{sibling.filename || copy.common.unknown}</span>
                            <span className={styles.versionMeta}>{formatDateTime(sibling.created_at)}</span>
                          </button>
                          <Badge tone={sibling.is_current ? "success" : "neutral"}>
                            {sibling.is_current ? text.identity.current : text.identity.old}
                          </Badge>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className={styles.hint}>{text.identity.onlyOne}</p>
                  )}
                </section>

                <section className={styles.sideSection}>
                  <h3 className={styles.sideTitle}>{text.exam.title}</h3>
                  {examSummary?.items.length ? (
                    <ul className={styles.examList}>
                      {examSummary.items.map((item) => (
                        <li className={styles.examItem} key={item.assignment_id ?? `${item.exam_id}-${item.submission_id ?? "none"}`}>
                          <div className={styles.examHead}>
                            <span className={styles.examName}>{item.exam_name}</span>
                            <ExamStateBadge
                              state={item.state}
                              label={item.state === "submitted" ? text.exam.submitted : text.exam.assigned}
                            />
                          </div>
                          <p className={styles.examMeta}>
                            {copy.common.audience[item.audience]}
                            {item.score === null
                              ? ""
                              : ` · ${text.exam.score(item.score, item.max_score ?? 0)} · ${item.passed ? text.exam.pass : text.exam.fail}`}
                          </p>
                          {item.deadline ? <p className={styles.examMeta}>{text.exam.deadline(formatDateTime(item.deadline))}</p> : null}
                          {item.submission_id ? (
                            <Link className={styles.sideLink} to={`/exams/result/${item.submission_id}`}>
                              {text.exam.result}
                            </Link>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <>
                      <p className={styles.hint}>{text.exam.empty}</p>
                      <p className={styles.examHint}>{text.exam.emptyHint}</p>
                    </>
                  )}
                  <Link className={styles.sideLink} to="/exams">
                    {text.exam.go}
                  </Link>
                </section>

                {canEdit ? (
                  <section className={styles.sideSection}>
                    <h3 className={styles.sideTitle}>{text.onboard.action}</h3>
                    {data.employee_user_id ? (
                      <Badge tone="success">{text.onboard.already}</Badge>
                    ) : canOnboard ? (
                      <Button variant="secondary" onClick={() => { setOnboardError(""); setOnboardOpen(true); }}>
                        {text.onboard.action}
                      </Button>
                    ) : (
                      <p className={styles.hint}>
                        {!data.phone
                          ? text.onboard.disabledNoPhone
                          : identity?.is_current === false
                            ? text.onboard.oldVersion
                            : text.onboard.disabledNoPhone}
                      </p>
                    )}
                  </section>
                ) : null}
              </aside>
            ) : null}
          </div>
        </div>
      )}

      <Modal
        open={onboardOpen}
        onClose={() => {
          if (!onboardBusy) setOnboardOpen(false);
        }}
        title={text.onboard.title}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOnboardOpen(false)} disabled={onboardBusy}>
              {copy.common.cancel}
            </Button>
            <Button variant="primary" onClick={() => void confirmOnboard()} loading={onboardBusy}>
              {text.onboard.confirm}
            </Button>
          </>
        }
      >
        <p className={styles.onboardBody}>{text.onboard.body}</p>
        {data?.phone ? <p className={styles.onboardPhone}>{text.fields.phone}：{data.phone}</p> : null}
        {onboardError ? <p className={styles.noticeError} role="alert">{onboardError}</p> : null}
      </Modal>

      <Modal
        open={onboardResult !== null}
        onClose={() => {
          setOnboardResult(null);
          setCopied(null);
        }}
        title={text.onboard.successTitle}
        size="sm"
        footer={
          <Button
            variant="primary"
            onClick={() => {
              setOnboardResult(null);
              setCopied(null);
            }}
          >
            {text.onboard.close}
          </Button>
        }
      >
        {onboardResult ? (
          <div className={styles.secret}>
            <label className={styles.secretLabel} htmlFor="onboard-account">{text.onboard.account}</label>
            <div className={styles.secretRow}>
              <Input id="onboard-account" readOnly value={onboardResult.username} />
              <Button variant="secondary" onClick={() => void copySecret(onboardResult.username, "account")}>
                {copied === "account" ? text.onboard.copied : text.onboard.copy}
              </Button>
            </div>
            <label className={styles.secretLabel} htmlFor="onboard-password">{text.onboard.password}</label>
            <div className={styles.secretRow}>
              <Input id="onboard-password" readOnly value={onboardResult.initial_password} />
              <Button variant="secondary" onClick={() => void copySecret(onboardResult.initial_password, "password")}>
                {copied === "password" ? text.onboard.copied : text.onboard.copy}
              </Button>
            </div>
            <p className={styles.onboardWarning}>{text.onboard.warning}</p>
          </div>
        ) : null}
      </Modal>
    </Modal>
  );
}
