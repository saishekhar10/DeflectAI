"use client";

import { useEffect, useState } from "react";
import { getQueue, resolveTicket } from "../lib/api";
import { HumanQueueItem } from "../lib/types";

const PRIORITY_ORDER: Record<HumanQueueItem["priority"], number> = {
  high: 0,
  medium: 1,
  low: 2,
};

function relativeTime(isoString: string): string {
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diff < 10) return "just now";
  if (diff < 60) return `${diff} seconds ago`;
  const mins = Math.floor(diff / 60);
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function priorityBorder(p: HumanQueueItem["priority"]) {
  if (p === "high") return "border-l-red-500";
  if (p === "medium") return "border-l-yellow-500";
  return "border-l-zinc-600";
}

function priorityBadge(p: HumanQueueItem["priority"]) {
  if (p === "high") return "bg-red-900 text-red-300";
  if (p === "medium") return "bg-yellow-900 text-yellow-300";
  return "bg-zinc-700 text-zinc-300";
}

function SkeletonCard() {
  return (
    <div className="animate-pulse bg-zinc-800 h-24 rounded-lg border border-zinc-700/50" />
  );
}

export default function HumanQueuePanel() {
  const [queue, setQueue] = useState<HumanQueueItem[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  async function fetchQueue() {
    try {
      const data = await getQueue();
      setQueue(
        [...data].sort(
          (a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]
        )
      );
      setFetchError(false);
    } catch {
      setFetchError(true);
    }
  }

  useEffect(() => {
    console.log("[HumanQueuePanel] NEXT_PUBLIC_API_URL:", process.env.NEXT_PUBLIC_API_URL);
    fetchQueue().finally(() => setInitialLoading(false));
    const interval = setInterval(fetchQueue, 10000);
    return () => clearInterval(interval);
  }, []);

  async function handleResolve(ticketId: string) {
    setResolvingId(ticketId);
    try {
      await resolveTicket(ticketId);
      await fetchQueue();
    } finally {
      setResolvingId(null);
    }
  }

  const pendingCount = queue.filter((t) => t.status !== "resolved").length;

  return (
    <div className="flex flex-col h-full bg-zinc-900/60 backdrop-blur-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-zinc-800 flex-shrink-0 flex items-center gap-2">
        <h2 className="text-white font-semibold text-base">Human Queue</h2>
        <span className="bg-zinc-700 text-zinc-300 text-xs font-semibold px-2 py-0.5 rounded-full">
          {pendingCount}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 scrollbar-thin scrollbar-track-zinc-900 scrollbar-thumb-zinc-700">
        {initialLoading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : fetchError ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-zinc-500 text-sm text-center">
              Unable to load queue
            </p>
          </div>
        ) : queue.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-zinc-500 text-sm text-center">
              No escalated tickets
            </p>
          </div>
        ) : (
          queue.map((ticket) => (
            <div
              key={ticket.ticket_id}
              className={`bg-zinc-800/50 border border-zinc-700/50 border-l-4 ${priorityBorder(ticket.priority)} rounded-lg px-3 py-3 hover:border-zinc-600 transition-all duration-150`}
            >
              {/* Top row */}
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-semibold px-1.5 py-0.5 rounded ${priorityBadge(ticket.priority)}`}
                  >
                    {ticket.priority}
                  </span>
                  <span className="text-zinc-400 text-xs">{ticket.customer_id}</span>
                </div>
                <span className="text-zinc-600 text-xs">
                  {relativeTime(ticket.created_at)}
                </span>
              </div>

              {/* Summary */}
              <p className="text-zinc-200 text-sm leading-snug mb-2">
                {ticket.summary.length > 120
                  ? ticket.summary.slice(0, 120) + "…"
                  : ticket.summary}
              </p>

              {/* Resolve button */}
              <button
                onClick={() => handleResolve(ticket.ticket_id)}
                disabled={resolvingId === ticket.ticket_id}
                className="text-xs px-2.5 py-1 border border-zinc-600 hover:border-zinc-500 text-zinc-300 hover:text-white rounded-md transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {resolvingId === ticket.ticket_id ? "Resolving..." : "Resolve"}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
