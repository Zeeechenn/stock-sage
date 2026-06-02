export const PANEL = 'rounded-sm border border-stone-300 bg-[#faf6ec] dark:border-slate-700 dark:bg-[#1d232e]'
export const LABEL = 'text-[10px] font-semibold uppercase tracking-[0.2em] text-stone-500 dark:text-slate-400'

export const SECTIONS = [
  ['decision', '决策引擎', '阈值 / 权重'],
  ['portfolio', '组合规则', '仓位 / 出场'],
  ['agents', 'LLM 与 Agent', '辩论 / 记忆'],
  ['data', '数据源', '价格 / 新闻'],
  ['schedule', '调度', 'A 股日历'],
  ['risk', '熔断开关', '风控保护'],
  ['memory', '记忆管理', '元数据 / 召回日志'],
  ['llmcost', 'LLM 成本', '7 天用量'],
]

export const SECTION_COPY = {
  decision: ['01 · 决策引擎', '规则草稿', '控制综合分如何计算，以及哪些信号可以进入可小仓试错。'],
  portfolio: ['02 · 组合规则', '仓位草稿', '集中展示仓位、止损止盈和退出保护的后端参数。'],
  agents: ['03 · LLM 与 Agent', '辩论草稿', '控制多空辩论、仲裁置信度和记忆读取边界。'],
  data: ['04 · 数据源', '数据草稿', '检查价格、财报、新闻覆盖率，并保留本地优先的数据源策略。'],
  schedule: ['05 · 调度', '日历草稿', '展示 A 股交易日相关的盘前、盘后、止损检查调度入口。'],
  risk: ['06 · 熔断开关', '风控草稿', '集中管理会阻断调度或跳过交易建议的保护性开关。'],
  memory: ['07 · 记忆管理', '受控编辑', '查看活跃记忆 / 删除固定 / 改 TTL / 召回审计日志（M9.2）。'],
  llmcost: ['08 · LLM 成本', '7 天滚动', '每次 LLM 调用的 token 估算和 CNY 成本，按 bucket 分桶。'],
}
