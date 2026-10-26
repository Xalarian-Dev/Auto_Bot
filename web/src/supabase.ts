import { createClient } from "@supabase/supabase-js";

// Les valeurs viennent de l'environnement (Vercel ou .env.local), jamais du code.
const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const isConfigured = Boolean(url && anonKey);

// Si la configuration manque, on crée un client factice pour que la page s'affiche
// et explique quoi faire (voir App.tsx), au lieu de planter.
export const supabase = createClient(
  url ?? "http://localhost:0",
  anonKey ?? "missing-anon-key",
);
