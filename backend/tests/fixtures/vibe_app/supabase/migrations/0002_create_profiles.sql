create table profiles (
  id uuid primary key,
  display_name text
);

alter table profiles enable row level security;

create policy "users read own profile" on profiles
  for select using (auth.uid() = id);
