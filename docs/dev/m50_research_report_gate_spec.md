# M50 Phase 0 设计 spec：ResearchReportGate + 共享定义

状态：Phase 0 文档（零代码）。本文件是 M50（见 `docs/ROADMAP.md`）的设计契约，供 Phase 1 实现对照。
配套产物：`.pi/skills/serenity-chokepoint/SKILL.md`（方法论）。
定位：observe-only / source-gated / non-promoting。不改 official signal / 仓位 / 止盈止损 / scheduler / test2 / production weights。

---

## 0. 三份产物的关系（为什么必须协同设计）

| 产物 | 角色 | 本文件 |
|---|---|---|
| `serenity-chokepoint/SKILL.md` | 产出检查项（证据等级、来源、证伪、反方） | 已交付 |
| ResearchReportGate | 强制执行：检查不过的报告物理上发不出 | §2-§4 |
| 共享定义 | 两者共用的枚举/词表/口径，定义一次 | §1 |

Serenity 产检查项，Gate 负责强制执行。先有结构化输出，门才有东西可查。

---

## 1. 共享定义（只定义一次，Serenity 与 Gate 同 import）

Phase 1 落点建议：`backend/research/research_evidence_defs.py`（新文件，纯常量，无副作用）。

### 1.1 `SOURCE_TIER`（证据来源等级枚举）

```
primary       # 一手：原始公告/招股书/问询函/电话会记录
official      # 官方：交易所/监管/政府产业数据
filing        # 定期报告：年报/半年报/季报
ir            # 投资者关系：调研纪要、互动易（公司回复≠审计事实）
industry      # 可信行业媒体/产业数据库/海外龙头披露
social_lead   # 社媒/KOL/传闻 —— 仅 lead，不能作唯一证据
```

强度序：`primary > official > filing > ir > industry > social_lead`。

### 1.2 `FORBIDDEN_REPORT_WORDING`（输出文本禁用措辞）

> ⚠️ 与输入侧 `ai_supply_chain_template.FORBIDDEN_TEMPLATE_KEYS` **是两套常量、两种检查**（落实 C1）：
> - `FORBIDDEN_TEMPLATE_KEYS` 查**输入字段名**（buy_score / price_target / position_pct …）。
> - `FORBIDDEN_REPORT_WORDING` 查**最终文本措辞**。
> 同一检查不在两处写。

建议词表（中英）：

```
强烈买入 / 强烈推荐 / 确定上涨 / 必涨 / 火速上车 / 满仓 / 加仓 / 减仓 /
目标价 / 买入价 / 建仓价 / 抄底 / 梭哈 /
strong buy / must rise / guaranteed / load up / price target
```

（实现时用正则/分词，避免误伤"目标价位区间属于压力测试情景"这类引用上下文——出现即 warning，明确荐股式断言才 blocked。）

### 1.3 `pass / warning / blocked` 语义（复用 M46.5 / M47 口径，不新造）

- `pass`：正常输出。
- `warning`：允许输出，但报告文本和持久化 snapshot 必须携带 gate warnings。
- `blocked`：物理上发不出（见 §3 挂点）。

与既有口径一致：warning 不自动影响生产信号；blocked 不自动触发 memory promotion。

---

## 2. Gate 检查项清单

**作用域（S7）：所有 deep research 报告**，以 `DeepResearchReport` + `audits` 为基线；Serenity 字段（若该次跑过结构化器）作可选加严层，**不假设 Serenity 一定跑过**。

下表"基线字段来源"列均为 Phase 1 写前挂点已存在的真实对象（见 §3）。

| 检查 | blocked 条件 | warning 条件 | 基线字段来源 |
|---|---|---|---|
| 来源完整性 | `source_count == 0` 或无任何 `audit.usable` | 有源但全是非直接来源（audit 含 `网传/传闻` risk_flag） | `source_count`、`audits[].usable`、`audits[].risk_flags`、`audits[].news.url/source` |
| 时间线（lookahead） | 任一关键证据日期晚于 `as_of` | 证据粒度只到月/季 | `as_of`、`audits[].news.published_at`、`financials[].report_date` |
| 主题/标的匹配 | 标的行业与论题核心链路明显冲突 | 暴露度不清 | `topic`、`symbols`、（行业需 join Stock.industry） |
| 数据覆盖 | （Phase 2）prices/financials 全空 | **Phase 1：sections 无 catalysts/evidence → warning** | Phase 1 用 `report.sections` 代理；prices/financials 未传入 gate |
| 叙事证据 | 只有媒体叙事、无公告/财报/订单（最强证据 = `social_lead`/`industry`） | 弱证据（`weak_source_count`）占比过高 | `audits`、Serenity `evidence_tier`（若有）、`weak_source_count` |
| LLM 越界措辞 | 文本出现荐股式断言（`FORBIDDEN_REPORT_WORDING` 强命中） | 语气过强 | 渲染出的 `text`（render 后、write 前） |
| 复盘闭环 | promotion 候选缺 ReviewCase | ReviewCase 证据不足 | 仅当该路径要创建 memory candidate 时检查；纯报告默认 N/A |

加严层（仅当 Serenity 结构化器跑过）：
- 主题级 `quick_filter_pass == false` → 至少 warning。
- `research_priority_band == 证据不足` 却仍要 promotion → blocked。
- `falsification_questions` 为空 → warning（反方先行未做）。

`SerenityChokepointReport` 的 `quick_filter` **按 chain_layer 分层记录**（见 SKILL.md 第二步）：
schema 用 `quick_filter_by_layer: list[{layer, forced_demand, size_mismatch, no_substitute, outside_voice}]`
+ 派生的主题级 `quick_filter_pass: bool`（取 `scarce_layer` 那层的判定）。Gate 的加严只看主题级布尔；
分层明细供报告展示与"分层错位"洞察，不参与 Gate 阻断逻辑。

---

## 3. Gate 挂点（已对代码核实）

当前 `backend/research/deep_research.py` 顺序：

```
769  text = _render_report(...)          # 渲染文本
782  path.write_text(text)               # ← 文件落盘
784  report = DeepResearchReport(...)    # 构造结构化报告
795  if persist: _persist_report(...)    # → record_decision_run + remember_deep_research
```

问题：若把 Gate 放在 `_persist_report` 前、`write_text` 后，blocked 报告**已经落盘**，达不到"物理上发不出"。

**Phase 1 改法**：把 `report = DeepResearchReport(...)` 的构造**上移到 `write_text` 之前**，然后：

```
text   = _render_report(...)
report = DeepResearchReport(...)                 # 上移
verdict = run_research_report_gate(report, audits, text, serenity=<opt>)
if verdict.status == "blocked":
    return report_with_gate_diagnostic(verdict)  # 不 write_text / 不 persist / 不建 candidate
if verdict.status == "warning":
    text = _annotate_warnings(text, verdict)     # 文本带 warnings
path.write_text(text)
if persist: _persist_report(db, report, audits, gate=verdict)  # snapshot 带 verdict
```

blocked 时连锁不发生：不 `write_text`、不 `record_decision_run`、不 `remember_deep_research`、不建 memory candidate。

**Phase 1 已实现/已决定的两点**：
1. 数据覆盖检查在 Phase 1 用 `report.sections`（catalysts/evidence）做代理、降级为 warning（见 §2）；"证据全空"的硬阻断由「来源完整性」`source_count==0` blocked 兜底，不冗余。**Phase 2** 再把 prices/financials 传入 gate 恢复 spec 原义的 blocked。
2. blocked 当前返回**同一个** frozen `DeepResearchReport`，其 `path` 指向未写出的文件——Phase 1 无测试依赖此区分，但 **Phase 2（API/UI 接线）必须**让调用方能区分 blocked/pass（独立诊断对象或 `gate_status` 字段），否则 `report.path.exists()` 类断言会踩坑。

---

## 4. Phase 1 验收清单（供实现回填）

- [ ] `research_evidence_defs.py`：`SOURCE_TIER` + `FORBIDDEN_REPORT_WORDING`，Serenity 与 Gate 同 import。
- [ ] Serenity 结构化器：schema 单测确认**不生成** `score`/`label_vote`/trading fields；不返回 `LongTermReport`；不调用 `LongTermTeam` 聚合路径（`aggregate`/`aggregate_v2`/`run_pipeline`/`apply_research_constraints`/`_aggregate_score`）。flag 默认 False，不写 DB。
- [ ] `research_report_gate.py`：返回 `pass/warning/blocked` + reasons；单测覆盖——direct source 通过、媒体-only blocked、证据晚于 as_of blocked、越界措辞 blocked、warning 可输出但携带 warning。
- [ ] `deep_research` 写前挂点单测：blocked 时不写 Markdown、不调用 `_persist_report`。
- [ ] 隔离单测：Serenity/Gate 不影响 official signal / production profile / 长期标签。
- [ ] `make verify` 无回归。

---

## 5. 不在本批

research_priority 数字分（用档位）、TradingAgents 多 agent/checkpoint、QuantDinger action scope 细分（audit 字段加厚/可复现快照留 P2）、UZI 评委团人格、前端 evidence cards（P2）、Buffett 质量门（P1 下一批，须与 piotroski 交叉引用防双重扣分）。

---

## 6. Phase 0 人工试跑验收

拿 1 个历史主题 + 1 个新主题，过 SKILL.md 六步 + 本文 Gate 清单，确认：

- 输出能把证据 / 叙事 / 风险 / 待核验分干净。
- 零买卖语气。
- 故意塞一个"只有媒体叙事、无公告"的论题 → Gate 清单判 blocked（叙事证据 + 来源完整性）。
- 不要求写 DB。
