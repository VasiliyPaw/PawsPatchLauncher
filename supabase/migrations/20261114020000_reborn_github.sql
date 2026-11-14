-- Additive provider metadata. Existing private Storage builds remain valid.
alter table paw_private.reborn_builds
 add column download_provider text not null default 'supabase',
 add column github_repository text,
 add column github_repository_id bigint,
 add column github_asset_id bigint,
 add constraint reborn_builds_provider check (
  (download_provider='supabase' and github_repository is null and github_repository_id is null and github_asset_id is null)
  or (download_provider='github' and github_repository is not null
   and github_repository ~ '^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}$'
   and github_repository_id is not null and github_repository_id between 1 and 9007199254740991
   and github_asset_id is not null and github_asset_id between 1 and 9007199254740991)
 );
-- Service-only RPCs serialize the full row, so they include these public metadata fields.
-- Credentials and signed URLs are never stored in this table.
