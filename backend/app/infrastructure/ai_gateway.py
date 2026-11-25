"""AI 网关适配器（OpenAI 兼容）。

设计原则：
1. **可缺席**：没配 Key 时 `available=False`，所有调用方回退到规则实现，不影响主流程；
2. **不重试风暴**：单次调用超时即返回 None，由调用方决定降级；
3. **可审计**：每次调用返回耗时与是否成功，由调用方写入 parse_logs / agent_run_logs。
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

from app.core.config import settings


class AiResult:
    def __init__(self, ok: bool, text: str = "", latency_ms: int = 0, error: str = ""):
        self.ok = ok
        self.text = text
        self.latency_ms = latency_ms
        self.error = error

    def json(self) -> dict | None:
        return _extract_json(self.text)


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    # 去掉 ```json 围栏
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


# 模型偶尔会把约定的英文键写成中文，调用方按英文键取值会静默拿到 None。
# 这里只做「中文 → 英文」的别名映射，调用方无需改动。
_CN_KEY_ALIASES = {
    "姓名": "name", "名字": "name",
    "电话": "phone", "手机": "phone", "手机号": "phone", "联系电话": "phone",
    "邮箱": "email", "邮件": "email", "电子邮箱": "email",
    "性别": "gender",
    "年龄": "age",
    "学历": "education", "最高学历": "education",
    "专业": "major", "所学专业": "major",
    "工作经验": "years_experience", "工作年限": "years_experience",
    "经验年限": "years_experience", "年限": "years_experience",
    "技能": "skills", "技能清单": "skills", "专业技能": "skills",
    "优势": "strengths", "个人优势": "strengths", "亮点": "strengths",
    "题目": "content", "题干": "content",
    "选项": "options",
    "答案": "answer", "正确答案": "answer",
    "分值": "score", "分数": "score",
    "解析": "analysis",
    "知识点": "knowledge_point",
    "难度": "difficulty",
}


def _normalize_keys(obj):
    """把中文键名映射成英文，嵌套 dict/list 一并处理。英文键优先，不被覆盖。"""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            nk = _CN_KEY_ALIASES.get(k.strip(), k)
            out.setdefault(nk, _normalize_keys(v))
        return out
    if isinstance(obj, list):
        return [_normalize_keys(v) for v in obj]
    return obj


class AiResult:
    def __init__(self, ok: bool, text: str = "", latency_ms: int = 0, error: str = ""):
        self.ok = ok
        self.text = text
        self.latency_ms = latency_ms
        self.error = error

    def json(self) -> dict | None:
        data = _extract_json(self.text)
        return _normalize_keys(data) if data is not None else None


class AiGateway:
    # 简易熔断：主模型刚失败过就直接走备用，避免每次请求都白等 25 秒
    _primary_failed_at: float = 0.0
    BREAKER_SECONDS = 180

    @property
    def available(self) -> bool:
        return bool(settings.ai_enabled and settings.ai_api_key)

    def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 800,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> AiResult:
        if not self.available:
            return AiResult(False, error="AI 未启用（缺少 API Key）")

        use_fallback_directly = (
            settings.ai_fallback_model
            and (time.time() - self._primary_failed_at) < self.BREAKER_SECONDS
        )
        payload = {
            "model": settings.ai_fallback_model if use_fallback_directly else settings.ai_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if settings.ai_reasoning_effort:
            # 网关支持思考等级：low / medium / high
            payload["reasoning_effort"] = settings.ai_reasoning_effort

        started = time.perf_counter()
        req = urllib.request.Request(
            f"{settings.ai_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("Authorization", f"Bearer {settings.ai_api_key}")

        try:
            # 主模型用配置的单次超时（实测 1900 字正文约 15s，12s 会误杀）
            timeout = min(settings.ai_timeout, settings.ai_timeout_fallback if use_fallback_directly
                          else settings.ai_timeout_primary)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            text = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
            if payload.get("model") == settings.ai_model:
                self._primary_failed_at = 0.0  # 主模型恢复，解除熔断
            return AiResult(True, text or "", int((time.perf_counter() - started) * 1000))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")[:300]
            return self._fallback(
                payload, started, f"HTTP {exc.code}: {detail}",
            )
        except Exception as exc:  # 超时、连接失败
            return self._fallback(payload, started, str(exc)[:300])

    def _fallback(self, payload: dict, started: float, error: str) -> AiResult:
        """主模型失败时，用备用模型重试一次（同一网关、同一超时）。"""
        if payload.get("model") == settings.ai_model:
            self._primary_failed_at = time.time()  # 记一次失败，后续 3 分钟直接走备用
        fallback = settings.ai_fallback_model
        if not fallback or fallback == payload.get("model"):
            return AiResult(False, error=error, latency_ms=int((time.perf_counter() - started) * 1000))

        retry = dict(payload)
        retry["model"] = fallback
        req = urllib.request.Request(
            f"{settings.ai_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(retry, ensure_ascii=False).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("Authorization", f"Bearer {settings.ai_api_key}")
        try:
            with urllib.request.urlopen(req, timeout=min(settings.ai_timeout, settings.ai_timeout_fallback)) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            text = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
            return AiResult(True, text or "", int((time.perf_counter() - started) * 1000))
        except Exception as exc:
            return AiResult(
                False,
                error=f"{error} | 备用模型也失败：{str(exc)[:120]}",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )



    def stream_chat(self, system: str, user: str, *, max_tokens: int = 1200,
                    temperature: float = 0.1, on_model=None):
        """Yield actual OpenAI-compatible content deltas. Never retry visible output."""
        if not self.available:
            raise RuntimeError("AI 未启用")
        primary = settings.ai_model
        fallback = settings.ai_fallback_model
        use_fallback = bool(fallback and time.time() - self._primary_failed_at < self.BREAKER_SECONDS)
        models = [fallback] if use_fallback else [primary]
        if not use_fallback and fallback and fallback != primary:
            models.append(fallback)
        emitted = False
        for model in models:
            payload = {
                "model": model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }
            if settings.ai_reasoning_effort:
                payload["reasoning_effort"] = settings.ai_reasoning_effort
            req = urllib.request.Request(
                f"{settings.ai_base_url.rstrip('/')}/chat/completions",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST",
                headers={"Content-Type": "application/json", "Accept": "text/event-stream",
                         "Authorization": f"Bearer {settings.ai_api_key}"},
            )
            timeout = min(settings.ai_timeout, settings.ai_timeout_primary if model == primary
                          else settings.ai_timeout_fallback)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    for chunk in self._stream_content(response):
                        if not emitted and on_model is not None:
                            on_model(model)
                        emitted = True
                        yield chunk
                if not emitted:
                    raise RuntimeError("模型没有返回答案")
                if model == primary:
                    self._primary_failed_at = 0.0
                return
            except Exception as exc:
                if model == primary:
                    self._primary_failed_at = time.time()
                if emitted or model == models[-1]:
                    raise RuntimeError("模型流式响应失败") from exc

    @staticmethod
    def _stream_content(response):
        """Decode SSE frames and require a terminal marker or finish reason."""
        data_lines = []
        finished = False
        for raw in response:
            line = raw.decode("utf-8").rstrip("\r\n")
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip(" "))
                continue
            if line or not data_lines:
                continue
            data = "\n".join(data_lines)
            data_lines.clear()
            if data == "[DONE]":
                return
            event = json.loads(data)
            if event.get("error"):
                raise RuntimeError("模型流式服务报错")
            choices = event.get("choices") or []
            if not choices:
                continue
            choice = choices[0]
            content = (choice.get("delta") or {}).get("content")
            if isinstance(content, str) and content:
                yield content
            if choice.get("finish_reason") == "stop":
                finished = True
            elif choice.get("finish_reason"):
                raise RuntimeError("模型未正常结束")
        if not finished:
            raise RuntimeError("模型流式响应意外中断")

    # ---------------------------------------------------------------- 多模态（扫描件 OCR）

    def chat_vision(self, image_b64: str, prompt: str, *, mime: str = "image/png",
                    max_tokens: int = 900, timeout: int | None = None) -> AiResult:
        """把一张图（base64）交给多模态模型，要求返回 JSON。"""
        if not self.available:
            return AiResult(False, error="AI 未启用（缺少 API Key）")

        payload = {
            "model": settings.ai_vision_model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                ],
            }],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        if settings.ai_reasoning_effort:
            payload["reasoning_effort"] = settings.ai_reasoning_effort

        started = time.perf_counter()
        req = urllib.request.Request(
            f"{settings.ai_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("Authorization", f"Bearer {settings.ai_api_key}")
        try:
            with urllib.request.urlopen(req, timeout=timeout or settings.ai_vision_timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            text = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
            return AiResult(True, text or "", int((time.perf_counter() - started) * 1000))
        except Exception as exc:
            return AiResult(False, error=str(exc)[:300],
                            latency_ms=int((time.perf_counter() - started) * 1000))

gateway = AiGateway()
