export type Customer = {
  customer_id: string;
  name: string;
  plan: string;
  tier: string;
};

export type TicketRequest = {
  ticket_text: string;
  customer_id: string;
};

export type TicketResponse = {
  final_response: string;
  resolution_type: "resolved" | "escalated";
  agents_used: string[];
  ticket_id: string;
  resolution_time_ms: number;
};

export type HumanQueueItem = {
  ticket_id: string;
  customer_id: string;
  customer_tier: string;
  priority: "low" | "medium" | "high";
  summary: string;
  what_was_tried: string;
  original_ticket: string;
  status: string;
  created_at: string;
};
