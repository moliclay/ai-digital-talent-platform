import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { X } from "lucide-react";

import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { FileDrop } from "../../components/ui/file-drop";
import { Input } from "../../components/ui/input";
import { Modal } from "../../components/ui/modal";
import { Textarea } from "../../components/ui/textarea";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import type {
  QuestionDraft,
  QuestionImportConfirmResult,
  QuestionImportResult,
} from "../../lib/api-types";
import styles from "./question-import-dialog.module.css";

const text = copy.exams;

const TYPE_OPTIONS = [
  { value: "single_choice", label: "单选" },
  { value: "multi_choice", label: "多选" },
  { value: "fill_blank", label: "填空" },
  { value: "essay", label: "简答" },
];

const DIFFICULTY_OPTIONS = [
  { value: "easy", label: "简单" },
  { value: "medium", label: "中等" },
  { value: "hard", label: "困难" },
];

type QuestionImportDialogProps = {
  open: boolean;
  bankId: number | null;
  bankName: string;
  onClose: () => void;
  onConfirmed: () => void;
};

export function QuestionImportDialog({
  open,
  bankId,
  bankName,
  onClose,
  onConfirmed,
}: QuestionImportDialogProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [result, setResult] = useState<QuestionImportResult | null>(null);
  const [draft, setDraft] = useState<QuestionDraft[]>([]);
  const [confirmResult, setConfirmResult] = useState<QuestionImportConfirmResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setFiles([]);
    setResult(null);
    setDraft([]);
    setConfirmResult(null);
    setError("");
  }, [open, bankId]);

  const upload = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.append("file", files[0]);
      return request<QuestionImportResult>(`/question-banks/${bankId}/import`, {
        method: "POST",
        raw: form,
      });
    },
    onSuccess: (data) => {
      setResult(data);
      setDraft(data.draft);
      setError("");
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : text.importFailed),
  });

  const confirm = useMutation({
    mutationFn: () =>
      request<QuestionImportConfirmResult>(`/question-banks/${bankId}/import/confirm`, {
        method: "POST",
        body: { questions: draft },
      }),
    onSuccess: (data) => {
      setConfirmResult(data);
      onConfirmed();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : text.importFailed),
  });

  const update = (index: number, patch: Partial<QuestionDraft>) => {
    setDraft((current) =>
      current.map((item, position) => (position === index ? { ...item, ...patch } : item)),
    );
  };

  const footer = confirmResult ? (
    <Button variant="primary" onClick={onClose}>
      完成
    </Button>
  ) : result ? (
    <>
      <Button variant="secondary" onClick={onClose} disabled={confirm.isPending}>
        {copy.common.cancel}
      </Button>
      <Button
        variant="primary"
        loading={confirm.isPending}
        disabled={!draft.length}
        onClick={() => confirm.mutate()}
      >
        {text.importConfirm}
      </Button>
    </>
  ) : (
    <>
      <Button variant="secondary" onClick={onClose} disabled={upload.isPending}>
        {copy.common.cancel}
      </Button>
      <Button
        variant="primary"
        loading={upload.isPending}
        disabled={!files.length || !bankId}
        onClick={() => upload.mutate()}
      >
        {upload.isPending ? text.importParsing : text.importStart}
      </Button>
    </>
  );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={text.importTitle}
      description={`${bankName || "当前题库"} · ${text.importDesc}`}
      size="lg"
      footer={footer}
    >
      <div className={styles.stack}>
        {!result ? (
          <>
            <FileDrop
              files={files}
              onChange={(next) => {
                setFiles(next.slice(-1));
                setError("");
              }}
              accept=".txt,.md,.csv,.docx,.pdf,.xlsx"
              disabled={upload.isPending}
              hint="拖入一份题库文件，或点击选择"
              acceptLabel="txt / md / csv / docx / pdf / xlsx · ≤10MB"
              multiple={false}
            />
            <p className={styles.note}>
              上传后只生成草稿，不会直接入库；确认前可以逐题修改。
            </p>
          </>
        ) : (
          <>
            <div className={styles.summary}>
              <Badge tone={result.source === "ai" ? "info" : "neutral"}>
                {result.source === "ai" ? text.importSourceAI : text.importSourceRule}
              </Badge>
              <span>{text.importParsed(result.parsed_count)}</span>
              <span className={styles.filename}>{result.filename}</span>
            </div>

            {result.warnings.length ? (
              <div className={styles.warnings} role="status">
                <p className={styles.warnTitle}>{text.importWarnings}</p>
                <ul>
                  {result.warnings.map((warning, index) => (
                    <li key={`${warning}-${index}`}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {!draft.length ? <p className={styles.note}>{text.importEmpty}</p> : null}

            {draft.length ? (
              <div className={styles.draftHead}>
                <span className={styles.draftTitle}>{text.importDraft}</span>
                <span className={styles.draftCount}>{draft.length} 题</span>
              </div>
            ) : null}

            <ol className={styles.draftList}>
              {draft.map((item, index) => (
                <li key={index} className={item.needs_review ? styles.cardReview : styles.card}>
                  <div className={styles.cardHead}>
                    <span className={styles.index}>第 {index + 1} 题</span>
                    {item.needs_review ? <Badge tone="warning">{text.importNeedsReview}</Badge> : null}
                    <button
                      type="button"
                      className={styles.remove}
                      onClick={() => setDraft((current) => current.filter((_, position) => position !== index))}
                      aria-label={`移除第 ${index + 1} 题`}
                    >
                      <X size={15} strokeWidth={1.75} aria-hidden="true" />
                    </button>
                  </div>

                  <div className={styles.inline}>
                    <label className={styles.field}>
                      <span>{text.importType}</span>
                      <select
                        value={item.question_type}
                        onChange={(event) => update(index, { question_type: event.target.value })}
                        aria-label={`第 ${index + 1} 题题型`}
                      >
                        {TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className={styles.field}>
                      <span>{text.importScore}</span>
                      <Input
                        type="number"
                        min={1}
                        value={item.score}
                        onChange={(event) => update(index, { score: Number(event.target.value) || 0 })}
                        aria-label={`第 ${index + 1} 题分值`}
                      />
                    </label>
                    <label className={styles.field}>
                      <span>{text.importDifficulty}</span>
                      <select
                        value={item.difficulty}
                        onChange={(event) => update(index, { difficulty: event.target.value })}
                        aria-label={`第 ${index + 1} 题难度`}
                      >
                        {DIFFICULTY_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <label className={styles.field}>
                    <span>{text.importContent}</span>
                    <Textarea
                      rows={2}
                      value={item.content}
                      onChange={(event) => update(index, { content: event.target.value })}
                    />
                  </label>

                  {item.options.length ? (
                    <label className={styles.field}>
                      <span>{text.importOptions}</span>
                      <Textarea
                        rows={Math.min(6, Math.max(3, item.options.length))}
                        value={item.options.join("\n")}
                        onChange={(event) =>
                          update(index, {
                            options: event.target.value.split("\n").map((line) => line.trim()).filter(Boolean),
                          })
                        }
                      />
                    </label>
                  ) : null}

                  <div className={styles.inline}>
                    <label className={styles.field}>
                      <span>{text.importAnswer}</span>
                      <Input
                        value={item.answer}
                        onChange={(event) => update(index, { answer: event.target.value })}
                      />
                    </label>
                    <label className={styles.field}>
                      <span>{text.importKnowledge}</span>
                      <Input
                        value={item.knowledge_point}
                        onChange={(event) => update(index, { knowledge_point: event.target.value })}
                      />
                    </label>
                  </div>
                </li>
              ))}
            </ol>

            {confirmResult ? (
              <p className={styles.success} role="status">
                {text.importDone(confirmResult.created, confirmResult.skipped, confirmResult.failed_count)}
                {confirmResult.failed_count ? (
                  <span className={styles.failedList}>
                    {confirmResult.failed.map((item) => `第 ${item.index} 题：${item.reason}`).join("；")}
                  </span>
                ) : null}
              </p>
            ) : null}
          </>
        )}

        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}
      </div>
    </Modal>
  );
}
