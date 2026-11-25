type AnalyticsPayload = Record<string, string | number | boolean | null | undefined>;

declare global {
  interface Window {
    dataLayer?: Array<Record<string, unknown>>;
  }
}

/**
 * 极简埋点：只写 window.dataLayer，不发起网络请求。
 * 规则：不放姓名、手机、邮箱、简历正文，不放账号密码。
 */
export function track(event: string, payload: AnalyticsPayload = {}) {
  const record = { event, ...payload, ts: Date.now() };
  window.dataLayer = window.dataLayer ?? [];
  window.dataLayer.push(record);
  if (import.meta.env.DEV) {
    console.debug("[analytics]", record);
  }
}
