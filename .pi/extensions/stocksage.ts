import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

type CommandResult = {
  stdout: string;
  stderr: string;
};

function pythonFor(cwd: string): string {
  const venvPython = join(cwd, ".venv", "bin", "python");
  if (existsSync(venvPython)) return venvPython;
  return process.env.PYTHON || "python3";
}

function runStockSage(cwd: string, args: string[], signal?: AbortSignal): Promise<CommandResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(
      pythonFor(cwd),
      ["-m", "backend.agent.cli", ...args],
      {
        cwd,
        env: {
          ...process.env,
          PYTHONPATH: cwd,
          STOCKSAGE_AGENT_MODE: process.env.STOCKSAGE_AGENT_MODE || "local",
        },
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    signal?.addEventListener("abort", () => child.kill("SIGTERM"), { once: true });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
        return;
      }
      reject(new Error(stderr.trim() || `StockSage CLI exited with ${code}`));
    });
  });
}

function textResult(text: string, details: Record<string, unknown> = {}) {
  return {
    content: [{ type: "text" as const, text: text.trim() || "{}" }],
    details,
  };
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "stocksage_health",
    label: "StockSage Health",
    description: "Read StockSage agent health, database counts, watchlist, positions, and memory counts.",
    promptSnippet: "Use stocksage_health before answering StockSage runtime, setup, or health questions.",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params, signal, _onUpdate, ctx) {
      const result = await runStockSage(ctx.cwd, ["health", "--pretty"], signal);
      return textResult(result.stdout, { command: "health" });
    },
  });

  pi.registerTool({
    name: "stocksage_project_context",
    label: "StockSage Project Context",
    description: "Read StockSage startup context, project memory summary, active watchlist, and positions.",
    promptSnippet: "Use stocksage_project_context before project-level StockSage research or review.",
    parameters: Type.Object({
      symbol: Type.Optional(Type.String({ description: "Optional stock symbol to include focused context." })),
    }),
    async execute(_toolCallId, params, signal, _onUpdate, ctx) {
      const args = ["project-context", "--pretty"];
      if (params.symbol) args.push("--symbol", params.symbol);
      const result = await runStockSage(ctx.cwd, args, signal);
      return textResult(result.stdout, { command: "project-context" });
    },
  });

  pi.registerTool({
    name: "stocksage_stock_context",
    label: "StockSage Stock Context",
    description: "Read one stock's latest signal, position, long-term label, copilot shadow opinion, and memory context.",
    promptSnippet: "Use stocksage_stock_context before single-stock StockSage research.",
    parameters: Type.Object({
      symbol: Type.String({ description: "Stock symbol, for example 300308." }),
    }),
    async execute(_toolCallId, params, signal, _onUpdate, ctx) {
      const result = await runStockSage(ctx.cwd, ["stock-context", params.symbol, "--pretty"], signal);
      return textResult(result.stdout, { command: "stock-context", symbol: params.symbol });
    },
  });

  pi.registerTool({
    name: "stocksage_memory_snapshot",
    label: "StockSage Memory Snapshot",
    description: "Read StockSage project-owned memory counts, recent memory rows, layered memory, and audit summaries.",
    promptSnippet: "Use stocksage_memory_snapshot for memory-sensitive StockSage work.",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params, signal, _onUpdate, ctx) {
      const result = await runStockSage(ctx.cwd, ["memory-snapshot", "--pretty"], signal);
      return textResult(result.stdout, { command: "memory-snapshot" });
    },
  });

  pi.registerTool({
    name: "stocksage_action_dry_run",
    label: "StockSage Action Dry Run",
    description: "Inspect a StockSage action schema, risk level, and payload without executing it.",
    promptSnippet: "Use stocksage_action_dry_run before any StockSage mutation.",
    parameters: Type.Object({
      name: Type.String({ description: "Registered action name, for example watchlist.add." }),
      payloadJson: Type.String({ description: "Action payload as a JSON object string." }),
    }),
    async execute(_toolCallId, params, signal, _onUpdate, ctx) {
      const result = await runStockSage(
        ctx.cwd,
        ["action", params.name, "--payload-json", params.payloadJson, "--pretty"],
        signal,
      );
      return textResult(result.stdout, { command: "action", action: params.name, dryRun: true });
    },
  });

  pi.registerTool({
    name: "stocksage_action_confirm",
    label: "StockSage Confirmed Action",
    description: "Execute a confirmed StockSage action. Use only after the user explicitly approves the exact payload.",
    promptSnippet: "Use stocksage_action_confirm only after the user explicitly confirms a StockSage action payload.",
    parameters: Type.Object({
      name: Type.String({ description: "Registered action name." }),
      payloadJson: Type.String({ description: "Action payload as a JSON object string." }),
      confirm: Type.Boolean({ description: "Must be true to execute." }),
    }),
    async execute(_toolCallId, params, signal, _onUpdate, ctx) {
      if (!params.confirm) {
        throw new Error("Set confirm=true only after explicit user approval.");
      }
      if (ctx.hasUI) {
        const ok = await ctx.ui.confirm(
          "Execute StockSage action?",
          `${params.name}\n\n${params.payloadJson}`,
        );
        if (!ok) throw new Error("StockSage action was cancelled by the user.");
      }
      const result = await runStockSage(
        ctx.cwd,
        ["action", params.name, "--payload-json", params.payloadJson, "--confirm", "--pretty"],
        signal,
      );
      return textResult(result.stdout, { command: "action", action: params.name, dryRun: false });
    },
  });

  pi.registerCommand("stocksage-health", {
    description: "Run StockSage health check.",
    handler: async (_args, ctx) => {
      const result = await runStockSage(ctx.cwd, ["health", "--pretty"]);
      ctx.ui.notify(result.stdout.trim(), "info");
    },
  });
}
