import { LABEL } from './adminPageConstants'

const INSET = 'rounded-sm border border-stone-300 bg-[#f3eddc] dark:border-slate-700 dark:bg-[#161b25]'

export function SettingRow({ label, hint, children, danger = false }) {
  return (
    <div className="grid gap-4 border-b border-stone-300 py-4 last:border-b-0 dark:border-slate-700 md:grid-cols-[1fr_auto] md:items-center">
      <div>
        <div className={`text-sm font-medium ${danger ? 'text-emerald-700 dark:text-emerald-200' : 'text-stone-950 dark:text-slate-100'}`}>
          {label}
        </div>
        <div className="mt-1 text-xs leading-relaxed text-stone-500 dark:text-slate-400">{hint}</div>
      </div>
      <div className="flex justify-start md:justify-end">{children}</div>
    </div>
  )
}

export function Toggle({ value, onChange, danger = false }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={`relative h-7 w-14 rounded-full border transition-colors ${
        value
          ? danger
            ? 'border-emerald-600 bg-emerald-600'
            : 'border-cyan-700 bg-cyan-700'
          : 'border-stone-300 bg-[#efe9dc] dark:border-slate-700 dark:bg-slate-900'
      }`}
    >
      <span
        className={`absolute left-1 top-1 h-5 w-5 rounded-full bg-[#faf6ec] transition-transform dark:bg-slate-100 ${
          value ? 'translate-x-7' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

export function ActionButton({ children, onClick, disabled = false, danger = false, type = 'button' }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-sm border px-3 py-1.5 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-50 ${
        danger
          ? 'border-emerald-600/40 bg-emerald-600/10 text-emerald-700 hover:border-emerald-700 dark:text-emerald-200 dark:hover:border-emerald-300'
          : 'border-stone-300 bg-[#f3eddc] text-stone-700 hover:border-cyan-700 hover:text-cyan-700 dark:border-slate-700 dark:bg-[#161b25] dark:text-slate-300 dark:hover:border-cyan-400 dark:hover:text-cyan-200'
      }`}
    >
      {children}
    </button>
  )
}

export function Slider({ value, min, max, onChange, suffix = '' }) {
  const pct = ((value - min) / (max - min)) * 100
  return (
    <div className="flex min-w-[260px] items-center gap-4">
      <div className="relative h-5 flex-1">
        <div className="absolute left-0 right-0 top-2 h-1 rounded bg-stone-300 dark:bg-slate-800" />
        <div className="absolute left-0 top-2 h-1 rounded bg-cyan-700 dark:bg-cyan-400" style={{ width: `${pct}%` }} />
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 h-5 w-full cursor-pointer opacity-0"
        />
      </div>
      <span className="min-w-12 text-right font-mono text-sm font-semibold text-stone-950 dark:text-slate-100">
        {value}{suffix}
      </span>
    </div>
  )
}

export function NumberInput({ value, onChange, min = 0, max, step = 1, suffix = '' }) {
  return (
    <label className="inline-flex w-fit flex-nowrap items-center gap-2">
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-24 rounded-sm border border-stone-300 bg-[#fffaf0] px-3 py-2 font-mono text-sm outline-none focus:border-cyan-700 dark:border-slate-700 dark:bg-[#161b25] dark:text-slate-100 sm:w-28"
      />
      {suffix && <span className="whitespace-nowrap text-xs text-stone-500 dark:text-slate-400">{suffix}</span>}
    </label>
  )
}

export function TimeInput({ value, onChange }) {
  return (
    <input
      type="time"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-sm border border-stone-300 bg-[#fffaf0] px-3 py-2 font-mono text-sm outline-none focus:border-cyan-700 dark:border-slate-700 dark:bg-[#161b25] dark:text-slate-100"
    />
  )
}

const DOW_OPTIONS = [
  ['mon', '周一'],
  ['tue', '周二'],
  ['wed', '周三'],
  ['thu', '周四'],
  ['fri', '周五'],
  ['sat', '周六'],
  ['sun', '周日'],
]

export function DayInput({ value, onChange }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-sm border border-stone-300 bg-[#fffaf0] px-3 py-2 text-sm outline-none focus:border-cyan-700 dark:border-slate-700 dark:bg-[#161b25] dark:text-slate-100"
    >
      {DOW_OPTIONS.map(([id, label]) => (
        <option key={id} value={id}>{label}</option>
      ))}
    </select>
  )
}

export function Segmented({ value, options, onChange }) {
  return (
    <div className="inline-flex overflow-hidden rounded-sm border border-stone-300 dark:border-slate-700">
      {options.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={`border-l border-stone-300 px-3 py-1.5 text-xs font-semibold first:border-l-0 dark:border-slate-700 ${
            value === option
              ? 'bg-cyan-700 text-white dark:bg-cyan-400 dark:text-slate-950'
              : 'bg-transparent text-stone-500 dark:text-slate-400'
          }`}
        >
          {option}
        </button>
      ))}
    </div>
  )
}

export function SchedulerState({ state }) {
  const jobs = Object.values(state?.jobs || {})
  return (
    <div className="min-w-[320px] space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="text-stone-500 dark:text-slate-400">scheduler</span>
        <span className={`rounded-sm border px-2 py-0.5 font-semibold ${state?.running ? 'border-cyan-600/30 bg-cyan-600/10 text-cyan-700 dark:text-cyan-200' : 'border-amber-500/35 bg-amber-500/10 text-amber-700 dark:text-amber-200'}`}>
          {state?.running ? '运行中' : '未运行'}
        </span>
      </div>
      {jobs.length === 0 ? (
        <div className="text-xs text-stone-500 dark:text-slate-400">暂无任务运行记录</div>
      ) : jobs.slice(0, 8).map((job) => (
        <div key={job.job} className="rounded-sm border border-stone-300 bg-[#fffaf0] p-2 text-xs dark:border-slate-700 dark:bg-[#161b25]">
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-stone-950 dark:text-slate-100">{job.job}</span>
            <span className="font-semibold text-stone-600 dark:text-slate-300">{job.last_status}</span>
          </div>
          <div className="mt-1 truncate text-stone-500 dark:text-slate-400">
            {job.last_finished_at || job.last_started_at || 'never run'}
            {job.last_error ? ` · ${job.last_error}` : ''}
          </div>
        </div>
      ))}
    </div>
  )
}

export function Weights({ weights }) {
  const rows = [
    ['量化', weights.quant, 'bg-cyan-700 dark:bg-cyan-400'],
    ['技术', weights.technical, 'bg-red-600'],
    ['情感', weights.sentiment, 'bg-amber-600'],
  ]
  return (
    <div className="w-[320px]">
      <div className="flex h-2 overflow-hidden rounded bg-stone-300 dark:bg-slate-800">
        {rows.map(([label, value, cls]) => (
          <div key={label} className={cls} style={{ width: `${value * 100}%` }} />
        ))}
      </div>
      <div className="mt-3 grid grid-cols-3 gap-3">
        {rows.map(([label, value, cls]) => (
          <div key={label}>
            <div className="flex items-center gap-1.5 text-xs text-stone-500 dark:text-slate-400">
              <span className={`h-2 w-2 rounded-sm ${cls}`} />
              {label}
            </div>
            <div className="mt-1 font-mono text-sm font-semibold text-stone-950 dark:text-slate-100">
              {(value * 100).toFixed(0)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const INIT_STEPS = [
  ['prices', '价格'],
  ['financials', '财报'],
  ['disclosure', '披露日'],
  ['signals', '信号'],
  ['done', '完成'],
]

export function InitStepBar({ step }) {
  const activeIdx = INIT_STEPS.findIndex(([id]) => id === step)
  const isError = step === 'error'
  return (
    <div className="flex items-center gap-1">
      {INIT_STEPS.map(([id, label], i) => {
        const done = !isError && i < activeIdx
        const active = !isError && i === activeIdx
        return (
          <div key={id} className="flex flex-1 flex-col items-center gap-1">
            <div className={`h-1.5 w-full rounded-full ${
              isError && i === activeIdx - 1
                ? 'bg-red-500'
                : done || active
                  ? 'bg-cyan-600 dark:bg-cyan-400'
                  : 'bg-stone-300 dark:bg-slate-700'
            }`} />
            <span className={`text-[9px] font-semibold ${
              active ? 'text-cyan-700 dark:text-cyan-300' : done ? 'text-stone-500 dark:text-slate-400' : 'text-stone-300 dark:text-slate-600'
            }`}>{label}</span>
          </div>
        )
      })}
    </div>
  )
}

export function DiffRow({ path, before, after }) {
  return (
    <div>
      <div className="font-mono text-[11px] text-stone-500 dark:text-slate-400">{path}</div>
      <div className="mt-1 flex items-center gap-2 font-mono text-sm">
        <span className="text-stone-400 line-through decoration-emerald-600 dark:text-slate-500">{String(before)}</span>
        <span className="text-stone-500 dark:text-slate-500">→</span>
        <span className="font-semibold text-red-700 dark:text-red-200">{String(after)}</span>
      </div>
    </div>
  )
}

export function MiniStat({ label, value }) {
  return (
    <div className={INSET}>
      <div className="p-3">
        <div className={LABEL}>{label}</div>
        <div className="mt-1 font-mono text-xl font-semibold text-stone-950 dark:text-slate-100">{value}</div>
      </div>
    </div>
  )
}
