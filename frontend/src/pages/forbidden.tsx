import { useNavigate } from "react-router-dom";

import { PageHeader } from "../components/ui/page-header";
import { EmptyState } from "../components/ui/empty-state";
import { Button } from "../components/ui/button";
import { copy } from "../content/copy";
import { landingPath } from "../lib/api";
import { useAuth } from "../lib/auth";
import styles from "./forbidden.module.css";

export default function ForbiddenPage() {
  const { me } = useAuth();
  const navigate = useNavigate();

  if (!me) return null;
  const roleLabel = me.user.roles.map((role) => copy.roles[role] ?? role).join(" / ");
  const home = landingPath(me);

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader title={copy.forbidden.title} />
      </div>
      <section className={styles.panel}>
        <EmptyState
        title={copy.forbidden.emptyTitle}
        hint={copy.forbidden.account(me.user.real_name, me.user.username, roleLabel)}
        action={
          <Button
            variant="secondary"
            onClick={() => navigate(home === "/403" ? "/login" : home, { replace: true })}
          >
            {copy.forbidden.back}
          </Button>
        }
        />
      </section>
    </div>
  );
}
