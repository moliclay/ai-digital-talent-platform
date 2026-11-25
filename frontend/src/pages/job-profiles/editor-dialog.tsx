import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";

import { Button } from "../../components/ui/button";
import { FormField } from "../../components/ui/form-field";
import { IconButton } from "../../components/ui/icon-button";
import { Input } from "../../components/ui/input";
import { Modal } from "../../components/ui/modal";
import { Select } from "../../components/ui/select";
import { Skeleton } from "../../components/ui/skeleton";
import { Textarea } from "../../components/ui/textarea";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import type { Condition, JobProfile } from "./types";
import styles from "./editor-dialog.module.css";

const text = copy.jobProfiles;
const editor = text.editor;
const MAX_CONDITIONS = 20;

const DEFAULT_WEIGHTS: Record<string, string> = {
  education: "0.2",
  skills: "0.4",
  experience: "0.15",
  project: "0.15",
  other: "0.1",
};
const WEIGHT_ORDER = ["education", "skills", "experience", "project", "other", "ability"];
const FIELD_OPTIONS = Object.entries(text.fields).map(([value, label]) => ({ value, label }));
const OP_OPTIONS = Object.entries(text.ops).map(([value, label]) => ({ value, label }));
const FIELD_BY_LABEL: Record<string, string> = Object.fromEntries(
  Object.entries(text.fields).map(([key, label]) => [label, key]),
);

type EditorCondition = { key: string; op: string; value: string };

type FormState = {
  name: string;
  prompt: string;
  conditions: EditorCondition[];
  weights: Record<string, string>;
  threshold: string;
  abilities: Record<string, string>;
};

function blankForm(): FormState {
  return {
    name: "",
    prompt: "",
    conditions: [{ key: "education", op: ">=", value: "" }],
    weights: { ...DEFAULT_WEIGHTS },
    threshold: "70",
    abilities: Object.fromEntries(text.abilities.map((dim) => [dim, ""])),
  };
}

function toForm(job: JobProfile): FormState {
  const rawWeights = job.score_rules?.weights ?? {};
  const known = Object.entries(rawWeights)
    .filter(([key]) => text.weights[key] !== undefined)
    .sort(([a], [b]) => WEIGHT_ORDER.indexOf(a) - WEIGHT_ORDER.indexOf(b));
  const base = known.length > 0 ? known : Object.entries(DEFAULT_WEIGHTS);
  const sum = base.reduce((acc, [, value]) => acc + Number(value), 0) || 1;
  return {
    name: job.name,
    prompt: job.prompt ?? "",
    conditions: (job.conditions ?? []).map((condition: Condition) => ({
      key: FIELD_BY_LABEL[condition.key] ?? "education",
      op: condition.op,
      value: Array.isArray(condition.value)
        ? condition.value.join("，")
        : String(condition.value ?? ""),
    })),
    weights: Object.fromEntries(
      base.map(([key, value]) => [key, (Number(value) / sum).toFixed(2)]),
    ),
    threshold: String(job.passing_threshold ?? 70),
    abilities: Object.fromEntries(
      text.abilities.map((dim) => {
        const value = job.ability_requirements?.[dim];
        return [dim, value === undefined ? "" : String(value)];
      }),
    ),
  };
}

type EditorDialogProps = {
  open: boolean;
  jobId: number | null;
  onClose: () => void;
  onSaved: () => void;
};

export function EditorDialog({ open, jobId, onClose, onSaved }: EditorDialogProps) {
  const [form, setForm] = useState<FormState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const detail = useQuery({
    queryKey: ["job-profile-detail", jobId],
    queryFn: () => request<JobProfile>(`/job-profiles/${jobId}`),
    enabled: open && jobId !== null,
  });

  useEffect(() => {
    if (!open) {
      setForm(null);
      setError(null);
      return;
    }
    if (jobId === null) {
      setForm(blankForm());
      setError(null);
      return;
    }
    if (detail.data && detail.data.id === jobId) {
      setForm(toForm(detail.data));
      setError(null);
    }
  }, [open, jobId, detail.data]);

  const weightSum = form
    ? Object.values(form.weights).reduce((sum, value) => sum + (Number(value) || 0), 0)
    : 0;
  const weightOk = Math.abs(weightSum - 1) <= 0.01;

  function updateCondition(index: number, patch: Partial<EditorCondition>) {
    if (!form) return;
    const conditions = form.conditions.map((condition, position) =>
      position === index ? { ...condition, ...patch } : condition,
    );
    setForm({ ...form, conditions });
  }

  async function save() {
    if (!form || saving) return;
    if (!form.name.trim()) {
      setError(editor.validateName);
      return;
    }
    if (form.conditions.some((condition) => !String(condition.value).trim())) {
      setError(editor.validateCondition);
      return;
    }
    if (!weightOk) {
      setError(editor.validateWeights);
      return;
    }
    const threshold = Number(form.threshold);
    if (!Number.isInteger(threshold) || threshold < 0 || threshold > 100) {
      setError(editor.validateThreshold);
      return;
    }
    const abilities: Record<string, number> = {};
    for (const dim of text.abilities) {
      const raw = form.abilities[dim];
      if (raw === undefined || raw.trim() === "") continue;
      const value = Number(raw);
      if (!Number.isFinite(value) || value < 0 || value > 100) {
        setError(editor.validateAbility);
        return;
      }
      if (value > 0) abilities[dim] = value;
    }

    const conditions = form.conditions.map((condition) => {
      const raw = condition.value.trim();
      let value: unknown = raw;
      if (condition.key === "skills") {
        value = raw
          .split(/[,，]/)
          .map((item) => item.trim())
          .filter(Boolean);
      } else if (condition.key === "experience") {
        value = Number(raw);
      }
      return { key: text.fields[condition.key] ?? condition.key, op: condition.op, value };
    });

    const payload = {
      name: form.name.trim(),
      prompt: form.prompt.trim(),
      conditions,
      score_rules: {
        weights: Object.fromEntries(
          Object.entries(form.weights).map(([key, value]) => [key, Number(value) || 0]),
        ),
      },
      passing_threshold: threshold,
      ability_requirements: abilities,
    };

    setSaving(true);
    setError(null);
    try {
      if (jobId === null) {
        await request<JobProfile>("/job-profiles", { method: "POST", body: payload });
      } else {
        await request<JobProfile>(`/job-profiles/${jobId}`, { method: "PUT", body: payload });
      }
      onSaved();
      onClose();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `${editor.saveError}${cause.message}。${editor.draftHint}`
          : `${editor.saveError}${editor.draftHint}`,
      );
    } finally {
      setSaving(false);
    }
  }

  const loading = jobId !== null && detail.isPending;

  return (
    <Modal
      open={open}
      onClose={() => {
        if (!saving) onClose();
      }}
      title={jobId === null ? editor.titleNew : editor.titleEdit}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            {copy.common.cancel}
          </Button>
          <Button variant="primary" onClick={() => void save()} loading={saving} disabled={loading}>
            {saving ? editor.saving : editor.save}
          </Button>
        </>
      }
    >
      {loading || !form ? (
        <div className={styles.skeleton}>
          <Skeleton width="half" height="title" />
          <Skeleton width="full" />
          <Skeleton width="wide" />
        </div>
      ) : (
        <div className={styles.form}>
          {error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : null}

          <fieldset className={styles.section}>
            <legend className={styles.legend}>{editor.basic}</legend>
            <div className={styles.stack}>
              <FormField id="job-name" label={editor.name}>
                <Input
                  id="job-name"
                  value={form.name}
                  placeholder={editor.namePlaceholder}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  disabled={saving}
                />
              </FormField>
              <FormField id="job-prompt" label={editor.prompt}>
                <Textarea
                  id="job-prompt"
                  value={form.prompt}
                  rows={2}
                  placeholder={editor.promptPlaceholder}
                  onChange={(event) => setForm({ ...form, prompt: event.target.value })}
                  disabled={saving}
                />
              </FormField>
            </div>
          </fieldset>

          <div className={styles.columns}>
          <fieldset className={styles.section}>
            <legend className={styles.legend}>{editor.conditions}</legend>
            <p className={styles.hint}>{editor.conditionsHint}</p>
            <div className={styles.conditions}>
              {form.conditions.map((condition, index) => (
                <div className={styles.conditionRow} key={index}>
                  <Select
                    value={condition.key}
                    options={FIELD_OPTIONS}
                    onChange={(value) => updateCondition(index, { key: value })}
                    ariaLabel={editor.field}
                    disabled={saving}
                  />
                  <Select
                    value={condition.op}
                    options={OP_OPTIONS}
                    onChange={(value) => updateCondition(index, { op: value })}
                    ariaLabel={editor.op}
                    disabled={saving}
                  />
                  <IconButton
                    label={editor.removeCondition}
                    disabled={saving || form.conditions.length === 1}
                    onClick={() =>
                      setForm({
                        ...form,
                        conditions: form.conditions.filter((_, position) => position !== index),
                      })
                    }
                  >
                    <X size={16} strokeWidth={1.75} aria-hidden="true" />
                  </IconButton>
                  <div className={styles.conditionValue}>
                    <Input
                      value={condition.value}
                      placeholder={editor.valuePlaceholder[condition.key] ?? editor.value}
                      aria-label={editor.value}
                      onChange={(event) => updateCondition(index, { value: event.target.value })}
                      disabled={saving}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className={styles.conditionFoot}>
              <Button
                variant="secondary"
                disabled={saving || form.conditions.length >= MAX_CONDITIONS}
                onClick={() =>
                  setForm({
                    ...form,
                    conditions: [...form.conditions, { key: "skills", op: "contains", value: "" }],
                  })
                }
              >
                {editor.addCondition}
              </Button>
              <span className={styles.hint}>{editor.maxConditions(MAX_CONDITIONS)}</span>
            </div>
            {form.conditions.length === 0 ? <p className={styles.hint}>{editor.none}</p> : null}
          </fieldset>

          <div className={styles.column}>
          <fieldset className={styles.section}>
            <legend className={styles.legend}>{editor.weights}</legend>
            <p className={styles.hint}>{editor.weightsHint}</p>
            <div className={styles.grid}>
              {Object.entries(form.weights).map(([key, value]) => (
                <FormField key={key} id={`weight-${key}`} label={text.weights[key] ?? key}>
                  <Input
                    id={`weight-${key}`}
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={value}
                    onChange={(event) =>
                      setForm({ ...form, weights: { ...form.weights, [key]: event.target.value } })
                    }
                    disabled={saving}
                  />
                </FormField>
              ))}
            </div>
            <p className={weightOk ? styles.sumOk : styles.sumBad}>
              {weightOk ? editor.weightSum(weightSum.toFixed(2)) : editor.weightSumBad(weightSum.toFixed(2))}
            </p>
            <div className={styles.thresholdRow}>
              <FormField id="job-threshold" label={editor.threshold}>
                <Input
                  id="job-threshold"
                  type="number"
                  min="0"
                  max="100"
                  value={form.threshold}
                  onChange={(event) => setForm({ ...form, threshold: event.target.value })}
                  disabled={saving}
                />
              </FormField>
            </div>
          </fieldset>

          <fieldset className={styles.section}>
            <legend className={styles.legend}>{editor.abilities}</legend>
            <p className={styles.hint}>{editor.abilitiesHint}</p>
            <div className={styles.abilityGrid}>
              {text.abilities.map((dim) => (
                <FormField key={dim} id={`ability-${dim}`} label={dim}>
                  <Input
                    id={`ability-${dim}`}
                    type="number"
                    min="0"
                    max="100"
                    placeholder={editor.abilityPlaceholder}
                    value={form.abilities[dim] ?? ""}
                    onChange={(event) =>
                      setForm({ ...form, abilities: { ...form.abilities, [dim]: event.target.value } })
                    }
                    disabled={saving}
                  />
                </FormField>
              ))}
            </div>
          </fieldset>
          </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
