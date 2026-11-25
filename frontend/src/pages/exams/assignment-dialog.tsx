import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { ErrorState } from "../../components/ui/error-state";
import { FormField } from "../../components/ui/form-field";
import { Input } from "../../components/ui/input";
import { Modal } from "../../components/ui/modal";
import { Select } from "../../components/ui/select";
import { Skeleton } from "../../components/ui/skeleton";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import type { ExamAssignment } from "../../lib/api-types";
import type { Exam } from "./types";
import styles from "./assignment-dialog.module.css";

const text = copy.exams;

export type CreateAssignmentsResult = {
  created: ExamAssignment[];
  existed: ExamAssignment[];
  failed: { parsed_resume_id: number; reason: string }[];
  created_count: number;
  existed_count: number;
  failed_count: number;
};

type ResumeRow = {
  id: number;
  name: string;
  education: string;
  major: string;
  years_experience: number;
  filename: string;
};

type ResumeList = { items: ResumeRow[]; total: number };

type AssignmentDialogProps = {
  open: boolean;
  exams: Exam[];
  onClose: () => void;
  onCreated: (result: CreateAssignmentsResult) => void;
};

export function AssignmentDialog({ open, exams, onClose, onCreated }: AssignmentDialogProps) {
  const [examId, setExamId] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [search, setSearch] = useState("");
  const [deadline, setDeadline] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setExamId(exams[0] ? String(exams[0].id) : "");
    setSelected([]);
    setSearch("");
    setDeadline("");
    setNote("");
    setError("");
  }, [open, exams]);

  const resumes = useQuery({
    queryKey: ["resumes", "assignment-picker"],
    queryFn: () => request<ResumeList>("/resumes?page=1&page_size=200"),
    enabled: open,
  });

  const subscribe = useMutation({
    mutationFn: () =>
      request<CreateAssignmentsResult>("/exam-assignments", {
        method: "POST",
        body: {
          exam_id: Number(examId),
          parsed_resume_ids: selected,
          deadline: deadline ? deadline.replace("T", " ") + ":00" : null,
          note: note.trim(),
        },
      }),
    onSuccess: (result) => onCreated(result),
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : "绑定失败，请稍后再试。"),
  });

  const candidates = useMemo(() => {
    const rows = resumes.data?.items ?? [];
    const keyword = search.trim().toLowerCase();
    if (!keyword) return rows;
    return rows.filter((row) =>
      [row.name, row.education, row.major, row.filename]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword)),
    );
  }, [resumes.data, search]);

  const exam = exams.find((row) => String(row.id) === examId);
  const allSelected = candidates.length > 0 && candidates.every((row) => selected.includes(row.id));

  const toggle = (id: number) => {
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={text.bindTitle}
      description={text.bindDesc}
      size="lg"
      footer={
        <div className={styles.actions}>
          <Button variant="ghost" onClick={onClose} disabled={subscribe.isPending}>
            {copy.common.cancel}
          </Button>
          <Button
            variant="primary"
            onClick={() => subscribe.mutate()}
            disabled={!examId || !selected.length}
            loading={subscribe.isPending}
          >
            {text.bindConfirm}
          </Button>
        </div>
      }
    >
      <div className={styles.form}>
        {exams.length ? (
          <FormField id="assignment-exam" label={text.bindExam}>
            <Select
              id="assignment-exam"
              value={examId}
              options={exams.map((row) => ({
                value: String(row.id),
                label: `${row.name} · ${copy.common.audience[row.audience] ?? row.audience}`,
              }))}
              onChange={(value) => {
                setExamId(value);
                setSelected([]);
              }}
              ariaLabel={text.bindExam}
            />
          </FormField>
        ) : (
          <p className={styles.warn}>{text.bindNoExam}</p>
        )}

        {exam ? (
          <p className={styles.examHint}>
            <Badge tone={exam.audience === "employee" ? "info" : "neutral"}>
              {copy.common.audience[exam.audience] ?? exam.audience}
            </Badge>
            {exam.total_questions} 题 · 合格 {exam.pass_score} 分 · {exam.duration_minutes} 分钟
          </p>
        ) : null}

        <div className={styles.dateRow}>
          <FormField id="assignment-deadline" label={text.bindDeadline}>
            <Input
              id="assignment-deadline"
              type="datetime-local"
              value={deadline}
              onChange={(event) => setDeadline(event.target.value)}
            />
          </FormField>
          <FormField id="assignment-note" label={text.bindNote}>
            <Input
              id="assignment-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="例如：一面通过后补测"
            />
          </FormField>
        </div>

        <fieldset className={styles.candidates}>
          <div className={styles.candidateHead}>
            <legend>{text.bindCandidates}</legend>
            <span className={styles.selectedCount}>{text.bindSelected(selected.length)}</span>
          </div>
          <div className={styles.candidateTools}>
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={text.bindSearch}
              aria-label={text.bindSearch}
            />
            <Button
              variant="ghost"
              onClick={() =>
                setSelected(allSelected ? [] : candidates.map((row) => row.id))
              }
              disabled={!candidates.length}
            >
              {allSelected ? text.bindClear : text.bindAll}
            </Button>
          </div>

          {resumes.isPending ? (
            <div className={styles.listState}>
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} height="title" />
              ))}
            </div>
          ) : resumes.isError ? (
            <ErrorState
              title="候选人没取到"
              detail={
                resumes.error instanceof ApiError ? resumes.error.message : "请检查简历服务后重试。"
              }
              retryLabel={text.retry}
              onRetry={() => void resumes.refetch()}
            />
          ) : !candidates.length ? (
            <p className={styles.warn}>{text.bindEmptyCandidates}</p>
          ) : (
            <ul className={styles.candidateList}>
              {candidates.map((row) => {
                const checked = selected.includes(row.id);
                return (
                  <li key={row.id} className={checked ? styles.candidateOn : styles.candidate}>
                    <label className={styles.candidateLabel}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(row.id)}
                        className={styles.checkbox}
                      />
                      <span className={styles.avatar} aria-hidden="true">
                        {row.name.slice(0, 1)}
                      </span>
                      <span className={styles.candidateText}>
                        <span className={styles.candidateName}>{row.name}</span>
                        <span className={styles.candidateMeta}>
                          {[row.education, row.major, row.years_experience ? `${row.years_experience} 年` : ""]
                            .filter(Boolean)
                            .join(" · ") || copy.common.empty}
                        </span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </fieldset>

        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}
      </div>
    </Modal>
  );
}
