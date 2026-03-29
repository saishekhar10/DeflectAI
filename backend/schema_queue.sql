create table if not exists human_queue (
    ticket_id uuid primary key,
    customer_id text,
    customer_tier text,
    priority text,
    summary text,
    what_was_tried text,
    original_ticket text,
    status text default 'pending',
    created_at timestamp with time zone default now()
);
