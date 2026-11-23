create table posts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  body text
);
