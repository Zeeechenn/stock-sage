# StockSage — 路线图（进行中与待做）

> 已完成里程碑详情优先见 `CHANGELOG.md`。本文件优先列当前未完成任务项（`[ ]`）、暂缓项和必要接手摘要；完成项只保留会影响后续执行边界的部分。
> 排序按当前接手优先级和风险边界组织，不严格按 M 编号递增；例如 M44 直接承接 M43 后的 Atlas 合并基准。

## 当前接手入口

| 工作线 | 当前状态 | 第一动作 | 停止条件 |
|---|---|---|---|
| M44 Atlas 合并 | Phase 0 已本地完成，`main` 有 M43 baseline；下一步是 Atlas rebase/Gate-A | 在 Atlas worktree rebase 到 `pre-atlas-m43-baseline` 后的 `main`，保护 M31/M41/M42/M43 主线能力 | 任何 official signal/test2/scheduler/shared-infra 漂移先停下归因 |
| M29 Forward Evidence | fresh forward coverage 尚未 ready；所有 alpha 证据仍 non-promoting | 先跑 `backend.tools.m29_forward_readiness --db-url ...`，ready 后再追加 1d/3d/5d forward shadow | 会恢复 quant、改 production profile、接 checkpoint、写真实 sentiment_cache 或调额外付费服务时先确认 |
| 历史完成项 | M30/M31/M41/M42/M43/M27/M28 仅保留执行边界摘要 | 需要细节时看 `CHANGELOG.md` / 对应工具 artifact | 不从历史摘要推出新的生产行为 |

---

## ⭐ M29 Alpha Reset / Forward Evidence Engine【P0 当前最高优先】🔬

> 当前入口。M27 已形成完整离线证据闭环，但所有候选均未过 production promotion gate。M29 的职责是把弱正向线索转为可积累、可复核、可预注册的 forward evidence；在完整 gate 与人工确认前，生产继续 `WEIGHT_QUANT=0.0`、`new_framework`、Kronos disabled。

### M29 当前决策与非目标

- 当前没有候选进入 promotion review：尚无 post-registration fresh forward 证据，旧 artifact 仍有 provenance/data-quality blockers。
- 不恢复 `weight_quant`，不改 production signal profile，不接 Kronos checkpoint，不把 M27 failed candidate 换名包装成 production alpha。
- 所有工具默认只读或 shadow：不写 DB、不调 LLM/API、不训练、不保存模型，除非用户明确批准。

### M29.1 Forward Evidence Ledger（已建，继续使用）

- [x] `backend.tools.m29_evidence_ledger` 汇总 M27/M29 artifact，输出 candidate、window、sample size、IC/ICIR、stride/non-overlap、monotonic、top-bottom、blockers、multiple-comparison、production_unchanged。
- [x] 已纳入 top-decile forward shadow、pure polarity/event overlay v2 gate、short-cycle/regime candidates、Kronos failed checkpoints、M29 shadow validation、quant residual attribution。
- [ ] 新增 forward artifact 后必须重新进 ledger；若 `gate_pass_count=0` 或存在 provenance/data-quality blockers，保持 non-promoting。

### M29.2 Hypothesis Registry / Promotion Contract（已建，继续约束）

- [x] 预注册候选包括 `regime_low_vol_alpha_v1`、`intra_industry_relative_strength_v1`、`liquidity_turnover_state_v1`、`post_event_drift_pure_polarity_v1`、`top_decile_entry_timing_v1`。
- [x] 生产 gate 固定：IC ≥ 0.04、ICIR ≥ 0.40、分层单调、fresh OOS/forward、非重叠稳定性、多重比较披露、data-quality blockers 清零、人工确认。
- [x] registry 与 ledger 会渲染/校验 promotion contract；没有完整字段的报告不能作为晋升证据。

### M29.3 Forward Shadow 自动延长（当前第一动作）

- [x] `backend.tools.m29_forward_readiness` 已作为只读 readiness guard：只判断完整交易日与 1d/3d/5d future-return 覆盖是否足以运行下一轮 bundle。
- [x] `backend.tools.m29_price_coverage_refresh` 已提供 close-confirmed price/provenance refresh；默认 dry-run，`--execute` 才写 `prices`，且拒绝今日 partial bar。
- [ ] 当前 rolling forward shadow 只延至 2026-05-29；2026-06-01 仍是 partial / future-return 未覆盖，不追加 fresh evidence。下一次先跑 readiness，再按 ledger 的 `next_forward_commands` 追加 1d/3d/5d。
- 样本门保持保守：filtered trades < 50 不引用 Sharpe，IC days 不足不引用 ICIR 稳定性，分位不单调不能晋升。

### M29.5 Quant Residual Attribution（首轮完成，等待 fresh forward）

- [x] 首轮 `backend.tools.m29_quant_residual_attribution` 已输出 `/private/tmp/m29_quant_residual_attribution_v1.{json,md}`，并进入 ledger。
- [x] 当前结论：量化可能有离散过滤价值，但未证明对 `technical+sentiment/event` 残差有稳定连续 alpha；关键 5d residual IC=0.018251、ICIR=0.151156、monotonic=False、gate_pass=False。
- [ ] fresh coverage ready 后，在同一 forward window 追加或复跑 fixed-threshold quant sweep、逐笔 attribution、residual IC 与交互分桶，再讨论任何小权重灰度。

### 新对话执行交接

1. 先读 `STATUS.md` 与本节，再运行 `git status --short`。
2. 第一动作：只读跑 `backend.tools.m29_forward_readiness --db-url ...`；未 ready 时停在等待状态，不把 partial local data 当 fresh evidence。
3. 第二动作：若 ready，运行 1d/3d/5d forward shadow bundle，并把新增 artifact 纳入 `m29_evidence_ledger`。
4. 第三动作：在同一 forward window 更新 M29.5 attribution/residual evidence；若仍 non-promoting，保持 `WEIGHT_QUANT=0.0`。
5. 停止条件：任何步骤会改变生产信号、恢复 quant、接入 checkpoint、继续 Kronos 长训、真实写 `sentiment_cache`、下载新依赖或调用额外付费外部服务。

---

## M30 工程质量收敛【完成】🛠️

> 完成摘要。详细历史与验证记录优先见 `CHANGELOG.md`；本节只保留后续开发需要遵守的边界。

- [x] 类型检查、M29 工具类型收敛、Python lock / frozen sync、CI 拆分、coverage / security / dependency audit 入口已完成。
- [x] 核心路径专项测试已补：aggregator、pipeline、database runtime schema、AI/system routes、memory layered、researcher degraded input。
- [x] 低噪声安全修复已完成：SQL table whitelist / bound params、hash 用途说明、Qlib joblib、外部 requests size guard、Bark retry、非 CLI `print()` 审计。
- [x] 可维护性拆分完成：前端 advisory lint/format、`AdminPage` 展示组件拆分、本地 ignored `test2_ab_runner` 模块化。
- 当前边界：`make verify` 仍是 release-quality gate；Python/npm 依赖升级必须跑 lock check、dependency audit、关键数据源 smoke；前端 lint/format 仍是 advisory，不因格式化制造无关 churn。
- 不再保留的旧评审噪声：错误路径、错误 CI 判断、未复现 XSS/sha1/docs 数量等不作为规划项。

---

## M31 工程化与产品化借鉴（StockInsight 对标）【完成】🧰

> 完成摘要。M31 借鉴的是工程表达与产品化入口，不引入 StockInsight 式涨跌预测、Strong Buy/Sell 或 ML 投票预言。

- [x] 显式 L1/L2/L3 cache policy、盘中 zero-network contract、provider fallback observability 与只读 benchmark 已完成。
- [x] 数据源按类型声明 freshness / TTL / observe-only 边界，并在 `/api/system/data-coverage` 暴露 fallback chain。
- [x] `backend.agent.cli` / `stocksage` 已有 `premarket` / `intraday` / `postmarket` / `weekend` 交易节奏命令，默认 dry-run orchestration。
- [x] postmarket HTML / Word-compatible report 已输出 rule/profile、信号表、证据卡、持仓复盘和非投资建议声明。
- 当前边界：M31 不改变 production signal profile，不恢复 quant，不把报告输出当交易建议；详细 SLA 和历史验证看 `CHANGELOG.md` / README。

---

## M42 价格复权口径(qfq/hfq)污染防护与修复【complete】🧹

> 来源：ATLAS Gate-B 前瞻跟踪发现约 30% 的 5 日前瞻收益不可信（|net|>1.5）。根因：2026-05-25/26 有约 52 个标的的后复权(hfq)收盘价被写入 prices 表且 `adjustment=NULL`，与 qfq 行无法区分，导致 qfq 入场价 / hfq 退出价产生 100–330x 伪收益。`adjustment` 列历史上 99.94% 为 NULL，无法按标签过滤。

- [x] 写入时护栏：`backend/data/price_quality.py:check_adjustment_basis_jump`（close > 3×前10中位数即判为污染）+ `PriceQualityPolicy.adjustment_jump_ratio`；接入 `backend/data/market.py:backfill_if_needed`，写库前跳过污染行（下次 backfill 以 qfq 重抓）。`evaluate_price_quality` 与打分逻辑不变。
- [x] 一次性修复 CLI：`backend/tools/m42_remediate_hfq_contamination.py`（dry-run 默认、删前 `shutil.copy2` 备份、拒绝生产路径、原生 sqlite3、跑到 0 行；级联需 2 遍收敛）。
- [x] 线上修复：删除 2026-05-25/26 共 84 行混合口径污染行（恢复备份 `~/.stock-sage/backups/stock-sage.db.bak.20260603_174914`）；真实判据复检 0 残留；周边日期 (05-22/05-27) 行数不变。新增 33 个 hermetic 测试，全量 754 passed。
- [x] 整条 hfq 标的修复（2026-06-04）：600519(茅台)/600601/600602 三只整条序列为 hfq（茅台 ¥9,108、600601 ¥151,341、600602 ¥10,767），删整条 + 经项目 backfill 链 qfq 重抓（years=6，源 tickflow_cn，adjustment 标签已填）。修后茅台 ¥1,268、600601 ¥12.62、600602 ¥18.35；全库 max close>10000 清零；OHLC 自洽；备份 `~/.stock-sage/backups/stock-sage.db.bak.20260604_203532`。

> 编号说明：M33–M40 属 ATLAS 研究架构分支（codex/atlas），主线 M32→M41 跳过了 M33–M40；M42 衔接 M41 之后，两分支编号无冲突。

---

## M43 架构边界硬化与行为等价重构【complete】🧱

> 来源：2026-06-04 代码架构复盘。项目整体不是单文件式“屎山”，但 `market.py`、`database.py`、`api/routes/ai.py`、`scheduler.py` 已经开始变厚；M43 采用兼容 facade + characterization tests，而不是推倒重写或拆微服务。

- [x] Market facade：`backend.data.market` 保留 public imports、provider 注册顺序、fallback、adjustment attrs、M42 写入 guard；实际 helper 拆到 `market_utils.py`、`market_sources.py`、`market_persistence.py`。
- [x] Runtime schema / seed：`database.py` 保留 ORM models、session、`get_db`、`init_db` 与兼容私有入口；启动时 schema patch 和默认 seed 分别落到 `schema_runtime.py` / `seed.py`。
- [x] News cycle cleanup：`RawNews` 迁到 `news_models.py`，`news.py` 与 `news_audit.py` 不再形成真实双向依赖。
- [x] AI route split：`api/routes/ai.py` 保留 HTTP/SSE、pending/confirm 和旧测试 wrapper；自然语言 action 解析、chat store、确定性回答构建分别落到 `agent/action_parser.py`、`memory/chat_store.py`、`agent/chat_responder.py`。
- [x] Scheduler split：`scheduler.py` 保留 scheduler 生命周期、job state、tracked jobs、kill-switch guard、cron schedule 与旧 monkeypatch 接缝；实际 job workflows 拆到 `backend/jobs/`。
- [x] Architecture guard：新增 AST 级 `tests/test_architecture_boundaries.py`，硬门禁只检查顶层 backend import graph、API routes 顶层 heavy-provider imports、核心 facade 行数，避免误伤有意 lazy import。

> 2026-06-04 M43 完成：`market.py` 从约 659 行降到 179 行，`api/routes/ai.py` 从约 657 行降到 344 行，`scheduler.py` 从约 858 行降到 352 行，`database.py` 从约 718 行降到 452 行。生产信号、provider 优先级、API URL/response、SSE 顺序、scheduler job id/时间表、`WEIGHT_QUANT=0.0` 均未改变。
> 验证：ruff、mypy、759 个 backend tests、19 个 frontend node tests 通过；集成 `make verify` 到 Vite build 步骤时因沙盒无法写 `frontend/node_modules/.vite-temp` 报 `EPERM`，随后在正常文件权限下单独 rerun `npm --prefix frontend run build` 通过。

---

## M44 Atlas 合并与 L0-L4 主架构升级【active / Phase 1 next】🧭

> 来源：2026-06-04 Atlas 合并规划。Atlas 不是主项目旁边的独立功能区，而是 `main` 的下一代架构候选；首个合并目标是工程安全落地，不是让新策略行为立刻影响正式信号。外部 `PLAN (2).md` 已被压缩进本节，后续 AI 以本节和 `STATUS.md` 为接手入口。
>
> 当前入口事实（执行前必须重新核验）：Phase 0 已在本地完成，`main` 有 M43 merge baseline，`pre-atlas-m43-baseline` 指向该合并点；Atlas worktree 为 `/Users/zeeechenn/Documents/项目s/atlas` 的 `codex/atlas`；测试2保持 frozen baseline，不中途改口径。

### M44.0 合并原则与已锁定决策

- **工程合并 gate**：判断 Atlas 架构代码能否进入 `main`。合并当天必须生产行为等价、默认休眠、可回滚。
- **投资效果 gate**：判断 Atlas 新行为能否影响正式信号、仓位、止损或未来自动交易；只看 shadow/test4 数据，不用工程合并结果替代投资证据。
- 首次 Atlas 合并必须是 dormant merge：总闸默认关闭，例如 `ATLAS_ENABLED=false` / `atlas_research_enabled=false`；official signal、test2、test3、标的1、scheduler/postmarket 不经过 Atlas 新逻辑。
- 分模块 flag 只能是二级开关，不能替代 Atlas 总闸；总闸也不能替代 migration、runtime schema、依赖、共享 helper 的单独 gate。
- 首次合并只允许 additive / non-destructive migration：新增表、nullable 新列、非破坏性 index、idempotent runtime schema patch；禁止删除/重命名旧表旧列、重写 live 旧行、改变既有字段语义或加不兼容约束。
- Atlas 不能用 tip 覆盖主线，只能在 M43 后的 `main` 上 rebase/重放增量；每次 `main` 有 test2、scheduler、database、official signal、M31/M41/M42/M43 相关非琐碎提交都要 re-sync。
- `Gate-B` 保留给现有 Atlas/M40 prospective tracker；L4 命名为 Review / Promotion / Calibration。
- 合并前范围只保留最小闭环：L0 最小 memory contract、L1/L2 case skeleton、一个只读 adapter/case view、memory promotion gate、Atlas 总休眠开关、行为等价验证和回滚 runbook。

### M44.1 Phase 0：固定主线基准，先合 M43（P0 已完成）

目标：让 `main` 先拥有 M43 架构边界硬化，成为 Atlas rebase 的唯一真实基准。

- [x] 确认主仓 M43 分支为 `codex/m43-architecture-boundaries`，worktree 干净，且相对 `main` 只有 M43/文档相关提交。
- [x] 跑完整主仓 gate：`make verify`，并记录结果；若环境 cache 或 Vite temp 权限导致假失败，使用 `/private/tmp` cache 或正常文件权限复跑对应步骤。
- [x] 固定 `--end` 重跑 test2 replay 到 `/private/tmp`，要求与 `paper_trading/test2_ab_state.json` 零 diff；不要改 `paper_trading/test2_ab_state.json`。
- [x] 将 M43 合入 `main`，保留可追溯历史，不 push。
- [x] 合并后建立 `pre-atlas-m43-baseline` 或同义 tag/branch。
- [x] 合并后确认：production profile 仍是 `new_framework`，`WEIGHT_QUANT=0.0` 不变，test2 replay、test3 universe、标的1文件、official signal 行为不变。

停止条件：`make verify` 失败、test2 JSON diff 非零、`main` 有未纳入判断的反向提交、或 M43 分支出现非 M43 范围改动时，先停下归因，不进入 Atlas rebase。

> 2026-06-04 Phase 0 completed locally：`main` merge commit `4882d49` 已包含 M43 与 M44 文档接手更新，并打本地 tag `pre-atlas-m43-baseline`（未 push）。M43 分支与 post-merge `main` 的 `make verify` 均通过：ruff、mypy、759 backend tests、19 frontend node tests、Vite build。test2 replay 固定 `--end 2026-06-04` 写入 `/private/tmp/stocksage_test2_ab_state_20260604_postmerge.json`，与 `paper_trading/test2_ab_state.json` JSON 相等且 SHA-256 均为 `3ad1af227d3767d27720122df8303d5afa84bc7b89415e69e9f60b68c298cdcd`。运行时边界确认：active profile `new_framework`，quant/technical/sentiment=`0.0/0.6/0.4`，entry threshold `25.0`，multi-agent off，Kronos off，official signal markets 仍为 `CN`，HK/US observe-only。

### M44.2 Phase 1：Atlas rebase 到 M43/main

目标：把 Atlas 从过期分支变成基于当前主线的架构候选。

- [ ] 在 Atlas worktree 内 rebase/重放到 M43 后的 `main`，不让 Atlas 删除或覆盖 M31/M41/M42/M43 主线能力。
- [ ] 明确保护 main-only 文件：cache policy、global data、market capabilities、price quality、M43 facade/jobs/architecture guard 等。
- [ ] 重点处理冲突：项目文档、`backend/data/database.py`、`docs/ROADMAP.md`、API/schema、`pyproject.toml`、`uv.lock`。
- [ ] 重做 Gate-A merge-safety；旧 `ATLAS_MERGE_SAFETY.md` 只能作历史参考。
- [ ] 跑 `make verify`、migration focused tests、M43 reproduction focused tests；Gate-A 只表示可进入架构审查，不等于批准合并。

### M44.3 Phase 2-3：定稿 L0-L4 contract，并优先完成 L0

目标：先把“合并后主项目是什么”定死，再完成最小记忆/知识底座。

| 层级 | 名称 | 职责 | 首次合并边界 |
|---|---|---|---|
| L0 | Memory / Knowledge Base | 长期知识、用户规则、历史教训、A老师方法、专题研究沉淀 | 最小 memory contract；legacy 默认 pending / legacy_import_pending |
| L1 | Evidence Layer | 带来源、时间、PIT、质量状态的证据 | EvidenceCard / Dossier 只读映射 |
| L2 | Thesis Layer | 研究命题、主题假设、失效条件、持有周期 | ResearchCase / Thesis skeleton |
| L3 | Action / Signal / Position Layer | 入场、持有、仓位、止损、退出建议 | ActionProposal 只做 proposal/shadow，不接 official path |
| L4 | Review / Promotion / Calibration Layer | 结果复盘、归因、校准、记忆晋升 | ReviewCase / PromotionGate；LLM 不得自动写 trusted memory |

- [ ] L0 设计复审前不做不可逆 schema 决策。
- [ ] 梳理 `stock_memory_items`、`decision_memory_layered`、research memory、A老师 skill、专题研究报告、ReviewCase candidates、用户明确要求记住的规则/偏好。
- [ ] 定义 memory scope：stock、theme、sector、market/global、user preference、methodology/skill。
- [ ] 定义 trust 状态：raw、pending、trusted、refuted、archived、legacy_import_pending。
- [ ] ResearchCase 和 ActionProposal 召回 memory 时必须区分 trusted 与 pending；trusted 只走 human gate / ReviewCase promotion。

### M44.4 Phase 4-5：最小 adapter 与 dormant merge

目标：用一个最小 adapter 证明旧模块可进入新架构，然后把 Atlas 合入 `main` 但保持默认休眠。

- [ ] 首个 adapter 优先选择 deep_research 或已有 dossier，只读接入 `ResearchCase` / `EvidenceCard` / memory candidate，不影响 official signal。
- [ ] 实现 Atlas 总休眠开关；总闸关闭时新 routes/modules 返回 disabled/empty/manual-only 行为。
- [ ] 合并前必须通过：final re-sync、final Gate-A、`make verify`、test2 replay zero diff、canonical parity、official signal parity smoke、scheduler/postmarket parity smoke、additive migration review、DB migration copy-smoke、dependency/lockfile shared-infra review、API route smoke、memory promotion gate smoke、architecture import guard、Atlas dormant flag smoke、`git diff --check`。
- [ ] 行为等价标准：official signal、`WEIGHT_QUANT=0.0`、test2 replay、test3 口径、标的1、stop/take/position sizing、daily/postmarket 自动流程均不变；ActionProposal 只能 shadow/proposal，不自动执行。

### M44.5 Phase 6：合并后启动 Atlas shadow/test4

目标：用投资效果数据验证 Atlas 新行为，不污染测试2。

- [ ] 测试2继续 frozen baseline：原规则、原状态、原 A/B 目标、原 dependency path；Atlas 合并后的普通 PR 也不得改变 test2 replay、runner 输入、退出/入场规则、position sizing、signal loading 或 state JSON 口径。
- [ ] test4 指标、阈值、样本窗口、失败条件必须预注册；同窗口回放只能 diagnostic，不能作为 promotion proof。
- [ ] 第一阶段可用 test2 universe / 日期窗口 / 价格数据 / 基础 signal，Atlas 只生成 shadow overlay。
- [ ] 建议三臂：`test2_baseline`、`atlas_exit_overlay`、`atlas_entry_exit_overlay`。
- [ ] 指标至少包括收益、回撤、卖飞率、误杀趋势率、重新入场质量、proposal 命中率、机会成本、额外回撤和尾部风险；proposal 命中率必须预定义 horizon、label source、判定规则和样本不足处理。

### M44 回滚 runbook 摘要

- 合并前打 `pre-atlas-m43-baseline` 或同义 tag/branch，记录 production profile、`WEIGHT_QUANT`、scheduler job ids、test2 state hash、schema digest、关键 production table row counts、lockfile hash、fixed-fixture official signal 输出。
- Atlas merge 保留为可 revert 的 merge commit；不要 squash 成难以回滚的散乱提交。
- 常规回滚优先 revert merge commit 或切回 baseline；SQLite copy 只作灾难恢复，不作为常规 rollback，避免丢失回滚窗口内新增 live 数据。
- 触发回滚：schema drift、旧 production row 非预期重写、official signal drift、test2 canonical parity drift、scheduler/postmarket drift、trusted memory 非预期写入、总闸关闭时 production path 仍调用 Atlas 行为模块。

---

## M41 A/HK/US Global Data/Research Buildout【complete】🌐

> 完成摘要。M41 已把 A/HK/US 数据能力统一成只读、可审计的数据/研究 facade；HK/US 仍是 observe-only research context，不进入官方信号。

- [x] `backend.data.global_data`、`GET /api/system/global-data`、`python3 -m backend.agent.cli global-data` 已按 `market + symbol + intent` 输出统一 envelope：source、fetched_at、currency/timezone、freshness、missing fields、PIT gate、write policy、signal safety。
- [x] A/HK/US 七层 capability catalog 已覆盖 quote/kline/fundamentals/capital_flow/derivatives/filings/tools_fallback，并在 `/api/system/data-coverage` 和 Admin 面板展示。
- [x] HK/US daily price、SEC/HKEX/yfinance probe、probe summary、health ledger、field normalization/PIT gates、global watchlist/portfolio UX 均已落地为 read-only / observe-only。
- [x] CN production boundary 已复核：official signal markets 仍为 `CN`；HK/US 不进入 postmarket batch、stop-loss checks、long-term constraint labels、`save_signal()` 或 composite scoring。
- 当前边界：任何 HK/US 或新增数据层想影响 scoring/position/signal，必须先注册 evidence candidate，走 M29 ledger、fresh forward、PIT/provenance、promotion gate 与人工确认。
- 停止条件：会写生产 DB schema、定时任务、长期 health 表、批量付费 API，或影响 official signal / test2 replay / scheduler / position sizing 时，先做只读验证和用户确认。

---

## M32 Forward 预测层 / 复盘 → 假设桥【设计立场 + 启动路径】🧭

> 记录于 2026-06-02。背景：评估小红书 StockInsight v3.0 的"AI 预测 + Strong Buy 评级"卖点后，确立本项目对"预测"的立场，并把"想像 A 老师一样提前判断赛道方向"这个目标落到可执行路径上。供未来开发参考，**不要重复讨论要不要做价格预测**。

### 立场：两种"预测"，只做一种

- **不做（明确拒绝）**：个股短期涨跌方向的 ML 分类 + 置信度 + Strong Buy/Sell 评级。理由：
  1. 违反 `AGENTS.md`「不把价格当确定性预测、不鼓励 strong buy」与 `PROJECT.md` 核心约束；
  2. M26/M27 已用完整 gate（DSR/PBO/walk-forward）否决该类候选，生产 `WEIGHT_QUANT=0.0`——系统已如实证明该 edge 不显著；
  3. 周末速成式 ML（多股 × 多技术特征）是过拟合 + 未来函数标本，输出"假确定性"比没有更危险。
  - 评级分数可保留，但定位为**多因子体检快照 / 5000 股分诊工具**，显式标注"非预测"。
- **要做（正路）**：赛道级、基本面/供应链驱动、**可证伪**的前瞻论点。这才是 A 老师"半年前判断存储牛市"的真实方法（供应链锁单 / 海外领先指标 / 周期 vs 结构性升维 / 盯边际变化），与 ML-on-price 无关。本项目已有的 M29 forward evidence + `/a-teacher` skill 就是它的载体。

### 复盘 → Forward 的三步桥（启动前提：复盘数据足够厚）

- [ ] **第 1 步 — 复盘攒"信号→结果"数据集**：用测试1/测试2 + `audit_log_fts` 沉淀"哪些信号在自有历史里真正领先行情"，作为 forward 假设的训练与校准基准。（与现有复盘工作合流，非新坑）
- [ ] **第 2 步 — 把验证过的信号注册成 forward 假设**：扩展 `backend.tools.m29_hypothesis_registry`，新增"赛道级前瞻论点"类型——动机用供应链/海外领先指标证据、horizon、证伪条件、最小样本门、多重比较规则齐全；接入 `/a-teacher` 五层框架（供应链核查 / 海外领先指标 / 周期升维 / 炒作过滤 / 高位过滤）作为论点的证据模板。
- [ ] **第 3 步 — forward 跟踪与回溯打分**：论点进入 M29 forward shadow / evidence ledger，事后按是否兑现做校准；输出形态是"带证据、可证伪、置信度被回溯打分的论点"，不是 Strong Buy 标签。

### 边界

- 启动时机：等第 1 步复盘数据更厚再正式开 M32.2/M32.3；当前保持 M29（forward evidence）为 P0。
- 不恢复 `weight_quant`、不接 Kronos checkpoint、不改生产 signal profile——M32 是研究/论点层，与生产信号解耦，遵循 M29 的 non-promoting / production_unchanged 纪律。

---

## M27 Alpha 根治工程【证据闭环，未晋升】🔬

> 历史摘要，不作为当前入口。当前入口是 M29；生产继续 `WEIGHT_QUANT=0.0`，不改 signal profile，不接 Kronos checkpoint。

- M27 production gate 已统一为 IC ≥ 0.04 / ICIR ≥ 0.40 / 分层单调；所有候选未达门槛。
- M27.1：经典因子、label/objective、top-decile 离散过滤、multi-exit/short-cycle/regime/include-inactive 均完成离线验证；过滤器有研究价值但只能作为 non-promoting diagnostic。
- M27.2：test3 约 100 支 universe 工程前置完成；`paper_trading/` 本地材料被 ignore，不作为 Git 交付。
- M27.3：sentiment_cache 对齐、lookback=5 回填、pure polarity / event overlay v2 gate 已闭合；pure polarity 和 polarity+event 均 `monotonic=False`，不晋升。
- M27.4：Kronos Path A launcher/smoke/真实隔离长训/同标尺评估已完成；`step_001500` 与 `step_002000` IC/ICIR 为负且未过 gate，不接生产。
- 关键 artifact：M27/M29 证据已由 `backend.tools.m29_evidence_ledger` 汇总；旧报告分布在 `/private/tmp/m27_*` 与 `~/.stock-sage/m27_*`。
- 停止条件：继续更长 Kronos training、覆盖 checkpoint、下载/安装新依赖、恢复 quant 权重、接入 checkpoint、或任何会改变生产信号配置的动作，必须先确认。

### M27.1 经典因子工程（历史）

- [ ] 重训 LightGBM 并达到 M27 alpha 目标后，才可重新讨论生产晋升。当前未达标。

### M27.2 / M27.3 / M27.4 历史状态

- [x] test3 universe、event taxonomy / sentiment cache pipeline、Kronos Path A 工程与评估均已完成。
- [x] 结论统一：保留为 non-promoting evidence，后续通过 M29/M32 重新组织，而不是继续在 M27 里扩坑。

---

## M28 调研模块整合与实时搜索接入【完成】✅

> 完成摘要。M28 已把 deep_research、copilot、多轮辩论从信息孤岛接成结构化研究流；详细设计见 `docs/M28_RESEARCH_INTEGRATION_PLAN.md`。

- [x] `ResearchSection` 已升级为 IC memo schema：catalysts、risks、valuation_anchor、evidence_snippets、stance、confidence。
- [x] deep research 已接 Tavily web search evaluator/planner loop，报告展示来源 URL，空 seed query 不再耗尽重试。
- [x] 多轮辩论可注入 `research_context`，bull/bear 轮分别接收 catalysts/risks/evidence；盘后路径可从 `research_pointer.evidence_json.sections` 恢复上下文。
- [x] copilot pending questions 可进入 dossier / deep_research seed queries。
- 当前边界：M28 是研究信息流，不直接改变 official signal、position sizing 或 production profile。

---

## M26 量化层重估 ✅ / M26.3 暂停

M26.0 基线 ✅ / M26.1 扩盘 ✅ / M26.2 Kronos 零样本 ✅（IC=-0.0017，不替换）

报告存档：M26 baseline / 扩盘诊断写入 `~/.stock-sage/m26_quant_baseline_report.{md,json}`，Kronos 零样本写入 `~/.stock-sage/m26_kronos_report.{md,json}`；当前决策口径以 M26.1/M26.2 后的 `keep_quant_disabled` 为准。

### M26.3 小权重 Paper Trading 验证（暂停）

> **重启条件**：M29 新 alpha gate（IC ≥ 0.04 / ICIR ≥ 0.40 / monotonic=True）达标后重新评估。

- [ ] 在 `test2_ab_runner.py` 新增第三臂 `quant_small`（Q=0.15, T=0.55, S=0.30, threshold=25）
- [ ] 跑满 4 周，按测试 2 汇报约定只汇报总结
- [ ] 决策门：`quant_small` 收益持续跑赢 `quant_off` ≥ 2pp 且最大回撤不高 → 进入生产权重恢复讨论

---

## M24.3 长期约束重新接入验证 ⏳

- [ ] **shadow forward outcome 观察**（从 2026-05-27 起）：每天保留只读报告输出，跟踪 `blocked_entry / position_reduced / score_capped` 样本的 1d/3d/5d/10d 表现；口径优先用相对沪深 300 超额收益。只观察，不开启约束。
- [ ] **中期检查点（建议 2026-06-10）**：汇总首批 shadow 样本，判断长期标签是否降低假阳性；不足或不稳定则继续观察。
- [ ] 测试 2 冻结期结束后（≥ 2026-07-18），用重建后的可信标签回放历史信号，严格按 PIT 口径对比「无约束」vs「有约束」；禁止使用未来生成的标签回改过去交易。
- [ ] 只有约束降低假阳性且不显著误杀有效入场时，才将 `LONG_TERM_CONSTRAINTS_ENABLED=true` 纳入下一轮测试架构。

---

## M25 综合改进路线图（剩余项）⏳

已完成：M25.0–M25.4 主体 / M25.2 统计口径补债 / M25.3 LLM 成本可观测性 + 跨入口契约回归测试

**M25.4 剩余（低优先）**
- [ ] 自选股 200+ 卡顿后再上虚拟列表；当前保留本地搜索/筛选
- [ ] 移动端先保障 Watchlist / StockDetail / Chat 三条核心路径可用，不急于完整复刻

**M25.5 Qlib 灰度（阻塞于 M27）**
- [ ] 只有多个窗口稳定通过 promotion gate 后，才允许小权重灰度（`quant=0.1`）；需配 kill switch 与复盘闭环

**M25.6 社区与战略（P3）**
- [ ] README demo 截图/GIF / release notes / 真实 quickstart 验证路径 / 典型研究案例
- [ ] PostgreSQL / pgvector：SQLite 成为真实瓶颈后再启动
- [ ] HK/US 多市场：A 股主线验证稳定后再做
- [ ] Tauri / 桌面客户端：Web 控制台稳定后再评估
- [ ] WebSocket：止损预警优先复用 scheduler + Bark，有多用户实时需求再引入

---

## M21.4 ATR 窄止损统计分析（触发条件：2026-07-18 后）

- [ ] 在 test1 + test2 全部 `closed` 仓位上统计 `ATR / 买入价` 分布，重点看 ATR 占比 < 0.5% 样本是否系统性触发假止损；如有问题评估：① 加 ATR 下限 `max(ATR×2, 买入价×3%)`；② 改用 trailing ATR×2.5。先出统计报告，不直接改测试 1（规则已冻结）。

---

## M12 外部数据源扩展治理（剩余）⏳

- [ ] 对任何新端点先补 provider health / PIT 时间戳 / 字段归一化 / 测试，再考虑写入 SQLite

---

## M10.5 长期工程基础（后置 / P3）

- [ ] 数据库迁移体系：先保留 `create_all + runtime patch`，中期引入 Alembic baseline
- [ ] 只有多个验证窗口通过后才允许小权重灰度；默认生产继续 `weight_quant=0.0`

---

## M4 多 Agent 决策深化（暂缓项）🟡

- [ ] **M4.4 LangGraph 重构 pipeline**：触发条件：本地验证 ≥ 10 笔样本 + path B Sharpe ≥ path A + 0.3
- [ ] **M4.5 FinMem 完整替换 `decision_memory.py`**：触发条件：≥ 30 笔样本证明"记忆深度 → Sharpe 改善"

---

## M5 自动化执行 🔲（后置，最不关键）

QMT/miniQMT 券商对接；盘中实时止损；半自动→全自动渐进。
**门槛**：本地验证通过 + M3.2 walk-forward 在独立 holdout 上验证通过。

---

## M2 本地验证材料 🏠

本地验证材料、个人记录和临时统计不进入 GitHub。

---

## 里程碑摘要（详情见 CHANGELOG / PROJECT）

| 里程碑 | 完成时间 | 简述 |
|---|---|---|
| M30 | 2026-06-01 主体完成 | 工程质量收敛：mypy、Python lock、CI/安全/覆盖率、核心路径专项测试；安全债与可维护性拆分后置 |
| M29.0–M29.5 | 进行中 | Alpha Reset / Forward Evidence Engine，M29.5 首轮 attribution 已完成，等待完整 fresh forward 覆盖 |
| M27.0–M27.4 | 2026-05-31 | Alpha 根治工程证据闭环，未过 promotion gate，转入 M29 |
| M26.0 量化基线 | 2026-05-30 | 初始 test2 基线归档；后续以 M26.1/M26.2 的生产边界为准 |
| M26.1 训练盘扩容 | 2026-05-30 | 707 支，IC=0.021，仅过 M26 诊断阈值，未过生产 promotion gate |
| M26.2 Kronos 评估 | 2026-05-30 | 零样本 IC=-0.0017，不替换 |
| M25 综合改进主体 | 2026-05-27 | LLM 成本可观测性 / Chat SSE / 跨入口契约回归 |
| M24.0–M24.2 长期标签隔离 | 2026-05-26 | 测试 1/2 冻结期隔离 + 质量门 |
| M23 信号证据链 + 回测口径 | 2026-05-25 | M17.1 / M18.1 / 前端 EvidenceCard |
| M22 持仓完整性与状态隔离 | 2026-05-24 | 持仓 schema 锁定 / agent action 对齐 |
| M21 基础设施评审修复 | 2026-05-23 | 远程写守卫 / model_tier 分层 / runtime-config 校验 |
| M20 量化与分析层评审修复 | 2026-05-23 | RSRS 共线修复 / 涨跌停阈值板块差异 |
| M19 数据层与 PIT 修复 | 2026-05-23 | PIT 用 disclosure_date / 复权口径统一 / Q1/Q3 披露日 |
| M18 回测统计口径修复 | 2026-05-23 | 滑点建模 / Sharpe 年化统一 / DSR trial 语义 |
| M17 决策链评审修复 | 2026-05-23 | regime 不覆盖风控否决 / 证据仓位归属 / 幂等写 |
| M16 全项目分层评审 | 2026-05-23 | 六层评审完成，缺陷转入 M17–M21 |
| M15 记忆系统与影子副驾驶修复 | 2026-05-23 | judgment 去重 / vetter 接线 / 召回副作用降级 |
| M14 股票长期记忆与跨入口召回 | 2026-05-23 | `stock_memory_items` + 统一召回 `build_memory_context` |
| M13 pi Shell + Agent Kernel | 2026-05-23 | `backend/agent/cli.py` / `.pi/` 本地配置 |
| M11 Agent-Ready 本地/远程接口 | 2026-05-21 | AGENTS.md / MCP 工具桥 / PortfolioManager 闭环 |
| M10 运行可靠性与产品化优化 | 2026-05-20 | 覆盖快照 / scheduler 状态 / Bark 重试 / 前端渐进加载 |
| M9 记忆系统接入与治理 | 2026-05-19 | 分层 DB / AdminPage 记忆管理 / 摘要器 / 过期清理 |
| M8 深度研究与来源审计层 | 2026-05-17 | deep_research.py / news_audit / research_memory |
| M6 量化与前端升级 | 2026-05-19 | M6.1 PIT 基本面因子 / M6.3 前端操作台 |
| M7 工程化与开源就绪 | 2026-05-16 | README / CI / Docker / pyproject / Makefile |
| M4 多 Agent（已完成部分） | 2026-05-16 | 多轮辩论 / Director / Portfolio Manager / M4.6–M4.9 |
| M3 可信度审计层 | 2026-05-15 | DSR / PBO / Walk-Forward / PIT 拦截 / Kill Switch |
| M1 严肃化与质量门槛 | 2026-05-15 | Backtrader / regime 过滤 / 长期分析师团 / 双 profile |
| M0 系统骨架 | — | 数据/技术/情感/量化/Web/复盘全链路打通 |

---

## 历史决策点（不再阻塞）

**Qlib 归零**（M1.1）：IC=0.0228，分层非单调 → 权重归零；M26/M27 正在从训练盘广度不足的根因重建。

**跨市场信号（已移除）**：美股 ETF 作为领先指标，全板块回测无显著改善，已移除。
