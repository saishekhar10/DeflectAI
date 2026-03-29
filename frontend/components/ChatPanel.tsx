"use client";

import { useEffect, useRef, useState } from "react";
import { getCustomers, submitTicket } from "../lib/api";
import { Customer, TicketResponse } from "../lib/types";

type ConversationEntry = {
  ticket: string;
  response: TicketResponse;
};

type ChatPanelProps = {
  onTicketResponse: (response: TicketResponse | null, isLoading: boolean) => void;
};

function Spinner() {
  return (
    <svg
      className="animate-spin h-4 w-4 text-white"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

function ResolutionBadge({ type }: { type: "resolved" | "escalated" }) {
  return (
    <span
      className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full animate-pulse ${
        type === "resolved"
          ? "bg-emerald-900 text-emerald-300"
          : "bg-orange-900 text-orange-300"
      }`}
      style={{ animationIterationCount: 1, animationDuration: "1s" }}
    >
      {type === "resolved" ? "Resolved" : "Escalated"}
    </span>
  );
}

export default function ChatPanel({ onTicketResponse }: ChatPanelProps) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customersError, setCustomersError] = useState(false);
  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [ticketText, setTicketText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [submitError, setSubmitError] = useState(false);
  const [history, setHistory] = useState<ConversationEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getCustomers()
      .then((data) => {
        setCustomers(data);
        if (data.length > 0) setSelectedCustomerId(data[0].customer_id);
      })
      .catch(() => setCustomersError(true));
  }, []);

  useEffect(() => {
    if (history.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [history]);

  async function handleSubmit() {
    if (!ticketText.trim() || !selectedCustomerId || isLoading) return;
    setIsLoading(true);
    setSubmitError(false);
    onTicketResponse(null, true);
    try {
      const result = await submitTicket({
        ticket_text: ticketText,
        customer_id: selectedCustomerId,
      });
      setHistory((prev) => [...prev.slice(-4), { ticket: ticketText, response: result }]);
      setTicketText("");
      onTicketResponse(result, false);
    } catch {
      setSubmitError(true);
      onTicketResponse(null, false);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-zinc-900/60 backdrop-blur-sm border-r border-zinc-800 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-zinc-800 flex-shrink-0">
        <h2 className="text-white font-semibold text-base">Support Chat</h2>
      </div>

      {/* Conversation history */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-thin scrollbar-track-zinc-900 scrollbar-thumb-zinc-700">
        {history.length === 0 && (
          <p className="text-zinc-600 text-sm text-center mt-8">
            Submit a ticket to start the conversation
          </p>
        )}
        {history.map((entry, i) => (
          <div key={i} className="space-y-2">
            {/* User message */}
            <div className="flex justify-end">
              <div className="bg-zinc-800 text-zinc-200 text-sm rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[85%]">
                {entry.ticket}
              </div>
            </div>
            {/* Agent response */}
            <div className="bg-zinc-800/50 border border-zinc-700 rounded-2xl rounded-tl-sm px-4 py-3 max-w-[90%]">
              <div className="flex items-center gap-2 mb-2">
                <ResolutionBadge type={entry.response.resolution_type} />
                <span className="text-zinc-500 text-xs">
                  {entry.response.resolution_time_ms}ms
                </span>
              </div>
              <p className="text-zinc-100 text-sm leading-relaxed">
                {entry.response.final_response}
              </p>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 border-t border-zinc-800 p-4 space-y-3">
        {/* Customer selector */}
        {customersError ? (
          <p className="text-red-400 text-xs">Unable to load customers</p>
        ) : (
          <select
            value={selectedCustomerId}
            onChange={(e) => setSelectedCustomerId(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-150"
          >
            {customers.map((c) => (
              <option key={c.customer_id} value={c.customer_id}>
                {c.name} — {c.plan} ({c.tier})
              </option>
            ))}
          </select>
        )}

        {/* Textarea */}
        <textarea
          rows={4}
          value={ticketText}
          onChange={(e) => setTicketText(e.target.value)}
          placeholder="Describe the customer's issue..."
          className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-2.5 resize-none placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-150"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
          }}
        />

        {/* Submit error */}
        {submitError && (
          <p className="text-red-400 text-xs">
            Something went wrong. Please try again.
          </p>
        )}

        {/* Buttons */}
        <div className="flex gap-2">
          <button
            onClick={handleSubmit}
            disabled={isLoading || customersError || !ticketText.trim()}
            className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium rounded-lg py-2.5 transition-all duration-150 active:scale-[0.98]"
          >
            {isLoading ? (
              <>
                <Spinner />
                Processing...
              </>
            ) : (
              "Submit Ticket"
            )}
          </button>
          {history.length > 0 && (
            <button
              onClick={() => setHistory([])}
              className="px-3 py-2.5 text-zinc-400 hover:text-zinc-200 text-sm border border-zinc-700 hover:border-zinc-600 rounded-lg transition-all duration-150"
            >
              Clear
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
