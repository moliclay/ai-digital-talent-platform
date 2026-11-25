import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Button } from "../../components/ui/button";
import { FileDrop } from "../../components/ui/file-drop";
import { FormField } from "../../components/ui/form-field";
import { Input } from "../../components/ui/input";
import { Modal } from "../../components/ui/modal";
import { Select } from "../../components/ui/select";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import type { JobOption, PageData } from "./types";
import styles from "./upload-dialog.module.css";

const text = copy.resumes;
const MAX_FILES = 20;
const MAX_SIZE = 10 * 1024 * 1024;
const ACCEPT = ".pdf,.docx,.txt";
const EXTENSIONS = ACCEPT.split(",");

type UploadResult = {
  accepted: number;
  rejected: number;
};

type Failure = { name: string; reason: string };

type UploadDialogProps = {
  open: boolean;
  onClose: () => void;
  onUploaded: (accepted: number) => void;
  canViewJobs: boolean;
};

export function UploadDialog({ open, onClose, onUploaded, canViewJobs }: UploadDialogProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [jobId, setJobId] = useState("");
  const [project, setProject] = useState("");
  const [issues, setIssues] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [result, setResult] = useState<{ accepted: number; failures: Failure[] } | null>(null);

  const jobs = useQuery({
    queryKey: ["job-options"],
    queryFn: () => request<PageData<JobOption>>("/job-profiles?page_size=100"),
    enabled: open && canViewJobs,
    staleTime: 60_000,
  });

  const jobOptions = useMemo(
    () => [
      { value: "", label: text.jobNone },
      ...(jobs.data?.items ?? [])
        .filter((job) => job.status === "active")
        .map((job) => ({ value: String(job.id), label: job.name })),
    ],
    [jobs.data],
  );

  function applyFiles(next: File[]) {
    const messages: string[] = [];
    const valid: File[] = [];
    for (const file of next) {
      const suffix = `.${(file.name.split(".").pop() ?? "").toLowerCase()}`;
      if (!EXTENSIONS.includes(suffix)) {
        messages.push(text.fileUnsupported(file.name));
        continue;
      }
      if (file.size > MAX_SIZE) {
        messages.push(text.fileTooLarge(file.name));
        continue;
      }
      valid.push(file);
    }
    let capped = valid;
    if (valid.length > MAX_FILES) {
      messages.push(text.tooMany(valid.length - MAX_FILES));
      capped = valid.slice(0, MAX_FILES);
    }
    setFiles(capped);
    setIssues(messages);
    setResult(null);
  }

  async function startUpload() {
    if (files.length === 0 || busy) return;
    setBusy(true);
    setResult(null);
    setProgress({ done: 0, total: files.length });

    let accepted = 0;
    const failures: Failure[] = [];

    for (let index = 0; index < files.length; index += 1) {
      const file = files[index];
      const form = new FormData();
      form.append("files", file);
      if (jobId) form.append("job_profile_id", jobId);
      if (project.trim()) form.append("project_name", project.trim());
      try {
        const response = await request<UploadResult>("/resumes/upload", {
          method: "POST",
          raw: form,
        });
        if (response.accepted > 0) accepted += response.accepted;
        else failures.push({ name: file.name, reason: text.uploadRejected });
      } catch (error) {
        failures.push({
          name: file.name,
          reason: error instanceof ApiError ? error.message : text.uploadError,
        });
      }
      setProgress({ done: index + 1, total: files.length });
    }

    setBusy(false);
    setResult({ accepted, failures });
    if (accepted > 0) {
      onUploaded(accepted);
      setFiles([]);
      setIssues([]);
    }
  }

  const uploadingLabel = text.uploading(Math.min(progress.done + 1, progress.total), progress.total);

  return (
    <Modal
      open={open}
      onClose={() => {
        if (!busy) onClose();
      }}
      title={text.uploadTitle}
      description={text.uploadHint}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            {result ? copy.common.close : copy.common.cancel}
          </Button>
          <Button
            variant="primary"
            onClick={() => void startUpload()}
            loading={busy}
            disabled={files.length === 0 || result !== null}
          >
            {busy ? uploadingLabel : text.start}
          </Button>
        </>
      }
    >
      <div className={styles.form}>
        <FileDrop files={files} onChange={applyFiles} accept={ACCEPT} disabled={busy || result !== null} />

        {issues.length > 0 ? (
          <ul className={styles.issues}>
            {issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        ) : null}

        <div className={styles.row}>
          <FormField id="upload-job" label={text.jobLabel}>
            <Select
              id="upload-job"
              value={jobId}
              options={jobOptions}
              onChange={setJobId}
              disabled={!canViewJobs || busy || jobs.isPending}
              ariaLabel={text.jobLabel}
            />
          </FormField>
          <FormField id="upload-project" label={text.projectLabel}>
            <Input
              id="upload-project"
              value={project}
              placeholder={text.projectPlaceholder}
              onChange={(event) => setProject(event.target.value)}
              disabled={busy}
            />
          </FormField>
        </div>

        {result ? (
          <div className={styles.result} role="status">
            <p>
              {result.accepted > 0
                ? result.failures.length > 0
                  ? text.uploadPartial(result.accepted, result.failures.length)
                  : text.uploadDone(result.accepted)
                : text.uploadPartial(0, result.failures.length)}
            </p>
            {result.failures.length > 0 ? (
              <ul className={styles.failures}>
                {result.failures.map((failure) => (
                  <li key={failure.name}>{text.uploadFail(failure.name, failure.reason)}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
