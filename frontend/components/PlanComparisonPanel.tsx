"use client";

import { usePlanComparison, CostResult } from "@/hooks/usePlanComparison";

const PLAN_LABELS: Record<string, string> = {
  "bronze-2024": "HMO Bronze",
  "silver-2024": "PPO Silver",
  "gold-2024": "HDHP Gold",
  "platinum-2024": "EPO Platinum",
};

function fmt(n: number) {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === "connected" ? "bg-green-500" :
    status === "connecting" ? "bg-yellow-400 animate-pulse" :
    status === "error" ? "bg-red-500" : "bg-zinc-500";
  return <span className={`inline-block w-2 h-2 rounded-full ${color} mr-2`} />;
}

function PlanCard({ plan, rank, isTrap }: { plan: CostResult; rank: number; isTrap: boolean }) {
  const label = PLAN_LABELS[plan.plan_id] ?? plan.plan_id;

  return (
    <div className={`rounded-lg border p-4 ${isTrap ? "border-red-500 bg-red-950/30" : "border-zinc-700 bg-zinc-900"}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-zinc-400">#{rank}</span>
          <span className="font-semibold text-white">{label}</span>
          {isTrap && (
            <span className="text-xs bg-red-600 text-white px-2 py-0.5 rounded-full font-bold">
              ⚠ TRAP
            </span>
          )}
        </div>
        <span className={`text-lg font-bold font-mono ${isTrap ? "text-red-400" : "text-emerald-400"}`}>
          {fmt(plan.annual_total)}/yr
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs text-zinc-400 mt-3">
        <div>
          <div className="text-zinc-500 uppercase tracking-wide mb-0.5">Premium</div>
          <div className="text-zinc-200 font-mono">{fmt(plan.annual_premium)}</div>
        </div>
        <div>
          <div className="text-zinc-500 uppercase tracking-wide mb-0.5">Covered OOP</div>
          <div className="text-zinc-200 font-mono">{fmt(plan.capped_covered_oop)}</div>
        </div>
        <div>
          <div className="text-zinc-500 uppercase tracking-wide mb-0.5">Uncovered</div>
          <div className={`font-mono font-bold ${plan.uncovered_costs > 0 ? "text-red-400" : "text-zinc-200"}`}>
            {fmt(plan.uncovered_costs)}
          </div>
        </div>
      </div>

      {plan.uncovered_drugs.length > 0 && (
        <div className="mt-2 text-xs text-red-400">
          Not covered: {plan.uncovered_drugs.join(", ")}
        </div>
      )}
      {plan.out_of_network_providers.length > 0 && (
        <div className="mt-1 text-xs text-yellow-400">
          Out-of-network: {plan.out_of_network_providers.join(", ")}
        </div>
      )}
      {plan.sources.length > 0 && (
        <div className="mt-2 text-xs text-zinc-600 truncate">
          Source: {plan.sources[0]}
        </div>
      )}
    </div>
  );
}

export default function PlanComparisonPanel() {
  const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL ?? "";
  const { status, comparison, totalLookups } = usePlanComparison(livekitUrl);

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-6 font-sans">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Amparo AI</h1>
            <p className="text-sm text-zinc-400 mt-0.5">Live Coverage Comparison</p>
          </div>
          <div className="text-right">
            <div className="flex items-center justify-end text-sm text-zinc-300">
              <StatusDot status={status} />
              <span className="capitalize">{status}</span>
            </div>
            <div className="text-xs text-zinc-500 mt-0.5">room: amparo-demo</div>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800">
          <div className="text-xs text-zinc-500 uppercase tracking-wide">Moss Lookups</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            {comparison?.lookup_count ?? 0}
          </div>
          <div className="text-xs text-zinc-600">this turn</div>
        </div>
        <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800">
          <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Lookups</div>
          <div className="text-2xl font-bold font-mono text-blue-400 mt-1">
            {totalLookups}
          </div>
          <div className="text-xs text-zinc-600">this session</div>
        </div>
        <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800">
          <div className="text-xs text-zinc-500 uppercase tracking-wide">Plans Compared</div>
          <div className="text-2xl font-bold font-mono text-purple-400 mt-1">
            {comparison?.plans.length ?? 0}
          </div>
          <div className="text-xs text-zinc-600">in parallel</div>
        </div>
      </div>

      {/* Trap warning banner */}
      {comparison?.trap && (
        <div className="mb-4 rounded-lg bg-red-900/40 border border-red-700 px-4 py-3 flex items-center gap-3">
          <span className="text-red-400 text-lg">⚠</span>
          <div>
            <div className="font-semibold text-red-300 text-sm">Cheap-Plan Trap Detected</div>
            <div className="text-xs text-red-400 mt-0.5">
              {PLAN_LABELS[comparison.trap_plan_id ?? ""] ?? comparison.trap_plan_id} has uncovered specialty drug costs
              NOT capped by the OOP maximum — this plan could cost tens of thousands more than it appears.
            </div>
          </div>
        </div>
      )}

      {/* Plan cards */}
      {comparison ? (
        <div className="space-y-3">
          <div className="text-xs text-zinc-500 uppercase tracking-wide mb-2">
            Ranked by annual cost — cheapest first
          </div>
          {comparison.plans.map((plan, i) => (
            <PlanCard
              key={plan.plan_id}
              plan={plan}
              rank={i + 1}
              isTrap={plan.trap_flag}
            />
          ))}
          <div className="text-xs text-zinc-600 text-right mt-2">
            Updated {new Date(comparison.timestamp * 1000).toLocaleTimeString()}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="text-4xl mb-4">📞</div>
          <div className="text-zinc-400 text-lg font-medium">Waiting for a call…</div>
          <div className="text-zinc-600 text-sm mt-2">
            Call <span className="text-white font-mono">+1 (415) 417-6002</span> and ask about your health plans
          </div>
          <div className="text-zinc-700 text-xs mt-4">
            {status === "connected"
              ? "Connected to amparo-demo — panel will update live"
              : status === "connecting"
              ? "Connecting to LiveKit room…"
              : status === "error"
              ? "Connection error — check LiveKit credentials"
              : "Initializing…"}
          </div>
        </div>
      )}
    </div>
  );
}
