import { useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { DetailModal } from "../pages/resumes/detail-modal";
import { hasPermission } from "../lib/permission";
import { useAuth } from "../lib/auth";

/**
 * 全局简历详情弹窗：任意页面用 ?resume=<parsed_resume_id> 打开。
 * 关闭时只移除 resume 参数，保留当前页面的筛选与滚动位置。
 */
export function ResumeDetailHost() {
  const { me } = useAuth();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const raw = params.get("resume");
  const resumeId = raw && /^\d+$/.test(raw) ? Number(raw) : null;

  function close() {
    const next = new URLSearchParams(params);
    next.delete("resume");
    setParams(next, { replace: true });
  }

  if (!me || resumeId === null) return null;

  return (
    <DetailModal
      open
      resumeId={resumeId}
      onClose={close}
      canEdit={hasPermission(me, "resume:edit")}
      onSaved={() => {
        void queryClient.invalidateQueries({ queryKey: ["resumes"] });
        void queryClient.invalidateQueries({ queryKey: ["resume-detail"] });
      }}
      onOpenResume={(id) => {
        const next = new URLSearchParams(params);
        next.set("resume", String(id));
        setParams(next);
      }}
    />
  );
}
