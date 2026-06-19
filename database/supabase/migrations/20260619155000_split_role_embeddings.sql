-- Split role matching vectors into capability and intent embeddings.
-- User/profile embeddings remain request-local and are not stored.

alter table public.career_roles
  add column if not exists capability_embedding vector(768),
  add column if not exists intent_embedding vector(768),
  add column if not exists capability_embedding_text text,
  add column if not exists intent_embedding_text text;

alter table public.career_roles
  drop column if exists embedding,
  drop column if exists embedding_text;

alter table public.certifications
  drop column if exists embedding;
