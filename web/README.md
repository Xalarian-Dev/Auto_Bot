# Auto_Bot web (refonte, étape 1)

Squelette du nouveau site : connexion Supabase + une table protégée (`supabase/migrations/`).
L'ancien bot (dossiers `scout/`, `drafter/`, `app.py`...) n'est pas touché.

- Réglages : copier `.env.example` vers `.env.local` (noms seulement dans le dépôt, jamais de valeurs).
- Lancer en local : `npm ci` puis `npm run dev`. Vérifier : `npm run build`.
- Vercel : dossier racine du projet = `web`; variables `VITE_SUPABASE_URL` et `VITE_SUPABASE_ANON_KEY`.
