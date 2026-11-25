import { useQuery } from "@tanstack/react-query";

import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { ErrorState } from "../../components/ui/error-state";
import { Modal } from "../../components/ui/modal";
import { Skeleton } from "../../components/ui/skeleton";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import { formatCount, formatScore } from "../../lib/format";
import type { JobProfile, TrialResult } from "./types";
import styles from "./trial-dialog.module.css";

const text = copy.jobProfiles;
const trial = text.trial;

type TrialDialogProps = {
  open: boolean;
  job: JobProfile | null;
  onClose: () => void;
};

export function TrialDialog({ open, job, onClose }: TrialDialogProps) {
  const result = useQuery({
    queryKey: ["job-trial", job?.id],
    queryFn: () => request<TrialResult>(`/job-profiles/${job?.id}/dry-run`, { method: "POST" }),
    enabled: open && job !== null,
  });

  const data = result.data;
  const maxBucket = Math.max(1, ...(data?.buckets.map((bucket) => bucket.count) ?? [0]));

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={trial.title}
      description={job ? trial.meta(job.name) : undefined}
      footer={
        <Button variant="secondary" onClick={onClose}>
          {trial.close}
        </Button>
      }
    >
      {result.isError ? (
        <ErrorState
          title={trial.error}
          detail={result.error instanceof ApiError ? result.error.message : undefined}
          retryLabel={text.retry}
          onRetry={() => void result.refetch()}
        />
      ) : result.isPending || !data ? (
        <div className={styles.skeleton}>
          <Skeleton width="full" />
          <Skeleton width="wide" />
          <Skeleton width="half" />
        </div>
      ) : data.scanned === 0 ? (
        <p className={styles.empty}>{trial.empty}</p>
      ) : (
        <div className={styles.body}>
          <dl className={styles.stats}>
            <div>
              <dt>{trial.scanned}</dt>
              <dd>{formatCount(data.scanned)}</dd>
            </div>
            <div>
              <dt>{trial.passed}</dt>
              <dd className={styles.pass}>{formatCount(data.passed)}</dd>
            </div>
            <div>
              <dt>{trial.failed}</dt>
              <dd className={styles.fail}>{formatCount(data.failed)}</dd>
            </div>
            <div>
              <dt>{trial.avg}</dt>
              <dd>{formatScore(data.avg_score)}</dd>
            </div>
            <div>
              <dt>{trial.threshold}</dt>
              <dd>{data.threshold}</dd>
            </div>
          </dl>

          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>{trial.buckets}</h3>
            <ul className={styles.buckets}>
              {data.buckets.map((bucket) => (
                <li className={styles.bucket} key={bucket.label}>
                  <span className={styles.bucketLabel}>{bucket.label}</span>
                  <span className={styles.track}>
                    <span
                      className={styles.fill}
                      style={{ width: `${(bucket.count / maxBucket) * 100}%` }}
                    />
                  </span>
                  <span className={styles.bucketCount}>{formatCount(bucket.count)}</span>
                </li>
              ))}
            </ul>
          </section>

          {data.top.length > 0 ? (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>{trial.top}</h3>
              <ul className={styles.top}>
                {data.top.map((item, index) => (
                  <li className={styles.topRow} key={`${item.name}-${index}`}>
                    <span className={styles.topName}>{item.name}</span>
                    <Badge tone={item.passed ? "success" : "neutral"}>
                      {item.passed ? trial.pass : trial.fail}
                    </Badge>
                    <span className={styles.topScore}>{formatScore(item.score)}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      )}
    </Modal>
  );
}
