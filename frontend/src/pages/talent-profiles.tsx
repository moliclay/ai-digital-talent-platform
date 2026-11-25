import { useEffect, useState, type CSSProperties } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Search, ShieldX, Sparkles } from "lucide-react";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { Input } from "../components/ui/input";
import { PageHeader } from "../components/ui/page-header";
import { Pagination } from "../components/ui/pagination";
import { Skeleton } from "../components/ui/skeleton";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { formatScore, initials } from "../lib/format";
import { hasPermission } from "../lib/permission";
import { GenerateDialog } from "./talent-profiles/generate-dialog";
import styles from "./talent-profiles.module.css";
import { ProfileModal } from "./talent-profiles/profile-modal";
import { RadarChart, radarLabel } from "./talent-profiles/radar-chart";
import { DIM_ORDER, sourceNote, type PageData, type Profile } from "./talent-profiles/types";

const text = copy.talent;
const PAGE_SIZE = 12;

export default function TalentProfilesPage() {
  const { me } = useAuth();
  const navigate = useNavigate();
  const [draft, setDraft] = useState("");
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [banner, setBanner] = useState<{ tone: "ok" | "error"; message: string } | null>(null);

  const canCreate = hasPermission(me, "talent:create");

  useEffect(() => {
    track("page_view", { page: "talent-profiles" });
  }, []);

  const profiles = useQuery({
    queryKey: ["talent-profiles", keyword, page],
    queryFn: () =>
      request<PageData<Profile>>(
        `/talent-profiles?keyword=${encodeURIComponent(keyword)}&page=${page}&page_size=${PAGE_SIZE}`,
      ),
    staleTime: 20_000,
  });

  if (profiles.error instanceof ApiError && profiles.error.status === 403) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.title} sub={text.sub} />
        </div>
        <EmptyState
          icon={<ShieldX size={20} strokeWidth={1.75} />}
          title={text.noPermissionTitle}
          hint={text.noPermissionHint}
        />
      </div>
    );
  }

  const items = profiles.data?.items ?? [];
  const total = profiles.data?.total ?? 0;

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader
          title={text.title}
          sub={text.sub}
          actions={
            <>
              <div className={styles.search}>
              <Input
                value={draft}
                placeholder={text.searchPlaceholder}
                aria-label={text.searchPlaceholder}
                iconLeft={<Search size={16} strokeWidth={1.75} aria-hidden="true" />}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    setPage(1);
                    setKeyword(draft.trim());
                    track("talent_search", {
                      page: "talent-profiles",
                      hasKeyword: Boolean(draft.trim()),
                    });
                  }
                }}
              />
            </div>
            <Button
              variant="secondary"
              onClick={() => {
                setPage(1);
                setKeyword(draft.trim());
                track("talent_search", {
                  page: "talent-profiles",
                  hasKeyword: Boolean(draft.trim()),
                });
              }}
            >
              {text.searchAction}
            </Button>
            {canCreate ? (
              <Button
                variant="primary"
                onClick={() => {
                  track("talent_generate_open", { page: "talent-profiles" });
                  setGenerateOpen(true);
                }}
              >
                <Sparkles size={16} strokeWidth={1.75} aria-hidden="true" />
                {text.generate}
              </Button>
            ) : null}
            </>
          }
        />
      </div>

      {banner ? (
        <p className={banner.tone === "ok" ? styles.bannerOk : styles.bannerError} role="status">
          {banner.message}
        </p>
      ) : null}

      {profiles.isError && !(profiles.error instanceof ApiError && profiles.error.status === 403) ? (
        <ErrorState
          title={text.loadError}
          detail={profiles.error instanceof ApiError ? profiles.error.message : text.loadErrorHint}
          retryLabel={text.retry}
          onRetry={() => void profiles.refetch()}
        />
      ) : profiles.isPending ? (
        <div className={styles.grid} aria-busy="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <div className={styles.card} key={index}>
              <Skeleton width="wide" height="title" />
              <Skeleton width="full" />
              <Skeleton width="full" />
            </div>
          ))}
        </div>
      ) : total === 0 ? (
        keyword ? (
          <EmptyState
            title={text.emptySearchTitle}
            hint={text.emptySearchHint(keyword)}
            action={
              <Button
                variant="secondary"
                onClick={() => {
                  setDraft("");
                  setKeyword("");
                  setPage(1);
                }}
              >
                {text.clearSearch}
              </Button>
            }
          />
        ) : (
          <EmptyState
            title={text.emptyTitle}
            hint={text.emptyHint}
            action={
              <>
                {canCreate ? (
                  <Button variant="primary" onClick={() => setGenerateOpen(true)}>
                    {text.generate}
                  </Button>
                ) : null}
                <Button variant="secondary" onClick={() => navigate("/resumes")}>
                  {text.goResumes}
                </Button>
              </>
            }
          />
        )
      ) : (
        <>
          <div className={styles.listBar}>
            <span className={styles.count}>
              {keyword ? text.filteredCount(total) : text.count(total)}
            </span>
            <span className={styles.listHint}>{text.radarNote}</span>
            {keyword ? (
              <Button
                variant="ghost"
                onClick={() => {
                  setDraft("");
                  setKeyword("");
                  setPage(1);
                }}
              >
                {text.clearSearch}
              </Button>
            ) : null}
          </div>

          <div className={styles.grid}>
            {items.map((profile, index) => {
              const note = sourceNote(profile);
              const dims = (profile.dimensions.length ? profile.dimensions : DIM_ORDER).filter(
                (dim) => typeof profile.abilities[dim] === "number",
              );
              const radarData = dims.map((dim) => ({ label: dim, value: profile.abilities[dim] ?? 0 }));
              const peak = radarData.reduce(
                (best, item) => (item.value > best.value ? item : best),
                radarData[0] ?? { label: "", value: 0 },
              );
              return (
                <article
                  className={styles.card}
                  key={profile.id}
                  style={{ "--card-index": index } as CSSProperties}
                >
                  <header className={styles.cardHead}>
                    <span className={styles.avatar} aria-hidden="true">
                      {initials(profile.name)}
                    </span>
                    <div className={styles.titleBlock}>
                      <h3 className={styles.name}>
                        <button
                          type="button"
                          className={styles.nameButton}
                          onClick={() => setSelectedId(profile.id)}
                        >
                          {profile.name}
                        </button>
                      </h3>
                      <p className={styles.profileTitle}>{profile.title}</p>
                    </div>
                    <Badge tone={note?.ai ? "info" : "neutral"}>
                      {note?.ai ? text.aiBadge : text.ruleBadge}
                    </Badge>
                  </header>

                  <div className={styles.body}>
                    <div className={styles.copy}>
                      <p className={styles.summary}>{profile.summary || copy.common.empty}</p>
                      {peak.label ? (
                        <div className={styles.peak}>
                          <span className={styles.peakLabel}>{text.peak}</span>
                          <span className={styles.peakName}>{peak.label}</span>
                          <span className={styles.peakValue}>{formatScore(peak.value)}</span>
                        </div>
                      ) : null}
                      <ul className={styles.tags}>
                        {profile.tags.map((tag) => (
                          <li className={styles.tag} key={tag}>
                            {tag}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className={styles.radarWrap}>
                      <RadarChart data={radarData} ariaLabel={radarLabel(profile.name, radarData)} />
                    </div>
                  </div>

                  <footer className={styles.cardFoot}>
                    <Button variant="secondary" onClick={() => setSelectedId(profile.id)}>
                      {text.view}
                    </Button>
                  </footer>
                </article>
              );
            })}
          </div>

          {total > PAGE_SIZE ? (
            <div className={styles.pagination}>
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                total={total}
                onChange={setPage}
                label={text.count(total)}
              />
            </div>
          ) : null}
        </>
      )}

      <GenerateDialog
        open={generateOpen}
        onClose={() => setGenerateOpen(false)}
        onGenerated={(result) => {
          setGenerateOpen(false);
          setBanner({
            tone: "ok",
            message: `${text.generated(result.total, result.created, result.updated)}${
              result.ai_available ? "" : ` ${text.aiFallback}`
            }`,
          });
          setPage(1);
          void profiles.refetch();
        }}
      />

      <ProfileModal
        open={selectedId !== null}
        profileId={selectedId}
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}
