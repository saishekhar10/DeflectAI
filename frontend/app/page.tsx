"use client";

import { useState } from "react";
import AgentTracePanel from "../components/AgentTracePanel";
import ChatPanel from "../components/ChatPanel";
import HumanQueuePanel from "../components/HumanQueuePanel";
import Navbar from "../components/Navbar";
import { TicketResponse } from "../lib/types";

export default function Home() {
  const [ticketResponse, setTicketResponse] = useState<TicketResponse | null>(null);
  const [traceLoading, setTraceLoading] = useState(false);

  function handleTicketResponse(response: TicketResponse | null, isLoading: boolean) {
    setTicketResponse(response);
    setTraceLoading(isLoading);
  }

  return (
    <div className="fixed inset-0 flex flex-col bg-zinc-950">
      <Navbar />
      <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-[40%_35%_25%] overflow-hidden">
        <ChatPanel onTicketResponse={handleTicketResponse} />
        <AgentTracePanel ticketResponse={ticketResponse} isLoading={traceLoading} />
        <HumanQueuePanel />
      </div>
    </div>
  );
}
