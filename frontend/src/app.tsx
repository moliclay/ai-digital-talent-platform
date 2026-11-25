import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./components/app-shell";
import { landingPath } from "./lib/api";
import { useAuth } from "./lib/auth";
import DashboardPage from "./pages/dashboard";
import ChatPage from "./pages/chat";
import ExamsPage from "./pages/exams";
import ExamResultPage from "./pages/exam-result";
import ExamTakePage from "./pages/exam-take";
import ForbiddenPage from "./pages/forbidden";
import LoginPage from "./pages/login";
import JobProfilesPage from "./pages/job-profiles";
import MatchingPage from "./pages/matching";
import MatchDetailPage from "./pages/match-detail";
import ResumesPage from "./pages/resumes";
import SoonPage from "./pages/soon";
import VacancyPage from "./pages/vacancy";
import SemanticPage from "./pages/semantic";
import TrainingPage from "./pages/training";
import SystemPage from "./pages/system";
import TalentProfilesPage from "./pages/talent-profiles";
import styles from "./app.module.css";

function Boot() {
  return <div className={styles.boot}>正在加载…</div>;
}

function RequireAuth() {
  const { me, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Boot />;
  if (!me) {
    const target = `/login?returnTo=${encodeURIComponent(location.pathname)}`;
    return <Navigate to={target} replace />;
  }
  return <Outlet />;
}

function RootRedirect() {
  const { me, loading } = useAuth();
  if (loading) return <Boot />;
  return <Navigate to={me ? landingPath(me) : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/resumes" element={<ResumesPage />} />
          <Route path="/job-profiles" element={<JobProfilesPage />} />
          <Route path="/matching" element={<MatchingPage />} />
          <Route path="/matching/:id" element={<MatchDetailPage />} />
          <Route path="/talent-profiles" element={<TalentProfilesPage />} />
          <Route path="/exams" element={<ExamsPage />} />
          <Route path="/exams/result/:sid" element={<ExamResultPage />} />
          <Route path="/exams/:id/take" element={<ExamTakePage />} />
          <Route path="/system" element={<SystemPage />} />
          <Route path="/vacancy" element={<VacancyPage />} />
          <Route path="/semantic" element={<SemanticPage />} />
          <Route path="/training" element={<TrainingPage />} />
          <Route path="/403" element={<ForbiddenPage />} />
          <Route path="/soon" element={<SoonPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
