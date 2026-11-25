import { useQuery } from "@tanstack/react-query";

import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Modal } from "../../components/ui/modal";
import { ErrorState } from "../../components/ui/error-state";
import { Skeleton } from "../../components/ui/skeleton";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import { formatDateTime, formatPercent, formatScore } from "../../lib/format";
import styles from "./profile-modal.module.css";
import { RadarChart, radarLabel } from "./radar-chart";
import { DIM_ORDER, sourceNote, type Profile } from "./types";

const text = copy.talent;

type ProfileModalProps = {
  open: boolean;
  profileId: number | null;
  onClose: () => void;
};

export function ProfileModal({ open, profileId, onClose }: ProfileModalProps) {
  const query = useQuery({
    queryKey: ["talent-profile", profileId],
    queryFn: () => request<Profile>(`/talent-profiles/${profileId}`),
    enabled: open && Boolean(profileId),
  });

  const data = query.data;
  const note = data ? sourceNote(data) : null;
  const generatedAt = note?.generated_at ? formatDateTime(note.generated_at) : "";
  const dims = data
    ? (data.dimensions.length ? data.dimensions : DIM_ORDER).filter(
        (dim) => typeof data.abilities[dim] === "number",
      )
    : [];
  const radarData = data
    ? dims.map((dim) => ({ label: dim, value: data.abilities[dim] ?? 0 }))
    : [];

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="md"
      title={data?.name || text.drawerTitle}
      description={data ? text.drawerMeta(data.title, generatedAt) : undefined}
      footer={
        <Button variant="secondary" onClick={onClose}>
          {copy.common.close}
        </Button>
      }
    >
      {query.isPending ? (
        <div className={styles.skeleton}>
          <Skeleton width="full" height="title" />
          <Skeleton width="full" />
          <Skeleton width="wide" />
        </div>
      ) : query.isError ? (
        query.error instanceof ApiError && query.error.status === 404 ? (
          <p className={styles.note}>{text.drawerEmpty}</p>
        ) : (
          <ErrorState
            title={text.drawerError}
            detail={query.error instanceof ApiError ? query.error.message : text.loadErrorHint}
            retryLabel={text.retry}
            onRetry={() => void query.refetch()}
          />
        )
      ) : data ? (
        <div className={styles.stack}>
          <div className={styles.intro}>
            <div className={styles.badgeRow}>
              <Badge tone={note?.ai ? "info" : "neutral"}>
                {note?.ai ? text.aiBadge : text.ruleBadge}
              </Badge>
              <span className={styles.muted}>{note?.ai ? text.aiNote : text.ruleNote}</span>
            </div>
            <p className={styles.summary}>{data.summary || copy.common.empty}</p>
          </div>

          <section className={styles.section}>
            <h3 className={styles.heading}>{text.radarTitle}</h3>
            <div className={styles.radarWrap}>
              <RadarChart data={radarData} ariaLabel={radarLabel(data.name, radarData)} />
            </div>
            <p className={styles.radarNote}>{text.radarNote}</p>
            <dl className={styles.dimList}>
              {radarData.map((item) => (
                <div className={styles.dimItem} key={item.label}>
                  <dt className={styles.dimLabel}>{item.label}</dt>
                  <dd className={styles.dimValue}>{formatScore(item.value)}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className={styles.section}>
            <h3 className={styles.heading}>{text.strengthsTitle}</h3>
            {data.strengths.length ? (
              <ul className={styles.list}>
                {data.strengths.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className={styles.muted}>{copy.common.empty}</p>
            )}
          </section>

          <section className={styles.section}>
            <h3 className={styles.heading}>{text.weaknessesTitle}</h3>
            {data.weaknesses.length ? (
              <ul className={styles.list}>
                {data.weaknesses.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className={styles.muted}>{copy.common.empty}</p>
            )}
          </section>

          <section className={styles.section}>
            <h3 className={styles.heading}>{text.recommendationTitle}</h3>
            <p className={styles.paragraph}>{data.recommendation || copy.common.empty}</p>
          </section>

          <section className={styles.section}>
            <h3 className={styles.heading}>{text.tagsTitle}</h3>
            {data.tags.length ? (
              <ul className={styles.tags}>
                {data.tags.map((tag) => (
                  <li className={styles.tag} key={tag}>
                    {tag}
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles.muted}>{copy.common.empty}</p>
            )}
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHead}>
              <h3 className={styles.heading}>{text.examTitle}</h3>
              {data.exam_evidence ? (
                <span className={styles.muted}>
                  {text.examMeta(data.exam_evidence.submissions, data.exam_evidence.weight)}
                </span>
              ) : null}
            </div>
            {data.exam_evidence?.rows?.length ? (
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">{text.examColumns.dim}</th>
                    <th scope="col" className={styles.alignEnd}>
                      {text.examColumns.resume}
                    </th>
                    <th scope="col" className={styles.alignEnd}>
                      {text.examColumns.exam}
                    </th>
                    <th scope="col" className={styles.alignEnd}>
                      {text.examColumns.merged}
                    </th>
                    <th scope="col" className={styles.alignEnd}>
                      {text.examColumns.questions}
                    </th>
                    <th scope="col" className={styles.alignEnd}>
                      {text.examColumns.weight}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.exam_evidence.rows.map((row) => (
                    <tr key={row.dim}>
                      <td>{row.dim}</td>
                      <td className={styles.alignEnd}>{formatScore(row.resume)}</td>
                      <td className={styles.alignEnd}>{formatScore(row.exam)}</td>
                      <td className={styles.alignEnd}>{formatScore(row.merged)}</td>
                      <td className={styles.alignEnd}>{row.questions}</td>
                      <td className={styles.alignEnd}>{formatPercent(row.weight, 1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className={styles.muted}>{text.examEmpty}</p>
            )}
          </section>
        </div>
      ) : null}
    </Modal>
  );
}
