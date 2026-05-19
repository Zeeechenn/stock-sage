# StockSage 记忆系统接入与治理规划

> 来源：2026-05-19 评估 `/path/to/codex/2026-05-19/s-2/StockSage-memory-system-management-report.md` 后的修订版。
> 原报告把记忆基础设施描述为"已有完整能力"，但实际跑通的只有两条干道，其余是装好的骨架。本规划在原报告基础上修正事实错误、补全缺失项、按"主要用 Claude Code 跑项目"的使用模式重排优先级。

---

## 一、当前真实接入情况

| 模块 | 状态 | 调用方 |
|---|---|---|
| `backend/decision/memory_layered.py` | ✅ 在用 | `scheduler.py:250/278` 盘后跑信号时读写 |
| `backend/memory/research_memory.remember_deep_research` | ✅ 在用 | `research/deep_research.py:296` 深度研究写入 |
| `chat_sessions / chat_messages` 表 + 归档 | ✅ 在用 | `api/routes/ai.py` 完整对接 |
| `backend/memory/ai_memory.py` (`remember/recall/forget`) | ⚠️ 半死 | 只被 `research_memory` 当底层用，业务层零直接调用 |
| `backend/memory/should_remember.py` | ❌ 死代码 | 函数定义存在，全代码库零调用 |
| `backend/memory/audit_log.audit_write` / `audit_log_fts` | ❌ 近乎空表 | 只在迁移脚本写过一次，业务零调用 |

**关键事实修正（原报告遗漏）**：
- 决策分层记忆**不是数据库表**。中期/长期实际存储在 `~/.stock-sage/memory/medium_{symbol}.md` 与 `long_term_reflection.md` 文件里。这会影响"前端显示每股记忆规模"的实现方式。

**为什么会有死代码**：
- "在用的"两条都挂在**后端自动化链路**上（scheduler 盘后、deep_research 周末），跟客户端无关、自动跑。
- "死的"三块全是给**ChatPage 内置 AI 助手**准备的接入点。因为主要用 Claude Code 跑项目，ChatPage 链路客观上很冷，"用户说'记住'之后什么都没发生"这件事长期没人发现。
- 根因仍是**接入本来就没写完**，跟用什么客户端没有直接因果——即便重度用 ChatPage，ai.py 路由层也没有"判断→写记忆→留审计"的代码。

**与 Claude Code auto memory 的关系**：
- 两套记忆系统**不重叠、不应互相替代**。
- 业务规则（"不碰高负债公司"等）属于 stock-sage 内部，要喂给多 Agent 决策链。
- 开发上下文（项目代号、Piotroski 偏差备忘）属于 Claude Code auto memory，不该塞进 stock-sage。

---

## 二、修改规划（按依赖顺序）

### 阶段 0｜先把死代码接电（堵漏，无 UI 改动）

目标：让现有骨架可用，**优先选跟客户端无关的接入点**。

- **`audit_write` 全链路埋点**（最高优先级）
  - `memory_layered.save_decision_layered/get_layered_context`
  - `research_memory.remember_deep_research`
  - `ai_memory.remember/recall/forget`
  - 跟客户端无关，后端自动跑，立刻就能让 `audit_log_fts` 有数据。
- **`should_remember()` 接入 `ai_memory.remember()`**：
  - 在 `ai_memory.remember()` 顶部加一层（可绕过参数 `force=True`），未通过时返回 `False` 并 `audit_write` 记原因。
- **ChatPage 写入接入**：**延后**。
  - 因主要不用 ChatPage，价值低、风险高，放阶段 4 之前再补。

### 阶段 1｜修正报告的事实错误（数据统一）

- **分层记忆迁入 DB**
  - 新表 `decision_memory_layered(symbol, layer, content, updated_at)`，把 `medium_{symbol}.md` 与 `long_term_reflection.md` 一次性迁入。
  - 旧文件保留只读做兜底，30 天后删除。
  - 不迁的代价：规模查询无法用 SQL，备份/导出需双通道。
- **只读 API**：
  - `GET /api/memory/overview` — 总数、分类计数、过期数、最近更新时间。
  - `GET /api/memory/list?scope=&category=&q=` — 分页+过滤。
  - `GET /api/memory/audit?q=` — 走 `audit_log_fts`。

### 阶段 2｜可见 + 受控元数据编辑

- **AdminPage 增"记忆管理"分区**
  - 复用现有左侧导航。M6.3 里"AI 对话：辩论 / 记忆"那条可拆出来。
- **允许的操作**：
  - 删除
  - 固定（`ttl_days = NULL`）
  - 改 TTL
  - 改 category
- **禁止**：编辑 raw value。会破坏 `UNIQUE(key, scope)` 约束和结构化字段。
- **召回日志面板**：直接走 `audit_log_fts` 的 FTS5 搜索。

### 阶段 3｜治理（新模块工作量真实）

- **窗口摘要器**（**这是新模块，不是扩展现有能力**——原报告把它和 TTL 放一起会严重低估工作量）
  - 长对话超阈值压缩，新增 `chat_sessions.summary` 列。
  - 摘要本身用一次 LLM 调用生成，需独立 prompt 模板。
- **过期清理**：scheduler 加日级任务扫 `ai_memory` 超 TTL 记录，软删除（保留 30 天再硬删）。
- **深度研究只回摘要+路径**：deep_research 召回时只读 `ai_memory` 里的 indexed value，不读原始报告全文。

### 阶段 4｜对话改写（高风险，最后做）

- LLM 生成的"删除/固定/改 TTL"候选 **不直接执行**。
- 写入 `pending_ai_actions`（database.py:431 已存在，复用），用户前端二次确认再落库。
- 仍然禁止 LLM 改 raw value，只能改元数据。
- **ChatPage 写入接入**也在这阶段补：用户说"记住"→ should_remember → 写 pending_ai_actions → 二次确认。

### 横向加项（原报告遗漏）

- **反偏差缓冲**
  - `ai_memory` 增 `category='bias_override'`，例如"Piotroski 对电力/扩张期成长股 规避标签需人工复核"。
  - 召回链路在 Piotroski 输出后强制注入。
  - 让已知系统性偏差不再依赖人脑记着，进入决策链。
- **备份/导出**
  - 每日 dump `ai_memory` + `decision_memory_layered` 到 `~/.stock-sage/memory/backup_{date}.json`，防误删无回滚。
- **TTL 默认值校准**
  - 上线时按"新闻 7 天 / 研究 90 天 / 规则长期"，但留读 `audit_log_fts` 命中率回写校准的口子，不硬编码。

---

## 三、最终效果

阶段 0–4 + 横向加项全部落地后：

1. **写入**：业务事件（盘后决策/深度研究/用户改参数）→ `should_remember` 判断 → `ai_memory.remember()` upsert（同 key+scope 覆盖）→ `audit_write` 留痕。
2. **召回**：决策/研究/对话三入口走统一规则——当前窗口最近消息 + 当前对象相关记忆 + 用户固定规则 + 风险记忆 + 必要时分层决策。默认 top-k ≤ 20，不跨窗口、不读过期、不全文注入。
3. **治理**：长对话自动摘要、过期记忆 30 天软删、研究报告只回摘要+路径。**数据库长大但每次 prompt 注入量稳定**，速度不随使用时长线性恶化。
4. **用户控制**：配置页能看总量/分类/最近更新；能删、固定、改 TTL、改 category；不能改 raw value；所有写入有审计；删除有备份兜底；LLM 改写走 `pending_ai_actions` 二次确认。
5. **反偏差**：Piotroski 等已知系统性偏差通过 `bias_override` 记忆自动提示复核。

**一句话总结**：当前记忆系统是"两条干道在跑 + 一堆未通电的骨架"，规划的核心不是新建系统，是把骨架接电，并补上摘要器、二次确认流、反偏差缓冲这三块真正缺的肌肉。

---

## 四、与 ROADMAP 的对应

- 本规划在 ROADMAP 里以 **M9 记忆系统接入与治理** 追踪。
- M6.3 中"记忆管理可视化入口"占位行指向本文档。
- 阶段 0/1/横向加项预计先行，阶段 2/3 视 ChatPage 使用频次决定排期，阶段 4 取决于 LLM 可控写入的信心。
