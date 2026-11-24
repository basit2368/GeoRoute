"use client";

import {
  Binary,
  Boxes,
  GitBranch,
  Layers3,
  Network,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Panel } from "./ui";

const ALGORITHMS = [
  {
    icon: <Binary className="h-5 w-5 text-amber-400" />,
    name: "Closest pair — brute force",
    complexity: "O(n²) time · O(1) auxiliary space",
    detail:
      "Evaluates every unordered point pair. Serves as the correctness baseline for the planar divide-and-conquer implementation.",
  },
  {
    icon: <GitBranch className="h-5 w-5 text-sky-400" />,
    name: "Closest pair — divide & conquer",
    complexity: "O(n log n) time · O(n) space",
    detail:
      "Sorts by x, recurses on halves, merges y-order, then checks a bounded vertical strip. Runs on UTM zone 42N projected coordinates.",
  },
  {
    icon: <Network className="h-5 w-5 text-emerald-400" />,
    name: "Exact TSP",
    complexity: "O(n · n!) time",
    detail:
      "Enumerates permutations with the depot fixed. Restricted to small instances; an input guard prevents impractical searches.",
  },
  {
    icon: <Sparkles className="h-5 w-5 text-violet-400" />,
    name: "Nearest neighbour + 2-Opt",
    complexity: "O(n²) · optional local search",
    detail:
      "Greedy tour construction followed by an optional edge-reversal improvement. Heuristic results are never labelled globally optimal.",
  },
];

export default function DocsPanel() {
  return (
    <div className="space-y-6">
      <Panel
        title="Algorithm reference"
        subtitle="The four implementations behind every experiment in this platform."
        icon={<Layers3 className="h-4 w-4 text-brand-400" />}
      >
        <div className="grid gap-3 md:grid-cols-2">
          {ALGORITHMS.map((item) => (
            <div key={item.name} className="rounded-xl border border-white/10 bg-ink-950/50 p-4">
              <div className="flex items-center gap-3">
                {item.icon}
                <div>
                  <h3 className="text-sm font-semibold text-slate-100">{item.name}</h3>
                  <p className="mt-0.5 font-mono text-[10px] text-slate-500">{item.complexity}</p>
                </div>
              </div>
              <p className="mt-3 text-xs leading-relaxed text-slate-400">{item.detail}</p>
            </div>
          ))}
        </div>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title="System architecture"
          subtitle="Modular client–server design with a native algorithm engine."
          icon={<Boxes className="h-4 w-4 text-brand-400" />}
        >
          <ol className="space-y-3 text-xs text-slate-400">
            {[
              "Next.js + TypeScript dashboard with Leaflet and Recharts",
              "FastAPI validates requests and prepares coordinate/matrix inputs",
              "C++17 engine runs algorithms via ctypes with high-resolution timers",
              "OSRM-compatible service supplies road matrices and route geometry",
            ].map((step, index) => (
              <li key={step} className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-500/15 font-mono text-[10px] text-brand-300">
                  {index + 1}
                </span>
                <span className="pt-1">{step}</span>
              </li>
            ))}
          </ol>
        </Panel>

        <Panel
          title="Measurement integrity"
          subtitle="How benchmarks stay comparable and honest."
          icon={<ShieldCheck className="h-4 w-4 text-emerald-400" />}
        >
          <ul className="space-y-2.5 text-xs leading-relaxed text-slate-400">
            <li>• Identical generated datasets and matrices for every compared algorithm.</li>
            <li>• Timers start after projection/matrix preparation; network calls are excluded.</li>
            <li>• Operation counters record distance evaluations and primitive comparisons.</li>
            <li>• Optimality gap is shown only when an exact cost exists for the same matrix.</li>
            <li>• Road failures are surfaced explicitly; straight-line distance is never a silent fallback.</li>
          </ul>
        </Panel>
      </div>

      <Panel
        title="About this project"
        subtitle="CS2009 — Design and Analysis of Algorithms · FAST National University"
        icon={<Sparkles className="h-4 w-4 text-brand-400" />}
      >
        <div className="grid gap-4 text-xs text-slate-400 sm:grid-cols-2">
          <div className="rounded-xl border border-white/10 bg-ink-950/50 p-4">
            <p className="font-semibold text-slate-200">Abdul Basit · k22-6000</p>
            <p className="mt-1.5 leading-relaxed">
              Project coordination, algorithm design, benchmark methodology, system integration and
              technical documentation.
            </p>
          </div>
          <div className="rounded-xl border border-white/10 bg-ink-950/50 p-4">
            <p className="font-semibold text-slate-200">Hamza Waqar · k22-5140</p>
            <p className="mt-1.5 leading-relaxed">
              Algorithm implementation and testing, frontend/backend development, map integration,
              visualization and documentation.
            </p>
          </div>
        </div>
        <p className="mt-4 text-[10px] leading-relaxed text-slate-500">
          Map and routing data © OpenStreetMap contributors, available under the Open Database
          License. Routing services are provided by OSRM-compatible endpoints subject to their
          usage policies.
        </p>
      </Panel>
    </div>
  );
}
