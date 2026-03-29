"use client";

import { useEffect, useState } from "react";
import { TicketResponse } from "../lib/types";

type AgentTracePanelProps = {
  ticketResponse: TicketResponse | null;
  isLoading: boolean;
};

const AGENT_DESCRIPTIONS: Record<string, string> = {
  billing_agent: "Looked up invoices and resolved billing dispute",
  technical_agent: "Searched knowledge base and diagnosed issue",
  account_agent: "Checked account details and processed request",
  escalation_agent: "Escalated to human queue with full context",
  synthesis_agent: "Merged agent responses into final reply",
  triage_agent: "Classified ticket intent and determined routing",
};

function agentDotColor(name: string): string {
  if (name === "triage_agent") return "bg-purple-500";
  if (name === "escalation_agent") return "bg-orange-500";
  if (name === "synthesis_agent") return "bg-emerald-500";
  return "bg-blue-500";
}

function formatAgentName(name: string): string {
  return name
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function SkeletonCard() {
  return (
    <div className="animate-pulse flex items-start gap-3">
      <div className="flex flex-col items-center mt-1">
        <div className="w-3 h-3 rounded-full bg-zinc-700" />
        <div className="w-px h-16 bg-zinc-800 mt-1" />
      </div>
      <div className="flex-1 bg-zinc-800 h-24 rounded-lg" />
    </div>
  );
}

export default function AgentTracePanel({ ticketResponse, isLoading }: AgentTracePanelProps) {
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    if (!ticketResponse) {
      setVisibleCount(0);
      return;
    }
    setVisibleCount(0);
    const agents = ticketResponse.agents_used;
    agents.forEach((_, i) => {
      setTimeout(() => setVisibleCount(i + 1), i * 150);
    });
  }, [ticketResponse]);

  return (
    <div className="flex flex-col h-full bg-zinc-900/60 backdrop-blur-sm border-r border-zinc-800">
      {/* Header */}
      <div className="px-5 py-4 border-b border-zinc-800 flex-shrink-0">
        <h2 className="text-white font-semibold text-base">Agent Trace</h2>
        <p className="text-zinc-400 text-sm mt-0.5">Multi-agent workflow</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 scrollbar-thin scrollbar-track-zinc-900 scrollbar-thumb-zinc-700">
        {isLoading ? (
          <div className="space-y-2">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : !ticketResponse ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-zinc-500 text-sm text-center">
              Submit a ticket to see the agent trace
            </p>
          </div>
        ) : (
          <div className="space-y-0">
            {ticketResponse.agents_used.map((agent, i) => (
              <div
                key={`${agent}-${i}`}
                className="flex items-start gap-3"
                style={{
                  opacity: visibleCount > i ? 1 : 0,
                  transform: visibleCount > i ? "translateX(0)" : "translateX(8px)",
                  transition: "opacity 300ms ease, transform 300ms ease",
                }}
              >
                {/* Timeline line + dot */}
                <div className="flex flex-col items-center flex-shrink-0 mt-3">
                  <div className={`w-3 h-3 rounded-full ${agentDotColor(agent)}`} />
                  {i < ticketResponse.agents_used.length - 1 && (
                    <div className="w-px flex-1 bg-zinc-700 min-h-[2.5rem]" />
                  )}
                </div>

                {/* Card */}
                <div className="flex-1 bg-zinc-800/50 border border-zinc-700/50 rounded-lg px-3 py-2.5 mb-2">
                  <p className="text-zinc-100 text-sm font-medium">
                    {formatAgentName(agent)}
                  </p>
                  <p className="text-zinc-400 text-xs mt-0.5">
                    {AGENT_DESCRIPTIONS[agent] ?? "Processed request"}
                  </p>
                </div>
              </div>
            ))}

            {/* Footer */}
            <p className="text-zinc-500 text-xs mt-3 pl-6">
              Resolved in {ticketResponse.resolution_time_ms}ms
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
