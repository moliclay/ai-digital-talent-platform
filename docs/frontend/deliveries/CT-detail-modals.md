# CT-Detail Modals 居中弹窗改造

日期：2026-11-03
范围：两个详情从右侧抽屉改为屏幕居中弹窗；解析队列仍是侧边抽屉。

---

## 1. 改动

| 入口 | 之前 | 现在 |
|---|---|---|
| 简历列表 → 姓名 | 右侧 480px 抽屉 | 居中 880px Modal |
| 人才画像卡片 → 姓名 / 查看画像 | 右侧 480px 抽屉 | 居中 640px Modal |
| 解析队列 | 右侧抽屉 | 不变 |

保留行为：

- 点击遮罩关闭、右上角 X、Esc 关闭、焦点陷阱与焦点归还由 Modal 原语统一处理。
- 简历详情的下载、修正档案、保存、错误提示不变。
- 画像详情的雷达图、维度分数、优势/待验证/建议/测评证据不变。
- 弹窗内容区独立滚动，底部操作栏固定。

文件：

- `src/pages/resumes/detail-drawer.tsx` → `detail-modal.tsx`
- `src/pages/resumes/detail-drawer.module.css` → `detail-modal.module.css`
- `src/pages/talent-profiles/profile-drawer.tsx` → `profile-modal.tsx`
- `src/pages/talent-profiles/profile-drawer.module.css` → `profile-modal.module.css`

## 2. 尺寸

- 简历详情：`size="lg"`，最大 880px；1440 下约占 60%，1910 下约占 46%。
- 画像详情：`size="md"`，最大 640px；雷达图 320px 居中。
- 390 下：弹窗占满可用宽，内容区滚动，底部按钮可见；简历字段在 ≤600px 改为单列，避免邮箱被拆成单个字符。

## 3. 截图

| 文件 | 说明 |
|---|---|
| `shots/ct-resumes-modal-1910.png` | 1910 简历详情弹窗 |
| `shots/ct-resumes-detail.png` | 1440 简历详情弹窗 |
| `shots/ct-resumes-modal-390.png` | 390 简历详情弹窗 |
| `shots/ct-talent-modal.png` | 1440 人才画像弹窗 |
| `shots/ct-talent-modal-390.png` | 390 人才画像弹窗 |

## 4. 读数

```
tsc 0
lint_hardcodes 0 处（121 文件）
check_no_emoji OK
lint.mjs 0 FAIL, 3 WARN
build JS 159.29 kB gzip · CSS 19.52 kB gzip
1910 / 1440 / 390 均无横向滚动
```
