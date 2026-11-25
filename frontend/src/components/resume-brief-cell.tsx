import { copy } from "../content/copy";
import { formatCount } from "../lib/format";
import type { ResumeBrief } from "../lib/api-types";
import styles from "./resume-brief-cell.module.css";

type ResumeBriefCellProps = {
  brief: ResumeBrief;
  onOpen?: (resumeId: number) => void;
};

export function ResumeBriefCell({ brief, onOpen }: ResumeBriefCellProps) {
  const skills = Array.isArray(brief.skills_top) ? brief.skills_top : [];
  const totalSkills = Number.isFinite(brief.skills_count) ? brief.skills_count : skills.length;
  const more = Math.max(0, totalSkills - skills.length);
  const disabled = !brief.accessible;
  const name = brief.name || copy.common.unknown;

  return (
    <div className={styles.brief}>
      <button
        type="button"
        className={disabled ? `${styles.name} ${styles.disabled}` : styles.name}
        disabled={disabled}
        title={disabled ? "无权查看该简历" : name}
        onClick={() => {
          if (!disabled) onOpen?.(brief.parsed_resume_id);
        }}
      >
        {name}
      </button>
      <span className={styles.meta}>
        {brief.education || copy.common.empty} · {brief.major || copy.common.empty} ·{" "}
        {formatCount(brief.years_experience ?? 0)} 年
      </span>
      <span className={styles.skills}>
        {skills.length ? (
          <>
            {skills.map((skill) => (
              <span className={styles.skill} key={skill}>
                {skill}
              </span>
            ))}
            {more > 0 ? <span className={styles.more}>+{more}</span> : null}
          </>
        ) : (
          <span className={styles.muted}>{copy.common.empty}</span>
        )}
      </span>
      {brief.filename ? (
        <span className={styles.file} title={brief.filename}>
          {brief.filename}
        </span>
      ) : null}
    </div>
  );
}
