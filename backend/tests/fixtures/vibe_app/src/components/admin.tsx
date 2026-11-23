import { createClient } from "@supabase/supabase-js";

// The service-role key must never ship to the browser.
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY as string;

export const adminClient = createClient(
  process.env.SUPABASE_URL as string,
  serviceKey,
);
