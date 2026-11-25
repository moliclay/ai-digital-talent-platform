import { request, tokenStore, type Me } from "./api";
import { hasPermission } from "./permission";

export type ChatSession = { id: number; title: string; created_at: string; updated_at: string };
export type ChatSource = { type: string; id: number; label: string; path?: string };
export type ChatTurn = { id: number; question: string; answer: string; status: string; source_refs: ChatSource[]; created_at: string; error_code?: string | null };
export type ChatEvent = { type: "meta"; conversation_id: number; session_id: number }
  | { type: "delta"; text: string }
  | { type: "sources"; source_refs: ChatSource[] }
  | { type: "error"; code: string; message: string }
  | { type: "done"; status: string };

export function canUseChat(me: Me | null) {
  return Boolean(me && me.user.roles.some((r) => r === "hr" || r === "admin") &&
    ["resume", "match", "talent", "job"].some((r) => hasPermission(me, r + ":view")));
}

export const chatApi = {
  list: () => request<ChatSession[]>("/chat/sessions"),
  create: (title: string) => request<ChatSession>("/chat/sessions", { method: "POST", body: { title } }),
  detail: (id: number) => request<{ session: ChatSession; conversations: ChatTurn[] }>("/chat/sessions/" + id),
  remove: (id: number) => request<null>("/chat/sessions/" + id, { method: "DELETE" }),
  async send(id: number, question: string, signal: AbortSignal, onEvent: (event: ChatEvent) => void) {
    const response = await fetch("/api/chat/sessions/" + id + "/messages", {
      method: "POST", headers: { Authorization: "Bearer " + tokenStore.get(), "Content-Type": "application/json" },
      body: JSON.stringify({ question }), signal,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      if (response.status === 401) tokenStore.clear();
      throw new Error(body?.message || "请求失败（HTTP " + response.status + "）");
    }
    if (!response.body) throw new Error("服务未返回对话流");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "", ended = false;
    try {
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        const frames = buffer.split(/\r?\n\r?\n/);
        buffer = frames.pop() || "";
        for (const frame of frames) {
          const data = frame.split(/\r?\n/).filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
          if (!data) continue;
          const event = JSON.parse(data) as ChatEvent;
          onEvent(event);
          if (event.type === "done") ended = true;
        }
        if (done) break;
      }
      if (!ended) throw new Error("对话连接提前结束，请查看历史记录");
    } finally {
      await reader.cancel().catch(() => undefined);
      reader.releaseLock();
    }
  },
};
