-- Python Submit : suppression sécurisée d'un compte élève par un professeur
-- À exécuter une fois dans Supabase > SQL Editor.

create or replace function public.teacher_delete_student(target_user_id uuid)
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
begin
  if not public.is_teacher() then
    raise exception 'Accès professeur requis';
  end if;

  -- Interdit de supprimer un compte professeur.
  if exists (
    select 1 from public.teacher_accounts
    where user_id = target_user_id
  ) then
    raise exception 'Impossible de supprimer un compte professeur';
  end if;

  -- Les tables student_progress et student_submissions sont liées
  -- à auth.users avec ON DELETE CASCADE : leurs données disparaissent aussi.
  delete from auth.users where id = target_user_id;

  if not found then
    raise exception 'Compte élève introuvable';
  end if;
end;
$$;

revoke all on function public.teacher_delete_student(uuid) from public;
grant execute on function public.teacher_delete_student(uuid) to authenticated;
