import { Customer, HumanQueueItem, TicketRequest, TicketResponse } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function getCustomers(): Promise<Customer[]> {
  const res = await fetch(`${BASE_URL}/customers`);
  return handleResponse<Customer[]>(res);
}

export async function submitTicket(req: TicketRequest): Promise<TicketResponse> {
  const res = await fetch(`${BASE_URL}/ticket`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return handleResponse<TicketResponse>(res);
}

export async function getQueue(): Promise<HumanQueueItem[]> {
  const res = await fetch(`${BASE_URL}/queue`);
  return handleResponse<HumanQueueItem[]>(res);
}

export async function resolveTicket(ticketId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/queue/${ticketId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: "resolved" }),
  });
  await handleResponse<unknown>(res);
}
