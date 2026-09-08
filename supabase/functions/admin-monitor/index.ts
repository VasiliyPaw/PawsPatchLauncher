import { makeHandler } from './handler.mjs';
Deno.serve(makeHandler({serviceKey:Deno.env.get('SUPABASE_SERVICE_ROLE_KEY'),
 resendKey:Deno.env.get('PAW_MONITOR_RESEND_KEY'),managementToken:Deno.env.get('PAW_MONITOR_SUPABASE_TOKEN'),
 tokenExpiresAt:Deno.env.get('PAW_MONITOR_TOKEN_EXPIRES_AT')}));
