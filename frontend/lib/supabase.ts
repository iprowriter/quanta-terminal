import { createBrowserClient } from "@supabase/ssr";

const supabaseUrl  = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

/**
 * Browser-side Supabase client — singleton.
 * Use this in client components and hooks.
 */
export const supabase = createBrowserClient(supabaseUrl, supabaseAnon);
