"""技能词典 + 同义词归一。

MVP 不接大模型，技能识别靠词典：把简历全文扫一遍，命中规范名或任一别名即计为该技能。
词典是可配置资产（评审确认：先用内置 60 词，后续由甲方提供公司级清单替换）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# 规范名: (别名列表, 分类)
SKILL_BOOK: dict[str, tuple[list[str], str]] = {
    # —— 编程语言
    "Python": (["python", "py3"], "语言"),
    "Java": (["java", "jdk"], "语言"),
    "Go": (["golang", "go语言"], "语言"),
    "C++": (["c++", "cpp"], "语言"),
    "C#": (["c#", "csharp", ".net"], "语言"),
    "JavaScript": (["javascript", "js", "es6"], "语言"),
    "TypeScript": (["typescript", "ts"], "语言"),
    "SQL": (["sql"], "语言"),
    "Shell": (["shell", "bash"], "语言"),
    "Rust": (["rust"], "语言"),
    "Scala": (["scala"], "语言"),
    "R": (["r语言"], "语言"),
    "Swift": (["swift"], "语言"),
    "Kotlin": (["kotlin"], "语言"),
    "PHP": (["php"], "语言"),
    # —— AI / 算法
    "PyTorch": (["pytorch", "torch", "炬火"], "AI"),
    "TensorFlow": (["tensorflow", "tf2"], "AI"),
    "机器学习": (["机器学习", "machine learning", "ml"], "AI"),
    "深度学习": (["深度学习", "deep learning", "dl"], "AI"),
    "NLP": (["nlp", "自然语言处理"], "AI"),
    "CV": (["计算机视觉", "cv", "图像识别"], "AI"),
    "大模型": (["大模型", "llm", "大语言模型"], "AI"),
    "RAG": (["rag", "检索增强"], "AI"),
    "微调": (["微调", "sft", "lora", "finetune"], "AI"),
    "Prompt工程": (["prompt", "提示词"], "AI"),
    "Agent": (["agent", "智能体"], "AI"),
    "LangChain": (["langchain", "langgraph"], "AI"),
    "向量数据库": (["milvus", "向量数据库", "faiss", "pgvector", "chroma"], "AI"),
    "推荐系统": (["推荐系统", "召回", "排序模型"], "AI"),
    "模型部署": (["模型部署", "推理优化", "tensorrt", "onnx", "vllm"], "AI"),
    "数据标注": (["数据标注", "标注平台"], "AI"),
    # —— 后端 / 工程
    "FastAPI": (["fastapi"], "后端"),
    "Django": (["django"], "后端"),
    "Flask": (["flask"], "后端"),
    "Spring Boot": (["spring boot", "springboot", "spring"], "后端"),
    "MySQL": (["mysql"], "后端"),
    "PostgreSQL": (["postgresql", "pgsql", "postgres"], "后端"),
    "Redis": (["redis"], "后端"),
    "MongoDB": (["mongodb", "mongo"], "后端"),
    "Kafka": (["kafka"], "后端"),
    "RabbitMQ": (["rabbitmq"], "后端"),
    "Elasticsearch": (["elasticsearch", "es搜索"], "后端"),
    "Docker": (["docker", "容器化"], "后端"),
    "Kubernetes": (["kubernetes", "k8s"], "后端"),
    "微服务": (["微服务", "microservice"], "后端"),
    "分布式": (["分布式", "高并发"], "后端"),
    "Celery": (["celery", "消息队列"], "后端"),
    "Neo4j": (["neo4j", "图数据库", "知识图谱"], "后端"),
    # —— 前端
    "React": (["react", "reactjs"], "前端"),
    "Vue": (["vue", "vue.js", "vuejs"], "前端"),
    "Next.js": (["next.js", "nextjs"], "前端"),
    "Node.js": (["node.js", "nodejs", "node"], "前端"),
    "CSS": (["css", "tailwind", "less", "sass"], "前端"),
    "小程序": (["小程序", "微信开发"], "前端"),
    "可视化": (["echarts", "d3", "数据可视化"], "前端"),
    # —— 产品 / 项目
    "需求分析": (["需求分析", "需求调研", "需求拆解"], "产品"),
    "产品设计": (["产品设计", "产品规划", "prd"], "产品"),
    "项目管理": (["项目管理", "pmp", "敏捷", "scrum"], "产品"),
    "Axure": (["axure", "原型设计", "墨刀", "figma"], "产品"),
    "数据分析": (["数据分析", "bi", "报表"], "产品"),
    "用户研究": (["用户研究", "用户访谈"], "产品"),
    "运营": (["运营", "增长"], "产品"),
    # —— 通用
    "英语": (["英语", "cet-6", "cet6", "雅思", "托福"], "通用"),
    "团队协作": (["团队协作", "跨部门"], "通用"),
    "沟通": (["沟通", "表达"], "通用"),
}

# 反向索引：别名(小写) → 规范名
_ALIAS: dict[str, str] = {}
for _canon, (_aliases, _cat) in SKILL_BOOK.items():
    _ALIAS[_canon.lower()] = _canon
    for _a in _aliases:
        _ALIAS[_a.lower()] = _canon


@dataclass(frozen=True)
class SkillHit:
    name: str
    category: str
    matched: str


def canonical(name: str) -> str | None:
    return _ALIAS.get(name.strip().lower())


def extract_skills(text: str, limit: int = 30) -> list[str]:
    """按词典扫全文，返回规范名列表（保持出现顺序、去重）。"""
    if not text:
        return []
    low = text.lower()
    found: list[str] = []
    # 长别名优先，避免 "java" 命中 "javascript"
    for alias in sorted(_ALIAS, key=len, reverse=True):
        canon = _ALIAS[alias]
        if canon in found:
            continue
        if _is_ascii(alias):
            pattern = r"(?<![a-z0-9+#.])" + re.escape(alias) + r"(?![a-z0-9+#])"
        else:
            pattern = re.escape(alias)
        if re.search(pattern, low):
            found.append(canon)
        if len(found) >= limit:
            break
    return found


def _is_ascii(s: str) -> bool:
    return all(ord(c) < 128 for c in s)


def skills_overlap(required: list[str], candidate: list[str]) -> list[str]:
    """required 里被候选人覆盖的技能（两边都先归一到规范名）。"""
    cand = {canonical(c) or c for c in candidate}
    hit = []
    for r in required:
        canon = canonical(r) or r
        if canon in cand:
            hit.append(canon)
    return hit


def category_of(name: str) -> str:
    entry = SKILL_BOOK.get(canonical(name) or name)
    return entry[1] if entry else "其他"


def all_canonical() -> list[str]:
    return sorted(SKILL_BOOK)
