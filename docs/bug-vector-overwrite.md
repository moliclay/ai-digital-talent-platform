# 向量字段被覆盖 · bug 证据

> 复现时间：2026-11-04 ｜ 状态：已复现、已定位根因、**待修复**

---

## 1. 现象

跑一次查重接口后，语义检索结果的 `education / major / skills / filename` 全部变空。前端表现：「学历 暂无数据」。

## 2. 复现步骤与真实输出

### 2.1 先重建索引（此时正常）

```bash
POST /api/vector/index
→ {'resumes': {'indexed': 6, 'total': 6}, 'jobs': {'indexed': 3, 'total': 3}}

GET /api/resumes/semantic?q=RAG&top_k=3
→ 程磊  education=本科  years=0  skills=Kubernetes、LangChain、PyTorch、FastAPI…（22 项）  filename=ai应用开发简历.pdf
→ 张伟  education=硕士  years=5  skills=PyTorch、Python、向量数据库、微调…（10 项）  filename=张伟_算法工程师.pdf
```

### 2.2 跑一次查重

```bash
GET /api/resumes/duplicates?threshold=0.5
→ pairs: 9
```

### 2.3 再检索同一句（字段被抹空）

```bash
GET /api/resumes/semantic?q=RAG&top_k=2
→ 程磊  education=""  years=0  skills=""  filename=""
→ 张伟  education=""  years=0  skills=""  filename=""
```

相似度分数没变（0.4346 / 0.3634），说明**向量本身还在，是标量字段被覆盖了**。

## 3. 根因

`app/services/vector_service.py` → `find_duplicates()`：

```python
store.upsert(settings.milvus_resume_collection,
             [{"id": int(p.id), "vector": v, "name": p.name or ""} for p, v in zip(rows, vectors)])
```

**Milvus 的 `upsert` 是整行替换，不是字段合并。** 主键已存在时，payload 里没带的动态字段会被写成空值。

而 `index_resumes()` 写的是完整行：

```python
payload = [_resume_row(p, f, v) for (p, f), v in zip(rows, vectors)]  # 含 education/major/years/skills/filename/dept_id/created_by
```

所以：**重建索引能救回来，但下次跑查重又坏。** 只要业务上有人点一次"查重"，整个简历向量库的回显字段就废了。

## 4. 影响面

| 功能 | 受影响 |
|---|---|
| `GET /resumes/semantic` | 学历/专业/技能/文件名 全空 |
| `GET /job-profiles/{id}/semantic-candidates` | 学历/年限/技能 全空 |
| `GET /resumes/duplicates` | 只返回 name，本身就没带其他字段 |
| 语义排序 | **不受影响**（相似度来自向量） |

## 5. 修复方案（见设计方案 §2.1）

1. **唯一构造入口**：`resume_row(parsed, file, vector)`，所有写简历向量的地方只准调它；
2. **删掉裸写**：`find_duplicates` 不再自己拼 payload，改为调 `ensure_indexed()`；
3. **回显回 MySQL**：三处召回的返回字段全部从 `parsed_resumes + resume_files` 批量查，Milvus 只给 id 和相似度。

第 3 条是关键：把「字段同步」从「靠记得写全」变成「结构上不可能不同步」。
