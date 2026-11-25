import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { MessageSquare, Plus, Send, Square, Trash2 } from "lucide-react";
import { Button } from "../components/ui/button";
import { PageHeader } from "../components/ui/page-header";
import { chatApi, type ChatSession, type ChatTurn } from "../lib/chat-api";
import styles from "./chat.module.css";

const suggestions = ["查找有 Python 技能的人才", "搜索有 RAG 项目经验的人才", "有哪些岗位存在缺口？", "如何查看某位人才的画像？"];
const statusText: Record<string, string> = { pending: "等待生成", streaming: "生成中", failed: "生成失败", cancelled: "已停止", rejected: "审核未通过" };

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [removeId, setRemoveId] = useState<number | null>(null);
  const controller = useRef<AbortController | null>(null);
  const locked = useRef(false);
  const alive = useRef(true);
  const bottom = useRef<HTMLDivElement>(null);
  const refresh = async () => { const list = await chatApi.list(); if (alive.current) setSessions(list); };
  useEffect(() => {
    alive.current = true;
    refresh().catch((e) => { if (alive.current) setError(String(e.message)); }).finally(() => { if (alive.current) setLoading(false); });
    return () => { alive.current = false; controller.current?.abort(); };
  }, []);
  useEffect(() => { bottom.current?.scrollIntoView({ block: "nearest" }); }, [turns]);

  async function open(id: number) {
    if (locked.current) return;
    locked.current = true; setBusy(true); setError("");
    try { const data = await chatApi.detail(id); setActive(id); setTurns(data.conversations); }
    catch (e) { setError((e as Error).message); }
    finally { locked.current = false; setBusy(false); }
  }
  function newChat() {
    if (locked.current) return;
    setActive(null); setTurns([]); setInput(""); setError("");
  }
  async function remove(id: number) {
    if (locked.current) return;
    locked.current = true; setBusy(true); setError("");
    try { await chatApi.remove(id); if (active === id) { setActive(null); setTurns([]); } setRemoveId(null); await refresh(); }
    catch (e) { setError((e as Error).message); }
    finally { locked.current = false; setBusy(false); }
  }
  async function send(question: string) {
    question = question.trim();
    if (!question || locked.current) return;
    locked.current = true; setBusy(true); setError(""); setInput("");
    const abort = new AbortController(); controller.current = abort;
    let id = active;
    const localId = -Date.now();
    try {
      if (id === null) { const session = await chatApi.create(question.slice(0, 32)); id = session.id; setActive(id); setSessions((old) => [session, ...old]); }
      if (abort.signal.aborted) return;
      setTurns((old) => [...old, { id: localId, question, answer: "", status: "streaming", source_refs: [], created_at: new Date().toISOString() }]);
      let turnId = localId;
      await chatApi.send(id, question, abort.signal, (event) => {
        if (event.type === "error") setError(event.message);
        const previousId = turnId;
        if (event.type === "meta") turnId = event.conversation_id;
        setTurns((old) => old.map((turn) => {
          if (turn.id !== previousId) return turn;
          if (event.type === "meta") return { ...turn, id: event.conversation_id };
          if (event.type === "delta") return { ...turn, answer: turn.answer + event.text };
          if (event.type === "sources") return { ...turn, source_refs: event.source_refs };
          if (event.type === "done") return { ...turn, status: event.status };
          return turn;
        }));
      });
    } catch (e) {
      if (!abort.signal.aborted) setError((e as Error).message);
      setTurns((old) => old.map((t) => t.status === "streaming" ? { ...t, status: abort.signal.aborted ? "cancelled" : "failed" } : t));
    } finally {
      controller.current = null; locked.current = false;
      if (alive.current) { setBusy(false); refresh().catch(() => undefined); }
    }
  }
  return <div className={styles.page}>
    <PageHeader title="ChatAI 人才助手" sub="通过自然语言查询人才、已有匹配记录和岗位信息" />
    <div className={styles.workspace}>
      <aside className={styles.history} aria-label="历史会话">
        <Button variant="primary" fullWidth iconLeft={<Plus size={16} />} onClick={newChat} disabled={busy}>新建对话</Button>
        <h2>历史会话</h2>
        {loading && <p>正在加载…</p>}
        {!loading && sessions.length === 0 && <p>暂无历史会话</p>}
        <div className={styles.list}>{sessions.map((s) => <div key={s.id} className={styles.session} data-active={s.id === active}>
          <button className={styles.sessionTitle} disabled={busy} onClick={() => open(s.id)} title={s.title}>{s.title}</button>
          <button className={styles.delete} disabled={busy} aria-label={"删除 " + s.title} onClick={() => setRemoveId(s.id)}><Trash2 size={15} /></button>
        </div>)}</div>
      </aside>
      <section className={styles.conversation} aria-label="聊天对话">
        <div className={styles.messages}>
          {!turns.length && <div className={styles.welcome}><MessageSquare size={32} /><h2>今天想了解什么？</h2><p>从一个人才、技能或岗位问题开始。</p><div className={styles.suggestions}>{suggestions.map((q) => <Button key={q} disabled={busy} onClick={() => send(q)}>{q}</Button>)}</div></div>}
          {turns.map((turn) => <article key={turn.id} className={styles.turn}>
            <div className={styles.question}>{turn.question}</div>
            <div className={styles.answer}><span className={styles.author}><MessageSquare size={16} /> 人才助手</span><div className={styles.answerText}>{turn.answer || (turn.status === "streaming" ? "正在查询并生成回答…" : "")}</div>
            {turn.status !== "success" && <span className={styles.status}>{statusText[turn.status] || turn.status}</span>}
            {turn.source_refs.filter((s) => s.type !== "scope").length > 0 && <div className={styles.sources}><span>业务来源</span>{turn.source_refs.filter((s) => s.type !== "scope").map((s) => <Link key={s.type + s.id} to={s.path || "/dashboard"}>{s.label} · #{s.id}</Link>)}</div>}</div>
          </article>)}
          <div ref={bottom} />
        </div>
        <div className={styles.composer}>
          {error && <p className={styles.error} role="alert">{error}</p>}
          <form onSubmit={(event) => { event.preventDefault(); void send(input); }}>
            <textarea aria-label="输入问题" placeholder="输入人才业务问题…" value={input} maxLength={2000} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(input); } }} disabled={busy} rows={3} />
            <div className={styles.actions}><span>{input.length}/2000 · Enter 发送</span>{controller.current ? <Button onClick={() => controller.current?.abort()} iconLeft={<Square size={15} />}>停止生成</Button> : <Button type="submit" variant="primary" disabled={busy || !input.trim()} iconLeft={<Send size={15} />}>发送</Button>}</div>
          </form><p className={styles.note}>回答基于授权业务数据，仅供 HR 业务核查。</p>
        </div>
      </section>
    </div>
    {removeId !== null && <div className={styles.overlay}><div role="alertdialog" aria-modal="true" aria-label="删除会话" className={styles.dialog}><h2>删除此会话？</h2><p>历史对话将被永久删除。</p><div className={styles.actions}><Button onClick={() => setRemoveId(null)}>取消</Button><Button variant="destructive" onClick={() => remove(removeId)} disabled={busy}>删除</Button></div></div></div>}
  </div>;
}
