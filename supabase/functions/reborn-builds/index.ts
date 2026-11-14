import { makeHandler } from "./handler.mjs";
Deno.serve(makeHandler({url:Deno.env.get("SUPABASE_URL"),serviceKey:Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"),publicKey:Deno.env.get("SUPABASE_ANON_KEY"),
 githubToken:Deno.env.get('REBORN_GITHUB_TOKEN'),githubRepository:Deno.env.get('REBORN_GITHUB_REPOSITORY'),githubRepositoryId:Number(Deno.env.get('REBORN_GITHUB_REPOSITORY_ID'))}));
