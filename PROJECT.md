# StockSage — 进度追踪

> 每次开始工作前先读这个文件，了解当前进度和下一步。

---

## 项目定位

个人 A 股辅助决策工具（美股为后期扩展，不在主线开发范围内）。
量化引擎（Qlib）负责 Alpha 信号，LLM（Claude API）负责个股新闻情感分析，
技术指标作为基础层，三路信号融合后输出建议，用户自行最终决策。

**核心约束：** 止盈止损由 ATR 公式计算，LLM 不做价格预测，不做自动交易。

---

## 任务编号体系（2026-05-15 起生效）

**统一用里程碑 M0–M6 + 子任务 M{X}.{Y}**。所有历史叫法（Phase / 阶段 / Tier / 执行计划）保留为括号别名，避免外部引用断裂，但**新任务一律用 M 编号**。

### 历史叫法映射

| 历史叫法 | 含义 | 归属 |
|---|---|---|
| Phase 0–6 | 系统骨架 8 阶段建设 | **M0** |
| Phase 6.5 | 验证轨 | **M2** |
| Phase 7 | 美股扩展（已降级） | **M6** |
| 执行计划 A | 修复轨（P0/P1/P2 + 数据回填 + 记忆骨架） | **M1.4** |
| 执行计划 B | 结构轨（文件归档 + 文档完善） | **M1.5** |
| 执行计划 C | 规则轨（信号语言 + 仓位 + 退出实验） | **M1.6** |
| 执行计划 D | 验证守护 | **M2** |
| 重构轨阶段 A | 地基重建（backtrader + alphalens） | **M1.1** |
| 重构轨阶段 B | 信号优化（8 方案扫描） | **M1.2** |
| 阶段 C（路线图） | TradingAgents-CN / FinMem 深化 | **M4** |
| 阶段 D（路线图） | QMT 半自动 | **M5** |
| 阶段 E（路线图） | RD-Agent 自动因子 | **M6** |
| Tier 1 | DSR + PBO + IC 显著性 | **M3.1** |
| Tier 2 | Walk-Forward + Holdout | **M3.2** |
| Tier 3 | Point-in-Time as_of 拦截 | **M3.3** |
| Tier 4 | Kill Switch + 健康检查 | **M3.4** |

---

## 系统架构

```
Data Layer:   AkShare（A股行情 + 个股新闻 + 指数）→ SQLite
Analysis:     技术指标 + LLM情感（Haiku）+ Qlib量化（LightGBM）
Decision:     三路信号融合 → 综合建议 + ATR止盈止损
Notify:       Bark iOS 推送（买入信号 + 止损预警）
Dashboard:    FastAPI + React + TradingView Charts
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.11 + FastAPI |
| 前端 | React 18 + Vite + TailwindCSS + TradingView Lightweight Charts |
| 量化 | Microsoft Qlib + LightGBM |
| 数据 | AkShare（A股全覆盖，含行情/新闻/指数/资金流） |
| LLM | Anthropic SDK — Claude Haiku（情感）/ Sonnet（仲裁） |
| DB | SQLite + SQLAlchemy |
| 调度 | APScheduler（BackgroundScheduler，集成进 FastAPI lifespan） |
| 推送 | Bark（iOS 推送，可选） |
| 扩展 | yfinance（美股，M6） |

---

## 终极目标与优先级

> **核心目标**：让系统对炒股产生**建设性意见**——AI 给出经过严肃验证、值得信任的择股+择时+风控建议。
> **自动化执行**（连接券商 API 自动下单）是**最后一步、最不关键**的能力，建议永远保留"半自动+人工确认"作为兜底。
>
> 优先级：建设性意见质量 ＞ 信号 α 验证 ＞ AI 决策能力 ＞ 自动化执行

---

## 里程碑总览

| 里程碑 | 名称 | 状态 | 旧名 |
|---|---|---|---|
| **M0** | 系统骨架 | ✅ 完成 | Phase 0–6 |
| **M1** | 严肃化与质量门槛 | ✅ 完成 | 重构轨阶段 A/B + 执行计划 A/B/C + 长期分析师团 first batch |
| **M2** | 纸上交易验证 | ⏳ 进行中 | Phase 6.5 + 执行计划 D + 测试1/测试2 |
| **M3** | 可信度审计层 | ✅ 完成 | Tier 1–4（DSR/PBO/walk-forward/PIT/kill-switch） |
| **M4** | 多 Agent 决策深化 | 🟡 部分（长期团 + risk_manager 已上线） | 路线图阶段 C |
| **M5** | 自动化执行 | 🔲 后置 | 路线图阶段 D |
| **M6** | 持续迭代与扩展 | 🔲 持续 | 路线图阶段 E + Phase 7 美股 |

---

## M0 系统骨架 ✅（旧 Phase 0–6）

数据/技术/情感/量化/Web/复盘 全链路打通。覆盖 AkShare 数据管道、ATR/RSI/MA 技术因子、Qlib 量化引擎、LLM 新闻情感、信号聚合、FastAPI + React Web 看板、APScheduler 调度。

**M0 收尾项**（旧"历史任务 Phase 6 已完成"段）：
- [x] `backend/data/market.py` — A股/美股拉取加指数退避重试
- [x] `backend/data/news.py` — AkShare 新闻拉取加重试
- [x] `backend/notification/bark.py` — Bark iOS 推送
- [x] `backend/scheduler.py` — 盘后 Bark 推送 + 14:30 止损预警
- [x] `backend/api/routes.py` — `GET /api/signals/eval/{symbol}` 信号胜率统计
- [x] `backend/api/schemas.py` — `SignalEvalOut` / `SignalEvalRecord` schema

---

## M1 严肃化与质量门槛 ✅（旧 重构轨阶段 A/B + 执行计划 A/B/C）

把"自家手搓回测"全部换成业界工具，让回测结果可信；同时修阻断 bug、整理文件结构、固化生产规则。

### M1.1 backtrader + alphalens 迁移（旧"重构轨阶段 A 地基重建"）

**核心交付**：
- [x] 依赖：`backtrader`, `alphalens-reloaded` 已安装
- [x] `backend/backtest/backtrader_eval.py` — Backtrader 严肃回测，支持 `--legacy/--compare/--symbols`
- [x] `backend/backtest/alphalens_qlib.py` — Qlib IC + ICIR + 分层回测
- [x] `backend/analysis/timing/{rsrs,diffusion,regime}.py` — RSRS + 扩散指标 + regime 聚合
- [x] aggregator 集成 regime 过滤层（`regime_filter_enabled` 控制）

**Qlib 有效性硬验证结果**（2020-04 ~ 2026-05，10 只股票面板 12797 行）：
- IC 均值 **+0.0228**（< 阈值 0.03 ❌）
- ICIR **+0.062**（< 阈值 0.3 ❌）
- 分层回测**非单调**（第 3 档高于第 4 档）
- **决策：Qlib 权重归零，融合切换到「技术 60% + 情感 40%」**

> **⚠ M3.1 二阶审计回算**（2026-05-15）：用 `backend/backtest/statistics` 复算，IC=0.0228 在 N=12797 下 t=2.58, p=0.0099（**极显著**）。当时按裸阈值 0.03 判"不合格"忽略了样本量，IC 本身在统计学上是显著的。但分层非单调是独立的、更强的判否证据，最终"Qlib 归零"决策保留。教训：单 IC 阈值不应裸用，需配套显著性。

### M1.2 8 方案参数扫描 + 默认值固化（旧"重构轨阶段 B 信号优化"）

**Legacy vs 试验版并排回测**（2025-11-01 ~ 2026-05-14）：

| 指标 | Legacy(RR=2.0 无trailing 无ADX) | 试验B(RR=1.5 trailing=ON ADX=ON) | 差值 |
|------|-------|-------|-------|
| 总笔数 | 128 | 112 | -16 |
| 总体胜率 | 51.6% | 56.2% | **+4.7%** ✅ |
| 平均净收益 | +14.18% | +12.25% | -1.94% |
| 平均 Sharpe | 0.56 | **0.21** | **-0.34** ❌ |
| 平均最大回撤 | 17.59% | 18.35% | +0.76% |
| 平均盈亏比 | 2.60 | 2.00 | -0.60 |

> 自我回测找到的问题：试验B 初版默认（1:1.5 RR + trailing 1.5×ATR + ADX 过滤）让胜率涨 4.7% 但 Sharpe 大跌。原因：1:1.5 RR 截断大行情；trailing 1.5×ATR 锁利润过早。

**8 方案参数扫描（按 Sharpe 降序）**：

| 方案 | 笔数 | 胜率 | Sharpe | 收益 | 备注 |
|------|------|------|--------|------|------|
| **F: 仅持仓10天** | 85 | 54.1% | **0.72** | +18.5% | 最大单点杠杆 |
| E: 仅RR=1.5 | 128 | 51.6% | 0.60 | +17.1% | 收益高但 Sharpe 一般 |
| D: 仅trailing(2.5×ATR) | 128 | 52.3% | 0.57 | +14.3% | 与基线持平 |
| **A: Legacy 基线** | 128 | 51.6% | 0.56 | +14.2% | 对照组 |
| C: 仅trailing(1.5×ATR) | 138 | 56.5% | 0.53 | +14.1% | trailing 设紧反而拖累 |
| G: ADX+trailing(2.5) | 103 | 50.5% | 0.39 | +10.5% | 双 ADX 叠加恶化 |
| B: 仅ADX 过滤 | 102 | 50.0% | 0.38 | +10.5% | ADX 单独也拖累 |
| H: 试验B 全开 | 112 | 56.2% | 0.21 | +12.3% | 改动叠加灾难 |

**反直觉教训**：
- "超时强平 80%" 的根因是 max_hold 太短，不是 trailing 缺失 — 5→10 天直接 +0.16 Sharpe
- ADX 过滤减少入场但每笔质量未提升 — 在当前股票池上整体拖累
- 多个"改进"叠加 ≠ 改进 — H 方案把每个单点都启用反而 Sharpe 最低
- 改动越少越好 — 当前数据上"做减法"比"做加法"更有效

> **⚠ M3.1 二阶审计回算**（2026-05-15）：8 方案做 multiple-testing 修正：SR_0(N=8)=**0.233**。入选 F 方案 Sharpe=0.72 **跨越**多试验阈值 ✅，结论稳健。但提醒：N=8 是较小的试验数，未来增加扫描次数需同步重算 SR_0。

**最终默认值（已写入 `config.py`）**：
- `weight_quant=0.0`（Qlib 归零），`weight_technical=0.6`，`weight_sentiment=0.4`
- `max_hold_days=10`（5→10 唯一确认提升 Sharpe 的杠杆）
- `risk_reward_ratio=2.0`（保持 1:2）
- `trailing_stop_enabled=False`，`adx_filter_enabled=False`
- `regime_filter_enabled=True`，dampen_factor 从 0.5→0.7

**Legacy vs 新默认 最终对比**：

| 指标 | Legacy | 新默认 | 差值 |
|------|-------|--------|------|
| 总笔数 | 128 | 85 | -43 |
| 总体胜率 | 51.6% | 54.1% | +2.6% ✅ |
| 平均净收益 | +14.18% | **+18.49%** | +4.31% ✅ |
| 平均 Sharpe | 0.56 | **0.72** | +0.16 ✅ |
| 平均最大回撤 | 17.59% | 17.19% | -0.40% ✅ |
| 平均盈亏比 | 2.60 | **3.01** | +0.41 ✅ |

### M1.3 长期分析师团 first batch（2026-05-15 上线）

三个长期分析师（A 老师赛道 + Piotroski 财务质量 + 景气投资 Δ类）+ QFII Outflow 反向规避 已完整实现并集成到生产流水线。

- 模块：`backend/agents/long_term/{a_teacher,piotroski,jingqi,qfii_flow}_analyst.py` + `team.py` + `storage.py`
- 数据层：`backend/data/fundamentals.py` + `backend/data/qfii_holdings.py` + 迁移脚本 + 新表（`financial_metrics` / `long_term_labels` / `stocks.industry`）
- Skills：`~/.claude/skills/{piotroski,jingqi,a-teacher}/SKILL.md`（可命令行单股查询）
- 调度：周日 11:00 自动跑（`job_weekly_longterm`）
- 集成点：`aggregate_v2(long_term_label=...)` + `risk_manager.review(*, long_term_label=...)` + `pipeline` 综合分截断
- Bug 修复：顺手修 `memory_layered.py:174` 的 `complete_text()`

**手工标注回测验证（10 只股 × 6 个月）**：

| 指标 | 无长期标签 | 含长期标签 | 改善 |
|------|----------|-----------|------|
| 总笔数 | 85 | 56 | -29 |
| 总体胜率 | 54.1% | **58.9%** | **+4.8%** ✅ |
| 平均净收益 | +18.5% | +13.5% | -5.0% ⚠️ |
| 平均 Sharpe | 0.72 | **1.36** | **+0.64** 🚀 |
| 平均最大回撤 | 17.19% | **8.60%** | **-8.60%** 🎉 |
| 平均盈亏比 | 3.01 | 2.78 | -0.23 |

**M1 验收标准全部达成**：
- ✅ Sharpe > 0.8（实际 **1.36**）
- ✅ 最大回撤 < 15%（实际 **8.60%**）
- ✅ 盈亏比 ≥ 1.3（实际 **2.78**）

> **⚠ M3.1 二阶审计回算**（2026-05-15）：1.36 vs 0.72 是 N=2 试验对比，SR_0 ≈ 0.235，1.36 跨越多试验阈值 ✅。但样本量小（10 只股 × 6 个月 ≈ 56 笔），DSR 在该样本下置信度有限。**M3.2 walk-forward 落地后**应在独立 OOS 时间窗复算一次再固化为生产参数。

**关键洞察**：
- 招商银行 / 紫金矿业 / 中国神华 标"规避"后**完全无交易**（笔数=0）
- Sharpe 从 0.72 → **1.36 几乎翻倍**，最大回撤从 17% → **8.6% 腰斩**
- 真实运行时长期 label 由 LLM 自动生成（每周日 11:00），不依赖手工标注

**QFII Outflow 反向规避（M1.3 一部分）**：
- 设计思路：决定只做反向（持续撤离 → 规避），不做正向（QFII 新进重仓 → 看好）。正向版的三大噪音根源：披露滞后 30-90 天、北向通道看不到、小盘股偏差
- 数据：AkShare `stock_gdfx_free_top_10_em` 拉前十大流通股东，按 QFII 中文关键词白名单（高盛/摩根士丹利/摩根大通/瑞银/巴克莱/法巴/阿布达比/淡马锡/GIC/挪威银行/汇丰/美林/花旗）过滤
- 触发阈值（settings 可调）：lookback=4 季 / ≥2 家 QFII / 连续 ≥2 季减仓 / 累计减仓占峰值 ≥20%
- 触发 → `label_vote="规避"`，score=-70 → 通过 team 一票否决生效

**首次运行（修复网络代理后）**：
```bash
# 1. 数据回填（5 年财报 + industry）
PYTHONPATH=. python3 -m backend.data.migrations.add_long_term
PYTHONPATH=. python3 -c "
from backend.data.database import SessionLocal, Stock
from backend.data.fundamentals import sync_financial_metrics
db = SessionLocal()
for s in db.query(Stock).filter(Stock.active==True, Stock.market=='CN').all():
    print(s.symbol, sync_financial_metrics(s.symbol, db, years=5))
db.close()
"

# 2. 手动跑一次长期团（验证端到端）
PYTHONPATH=. python3 -c "from backend.scheduler import job_weekly_longterm; job_weekly_longterm()"

# 3. 查看生成的 label
sqlite3 stock-sage.db "SELECT symbol, label, score, expires_at FROM long_term_labels ORDER BY date DESC;"
```

### M1.4 修阻断 bug + 数据回填 + 记忆骨架（旧"执行计划 A 修复轨"）

- [x] RSI 单边上涨/下跌/横盘 NaN 修复，并补单元测试
- [x] 聚合层 composite 遇到 NaN/Inf 回退中性 0
- [x] 仓位计算保留现金，不再因归一化破坏单股上限
- [x] 长期标签缺失时禁强信号，最多降级到"可关注"
- [x] `financial_metrics=200`、`long_term_labels=10`
- [x] `signals.rule_version` / `signals.data_timestamp` 幂等迁移
- [x] `/api/signals/eval/{symbol}` 拆为 long / neutral / short 统计
- [x] `/api/system/status` 返回 DB 路径、数据最新日期、标签状态
- [x] `backend/memory/`、`ai_memory`、`audit_log_fts`、`should_remember()`、迁移脚本和测试

### M1.5 文件结构整理（旧"执行计划 B 结构轨"）

- [x] legacy backtest 已移入 `backend/backtest/legacy/`
- [x] `position_sizer.py` → `backend/portfolio/combo_weights.py`
- [x] `position_sizing.py` → `backend/portfolio/single_position.py`
- [x] `kronos_engine.py` → `backend/analysis/legacy/kronos_engine.py`
- [x] `cross_market.py` → `backend/data/legacy/cross_market.py`
- [x] `STATE_GOVERNANCE.md` 移入 `docs/`
- [x] `PAPER_TRADING.md` 改为索引，测试记录拆到 `paper_trading/`
- [x] 新增 `docs/ARCHITECTURE.md`、`docs/BUGS_FIXED.md`、`docs/MEMORY_DESIGN.md`

### M1.6 信号语言 + 仓位上限 + 退出实验（旧"执行计划 C 规则轨"）

- [x] 信号语言改为：`可小仓试错 / 可关注 / 观望 / 规避`
- [x] 历史信号显示兼容：旧"强买/买入/卖出/强卖"在 API 输出层映射为新语言
- [x] 仓位约束：单股 15%、单板块 30%、总权益 80%、新信号试错仓 5%
- [x] RSI 超买不再直接产生卖出分
- [x] 新增 `backend/backtest/exit_logic_experiment.py` 比较 5 类退出逻辑

### M1.7 测试1/测试2 双 profile 切换系统（2026-05-15）

为支持测试1（旧三路 Qlib 框架）与测试2（新框架 + 多 Agent）并行：

- [x] `backend/config.py` 新增 `SignalWeights` dataclass + `active_signal_weights(as_of)`
- [x] `paper_trading_profile`：`auto` / `test1_legacy_qlib` / `new_framework`，`auto` 时按日期自动判定
- [x] 测试1 配置：quant=0.45 / technical=0.40 / sentiment=0.15，threshold=20，关闭多 Agent
- [x] 测试2/生产配置：quant=0.0 / technical=0.6 / sentiment=0.4，threshold=25，启用多 Agent
- [x] `backend/decision/signal_policy.py` 新建：统一新旧信号语言判断
- [x] `backend/portfolio/trailing_stop.py` 新建：`TrailingStopTracker` + JSON 持久化
- [x] `scheduler.py` 用 `_use_multi_agent_decision()` 二选一调 aggregate vs aggregate_v2
- [x] `notification/bark.send_signal_alert` 按建议输出具体动作（"加入主动观察，不新开仓" vs "次日按规则买入 5.0%"）
- [x] `risk_manager.py` / `trader.py` / `single_position.py` / `aggregator.py` 全部接到新 policy
- [x] 新增 `tests/test_signal_policy.py`（7 用例）和 `tests/test_stage_a_fixes.py`（4 用例）

### M1.8 前端复盘卡片（2026-05-15）

- [x] `frontend/src/api.js` 新增 `getSignalEval(symbol, days)`
- [x] `frontend/src/components/SignalEvalCard.jsx` 新建：胜率/平均次日收益 + 分方向收益 + 信号明细列表 + 30/60/90/180 天窗口切换
- [x] `frontend/src/pages/StockDetailPage.jsx` 接入卡片

### M1 遗留（不阻塞日常使用）

- [ ] TA-Lib 安装并替换 `backend/analysis/factors.py`（历史遗留）

---

## M2 纸上交易验证 ⏳（旧 Phase 6.5 + 执行计划 D + 测试1/测试2）

详细规则与持仓见 `PAPER_TRADING.md` 索引及 `paper_trading/` 拆分文件。

### M2.1 测试 1（用户主导，2026-05-13 ~ 05-20）
宽撒网验证系统完整性。

### M2.2 测试 2（Claude 主导，2026-05-21 ~ 06-03）
精选 7 股，阈值 25，10 个交易日。

### M2.3 测试1 收盘后汇总（2026-05-20）
- [ ] 汇总持仓 / 信号准确率 / 与系统建议的对照

### M2.4 测试2 启动 checklist（2026-05-21）
- [ ] 启动当日执行 checklist（详见 `paper_trading/test2.md`）

> 测试 2 收尾时（约 2026-06-03）会有真实样本可与 M1 严肃回测交叉验证。

---

## M3 可信度审计层 ✅（旧 Tier 1–4）

背景：基于学术框架（Bailey & López de Prado）+ QuantCode-Bench + TradingAgents/FinMem 同期 SOTA 对项目做的专业评测，识别出主要短板集中在"统计严肃性"——能回答"做了什么"但回答不了"做的事能不能信"。M3 补四层工具。

### M3.1 DSR + PBO + IC 显著性（旧 Tier 1）

**模块**：`backend/backtest/statistics/`
- `deflated_sharpe.py` — Bailey & López de Prado 2014 闭式公式，含 SR_0 多试验阈值估计
- `probability_overfitting.py` — CSCV 切分 + IS/OOS 排名 → PBO
- `significance.py` — IC 标准误 / t-stat / 双尾 p
- `tests/test_statistics.py` — 11 用例

**接入点**（不重做扫描，只补统计标签）：
- `exit_logic_experiment.annotate_with_dsr()` — 给每方案补 dsr / dsr_p_value / dsr_threshold
- `backtrader_eval.aggregate()` — 汇总输出加 sr_threshold_multi_trial / sr_passes_multi_trial / avg_sharpe_t_stat

**历史回算结论**（不删原决策，加二阶审计警示，见 M1.1 / M1.2 / M1.3 段内注释）。

### M3.2 Walk-Forward + Holdout（旧 Tier 2）

**模块**：
- `backend/backtest/walk_forward.py` — `generate_windows` / `run_walk_forward` / `holdout_window` / `HOLDOUT_START=2026-01-01`
- `backend/backtest/exit_logic_experiment.py` 重构：`run(as_of_start, as_of_end, db=None)`、`walk_forward_eval()`、`holdout_eval()`
- `tests/test_walk_forward.py` — 7 用例

**设计约定**：
- HOLDOUT_START = 2026-01-01。所有参数决策只能在 in-sample 段做出，holdout 仅做一次
- walk-forward 每窗口先 train 段扫描选 Sharpe 最大方案，再用该方案的 test 段 metrics 入聚合
- 跨窗口聚合输出含 mean / stdev / t_stat_across_windows / multi_window_sr_threshold

### M3.3 Point-in-Time as_of 拦截层（旧 Tier 3）

**模块**：
- `backend/data/point_in_time.py` — `PITSession` 包装 db session，按 model 字段自动加 `<= as_of` 过滤
- `assert_pit_clean()` 审计辅助
- `tests/integration/test_no_look_ahead.py` — 10 用例

**设计取舍**：不修改 ORM 模型本体，PITSession 是显式包装器；主流程裸 SessionLocal 不变。灵感来自 Benhenda 2026 Look-Ahead-Bench。

### M3.4 Kill Switch + 健康检查（旧 Tier 4）

**模块**：
- `backend/ops/kill_switch.py` — 状态文件 `~/.stock-sage/kill_switch.json`，四类自动检查 + 手动触发 + reset
  - 连续 N 笔信号亏损（默认 5）
  - 单日组合回撤 ≥ X%（默认 5%）
  - 数据陈旧：最新价格日距今 > N 天（默认 5）
  - 手动触发
- `backend/scheduler.py` — `_kill_switch_guard()` 在 premarket/postmarket/stoploss_check 入口拦截
- `backend/api/routes.py` — `GET /api/system/health`、`POST /api/system/kill-switch/{trigger,reset}`
- `tests/test_kill_switch.py` — 14 用例

### M3 评级提升预期（与外部评测对照）

| 维度 | 原评级 | 新预期 |
|---|---|---|
| 回测严肃性缺口 | C | A- |
| 统计显著性 | C | A- |
| 数据时间对齐 | B | A |
| 可操作性落地 | B | A- |
| 总评 | B+ ~ A- | A- ~ A |

---

## M4 多 Agent 决策深化 🟡（旧 路线图阶段 C）

**已部分完成**：
- [x] 长期分析师团（M1.3）— 4 路投票 + 一票否决
- [x] `risk_manager.py` — 风险经理对最终建议有否决权
- [x] `memory_layered.py` — FinMem 风格分层记忆

**待做**：
- [ ] fork TradingAgents-CN，做 7 角色多 Agent 决策（researcher 辩论 / trader 仓位 / portfolio manager）
- [ ] FinMem 完整替换 `decision_memory.py`
- [ ] 与 M3.2 walk-forward 配合：多 Agent 路径 vs 单 aggregate 路径并排回测

---

## M5 自动化执行 🔲（旧 路线图阶段 D，最不关键）

QMT/miniQMT 券商对接；盘中实时止损；3 层 kill switch（M3.4 已奠基）；半自动→全自动渐进。

**门槛**：M2 测试 1/2 通过 + M3.2 walk-forward 在独立 holdout 上验证通过。

---

## M6 持续迭代与扩展 🔲（旧 路线图阶段 E + Phase 7 美股）

### M6.1 自动因子挖掘 + 周复盘自动化
- RD-Agent 集成
- Tushare 财报 / 资金流接入

### M6.2 美股扩展（旧 Phase 7，已降级）
- yfinance 接入 / 美股新闻源 / 双市场调度
- 仅在主线稳定后考虑

---

## 调度时间表

| 时间 | 任务 | 说明 |
|------|------|------|
| 08:30 工作日 | 盘前同步 | 行情回填 + 个股新闻抓取 + 沪深 300 指数 |
| 14:30 工作日 | 止损预警 | 检查买入信号止损线，触及则 Bark 推送 |
| 16:00 工作日 | 盘后信号 | 三路信号聚合 → 写 Signal 表 → Bark 推送 |
| 周六 09:00 | 模型重训 | LightGBM Alpha 模型周训练 |
| 周日 11:00 | 长期团 | M1.3 长期分析师团周度 label 生成 |

> **注意**：所有任务跑在 FastAPI 进程内（APScheduler），服务不运行则任务不触发。
> 止损预警比较的是数据库最新收盘价（前一交易日），非实时盘中价格。
> M3.4 kill switch 激活时，premarket / postmarket / stoploss_check 自动跳过。

---

## 信号权重（Decision Layer）

**当前权重**（M1.1 后固化，由 `paper_trading_profile` 切换）：

| Profile | quant | technical | sentiment | entry_threshold | 触发条件 |
|---|---|---|---|---|---|
| `test1_legacy_qlib` | 0.45 | 0.40 | 0.15 | 20 | 测试 1 期间 2026-05-13 ~ 05-20 |
| `new_framework` | 0.0 | 0.6 | 0.4 | 25 | 测试 2 起 / 生产默认 |

情感权重刻意压低：A 股新闻滞后、噪音高，情感以独立卡片形式在 UI 展示，供用户自行判断。

> **跨市场信号（已移除）**：曾测试过用美股 ETF（COPX/GLD/UUP 等）作为有色金属/黄金矿业的领先指标，全板块扩展回测显示大多数板块无显著收益改善，决定移除。回测代码保留在 `backend/backtest/legacy/` 供参考。

综合评分范围：-100（规避）→ +100（可小仓试错）

---

## 止盈止损公式

```
止损价 = 收盘价 - ATR(14) × 2.0
止盈价 = 收盘价 + (收盘价 - 止损价) × 2.0   # 1:2 风险收益比
```

---

## Kronos 集成说明

Kronos 是已归档的可选增强模块（需要 CUDA GPU），默认关闭；当前主流程不再主动调用。

- **当前状态**：代码保留在 `backend/analysis/legacy/kronos_engine.py`，需要恢复接入点后才会影响生产信号
- **作用**：在量化信号层内部，与 Qlib 得分混合（Kronos 占 40%，Qlib 占 60%）
- **额外能力**：预测未来 5 日 OHLCV 方向 / 预测高波动时扩大止损 / 预测支撑阻力价位透传前端
- **无 GPU**：模块静默跳过，主流程不受影响

---

## 验证结果（2026-05-15 最新）

- 后端测试：`PYTHONPATH=. pytest -q` → **99 passed**（较初版 +58）
- Python 编译：`python3 -m compileall backend tests` → 通过
- 前端构建：`npm run build` → 通过（47 modules，bundle 347 KB / gzip 111 KB）
- `/api/system/status` → DB 存在，最新价格日期 `2026-05-15`，`financial_metrics=200`，`long_term_labels=10`
- `/api/system/health` → 健康（M3.4 新增）

---

## 环境准备（首次运行前）

```bash
cp .env.example .env                  # 填入 ANTHROPIC_API_KEY（必填）和 BARK_KEY（可选）
pip install -r backend/requirements.txt
python3 backend/data/database.py      # 初始化 DB
cd frontend && npm install
```

### 启动服务

```bash
cd /path/to/stock-sage
PYTHONPATH=. uvicorn backend.main:app --reload
# 前端
cd frontend && npm run dev
```

### 模型训练 / API 触发

```bash
PYTHONPATH=. python3 -m backend.analysis.qlib_engine --train
PYTHONPATH=. python3 -m backend.backtest.walk_forward --start 2024-01-01 --end 2026-05-15
PYTHONPATH=. python3 -m backend.backtest.walk_forward --mode holdout --start 2026-01-01 --end 2026-05-15 --strategy fixed_10d
curl -X POST http://localhost:8000/api/model/train
curl http://localhost:8000/api/model/status
curl http://localhost:8000/api/signals/eval/600519?days=60
curl http://localhost:8000/api/system/health             # M3.4
curl -X POST http://localhost:8000/api/system/kill-switch/reset  # M3.4
```

---

## 关键文件索引

```
backend/config.py                            配置入口（环境变量、路径、调度时间、Bark、双 profile）
backend/data/database.py                     数据库模型 + 轻量幂等迁移
backend/data/market.py                       行情数据拉取（AkShare A 股为主，含重试）
backend/data/news.py                         新闻抓取（stock_news_em，含重试）
backend/data/fundamentals.py                 财务指标（M1.3）
backend/data/qfii_holdings.py                QFII 前十大流通股东（M1.3）
backend/data/point_in_time.py                PIT as_of 拦截层（M3.3）
backend/analysis/factors.py                  技术因子计算
backend/analysis/qlib_engine.py              Qlib 量化引擎
backend/analysis/technical.py                技术信号生成
backend/analysis/sentiment.py                LLM 新闻情感分析
backend/analysis/timing/{rsrs,diffusion,regime}.py  regime 过滤层（M1.1）
backend/analysis/legacy/kronos_engine.py     Kronos 预测模块（可选，需 GPU，已归档）
backend/decision/aggregator.py               多信号聚合 → 最终建议
backend/decision/decision_memory.py          历史决策记忆 + 反思上下文注入
backend/decision/memory_layered.py           FinMem 风格分层记忆（M4 前置）
backend/decision/signal_policy.py            信号语言统一（M1.7）
backend/memory/                              ai_memory + audit_log_fts 记忆接口
backend/notification/bark.py                 Bark iOS 推送
backend/api/routes.py                        REST API 路由（含 M3.4 health/kill-switch）
backend/api/schemas.py                       Pydantic response schemas
backend/main.py                              FastAPI 应用入口
backend/scheduler.py                         定时任务（盘前/盘中/盘后/周训练 + M3.4 guard）
backend/agents/long_term/                    长期分析师团（M1.3）
backend/agents/pipeline.py                   多 Agent 决策流水线（M4 前置）
backend/agents/risk_manager.py               风险经理（M4 前置）
backend/backtest/                            严肃回测与实验脚本（legacy 在 backend/backtest/legacy）
backend/backtest/statistics/                 DSR / PBO / IC 显著性（M3.1）
backend/backtest/walk_forward.py             walk-forward harness（M3.2）
backend/portfolio/combo_weights.py           组合候选权重分配
backend/portfolio/single_position.py         单信号仓位映射
backend/portfolio/trailing_stop.py           Trailing stop 持仓追踪（M1.7）
backend/ops/kill_switch.py                   Kill switch（M3.4）
frontend/src/pages/                          页面组件
frontend/src/components/SignalEvalCard.jsx   信号复盘卡片（M1.8）
```

---

## 历史决策点（不再阻塞，仅记录）

**Qlib 命运决策**（M1.1 收尾）：
- Alphalens IC > 0.03 → Qlib 保留并接 RD-Agent 升级（进入 M6.1）
- IC < 0.02 → Qlib 权重归零，融合切到「技术 60% + 情感 40%」
- 实际结果：IC=0.0228，分层非单调 → Qlib 归零（详见 M1.1 二阶审计回算）

**M1 验收标准**：

| 指标 | 最低标准 | 实际 |
|------|---------|---|
| 含 0.20% 手续费 + 0.10% 滑点的净 Sharpe（10 只股票池） | > 0.8 | **1.36** ✅ |
| 最大回撤 | < 15% | **8.60%** ✅ |
| 净盈亏比 | ≥ 1.3 | **2.78** ✅ |
| Qlib IC（Alphalens） | 给出明确数值并据此决定权重 | 0.0228，权重归零 ✅ |
