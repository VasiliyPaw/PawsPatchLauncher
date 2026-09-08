alter table public.paw_messages add constraint paw_messages_nonempty_id check(message_id<>'00000000-0000-0000-0000-000000000000'::uuid);
