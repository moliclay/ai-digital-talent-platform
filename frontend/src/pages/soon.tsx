import { useNavigate, useSearchParams } from "react-router-dom";

import { PageHeader } from "../components/ui/page-header";
import { EmptyState } from "../components/ui/empty-state";
import { Button } from "../components/ui/button";
import { copy } from "../content/copy";
import { useAuth } from "../lib/auth";
import { landingPath } from "../lib/api";
import styles from "./soon.module.css";

export default function SoonPage() {
  const { me } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const name = params.get("menu") || copy.soon.fallbackTitle;
  const home = me ? landingPath(me) : "/login";

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader title={name} sub={copy.soon.title} />
      </div>
      <section className={styles.panel}>
        <EmptyState
        title={copy.soon.emptyTitle}
        hint={copy.soon.hint}
        action={
          <Button variant="secondary" onClick={() => navigate(home === "/soon" ? "/" : home)}>
            {copy.soon.back}
          </Button>
        }
        />
      </section>
    </div>
  );
}
