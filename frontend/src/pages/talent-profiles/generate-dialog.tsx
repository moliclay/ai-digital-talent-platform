import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/button";
import { Modal } from "../../components/ui/modal";
import { Select } from "../../components/ui/select";
import { Switch } from "../../components/ui/switch";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import { track } from "../../lib/analytics";
import styles from "./generate-dialog.module.css";
import type { GenerateResult, PageData, ResumeOption } from "./types";

const text = copy.talent;

type GenerateDialogProps = {
  open: boolean;
  onClose: () => void;
  onGenerated: (result: GenerateResult) => void;
};

export function GenerateDialog({ open, onClose, onGenerated }: GenerateDialogProps) {
  const navigate = useNavigate();
  const [scope, setScope] = useState<"all" | "single">("all");
  const [resumeId, setResumeId] = useState("");
  const [useAi, setUseAi] = useState(true);
  const [useExam, setUseExam] = useState(true);
  const [notice, setNotice] = useState("");

  const resumes = useQuery({
    queryKey: ["talent-generate-resumes"],
    queryFn: () => request<PageData<ResumeOption>>("/resumes?page_size=200"),
    enabled: open,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (!open) return;
    setScope("all");
    setResumeId("");
    setUseAi(true);
    setUseExam(true);
    setNotice("");
  }, [open]);

  const generate = useMutation({
    mutationFn: () =>
      request<GenerateResult>("/talent-profiles/generate", {
        method: "POST",
        body: {
          use_ai: useAi,
          use_exam: useExam,
          ...(scope === "single" && resumeId ? { resume_id: Number(resumeId) } : {}),
        },
      }),
    onSuccess: (result) => {
      track("talent_generate_done", {
        page: "talent-profiles",
        total: result.total,
        ai_used: result.ai_used,
        exam_used: result.exam_used,
      });
      onGenerated(result);
    },
    onError: (error) => {
      track("talent_generate_failed", {
        page: "talent-profiles",
        status: error instanceof ApiError ? error.status : 0,
      });
      setNotice(
        error instanceof ApiError && error.status === 400
          ? text.noResumes
          : `${text.generateError}${error instanceof ApiError ? error.message : text.loadErrorHint}`,
      );
    },
  });

  const total = resumes.data?.total ?? 0;
  const options = resumes.data?.items ?? [];
  const selected = options.find((item) => String(item.id) === resumeId);
  const canSubmit =
    !generate.isPending &&
    total > 0 &&
    (scope === "all" || Boolean(selected));

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={text.generateTitle}
      description={text.generateDesc}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={generate.isPending}>
            {copy.common.cancel}
          </Button>
          <Button
            variant="primary"
            loading={generate.isPending}
            disabled={!canSubmit}
            onClick={() => {
              track("talent_generate_submit", {
                page: "talent-profiles",
                scope,
                use_ai: useAi,
                use_exam: useExam,
              });
              generate.mutate();
            }}
          >
            {generate.isPending ? text.running : text.run}
          </Button>
        </>
      }
    >
      {resumes.isError ? (
        <div className={styles.state}>
          <p className={styles.errorText}>{text.loadError}</p>
          <Button variant="secondary" onClick={() => void resumes.refetch()}>
            {text.retry}
          </Button>
        </div>
      ) : resumes.isPending ? (
        <div className={styles.state}>
          <p className={styles.muted}>{copy.common.loading}</p>
        </div>
      ) : total === 0 ? (
        <div className={styles.state}>
          <p className={styles.emptyTitle}>{text.noResumes}</p>
          <p className={styles.muted}>{text.noResumesHint}</p>
          <Button variant="secondary" onClick={() => navigate("/resumes")}>
            {text.goResumes}
          </Button>
        </div>
      ) : (
        <>
          <fieldset className={styles.scope}>
            <legend className={styles.legend}>{text.scopeLegend}</legend>
            <label className={styles.radio}>
              <input
                type="radio"
                name="scope"
                value="all"
                checked={scope === "all"}
                onChange={() => setScope("all")}
              />
              <span className={styles.radioText}>
                <span className={styles.radioLabel}>{text.scopeAllCount(total)}</span>
                {total > 50 ? <span className={styles.muted}>{text.largeScope(total)}</span> : null}
              </span>
            </label>
            <label className={styles.radio}>
              <input
                type="radio"
                name="scope"
                value="single"
                checked={scope === "single"}
                onChange={() => setScope("single")}
              />
              <span className={styles.radioText}>
                <span className={styles.radioLabel}>{text.scopeSingle}</span>
              </span>
            </label>
          </fieldset>

          {scope === "single" ? (
            <div className={styles.single}>
              <Select
                value={resumeId}
                options={options.map((item) => ({
                  value: String(item.id),
                  label: `${item.name} · ${item.education || "学历未识别"} · ${item.years_experience ?? 0} 年`,
                }))}
                onChange={setResumeId}
                ariaLabel={text.resumeSelect}
              />
              {total > options.length ? (
                <p className={styles.muted}>{text.singleLimit(options.length)}</p>
              ) : null}
            </div>
          ) : null}

          <div className={styles.toggles}>
            <Switch checked={useAi} onChange={setUseAi} label={text.toggleAi} hint={text.toggleAiHint} />
            <Switch
              checked={useExam}
              onChange={setUseExam}
              label={text.toggleExam}
              hint={text.toggleExamHint}
            />
          </div>

          {notice ? (
            <p className={styles.errorText} role="status">
              {notice}
            </p>
          ) : null}
        </>
      )}
    </Modal>
  );
}
