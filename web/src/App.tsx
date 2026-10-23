import { FormEvent, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { isConfigured, supabase } from "./supabase";

const box: React.CSSProperties = {
  maxWidth: 420,
  margin: "40px auto",
  padding: "0 16px",
  fontFamily: "system-ui, sans-serif",
};

function AuthForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  async function submit(mode: "signup" | "signin", e: FormEvent) {
    e.preventDefault();
    setMessage("");
    const creds = { email, password };
    const { error } =
      mode === "signup"
        ? await supabase.auth.signUp(creds)
        : await supabase.auth.signInWithPassword(creds);
    if (error) setMessage(error.message);
    else if (mode === "signup")
      setMessage("Compte créé. Si Supabase demande une confirmation, regarde tes e-mails.");
  }

  return (
    <form onSubmit={(e) => submit("signin", e)}>
      <h1>Auto_Bot</h1>
      <p>Connecte-toi ou crée un compte.</p>
      <p>
        <input type="email" required placeholder="E-mail" value={email}
          onChange={(e) => setEmail(e.target.value)} style={{ width: "100%" }} />
      </p>
      <p>
        <input type="password" required minLength={8} placeholder="Mot de passe (8 caractères min.)"
          value={password} onChange={(e) => setPassword(e.target.value)} style={{ width: "100%" }} />
      </p>
      <button type="submit">Me connecter</button>{" "}
      <button type="button" onClick={(e) => submit("signup", e)}>Créer mon compte</button>
      {message && <p role="status">{message}</p>}
    </form>
  );
}

function Home({ session }: { session: Session }) {
  const [name, setName] = useState("");
  const [visibleRows, setVisibleRows] = useState<number | null>(null);
  const [message, setMessage] = useState("");

  async function refresh() {
    // Sans filtre volontaire : c'est la base (RLS) qui doit limiter aux lignes du compte.
    const { data, error } = await supabase.from("profiles").select("user_id, display_name");
    if (error) return setMessage(error.message);
    setVisibleRows(data.length);
    setName(data[0]?.display_name ?? "");
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    setMessage("");
    const { error } = await supabase
      .from("profiles")
      .upsert({ user_id: session.user.id, display_name: name });
    setMessage(error ? error.message : "Enregistré.");
    await refresh();
  }

  return (
    <div>
      <h1>Bonjour, tu es connecté</h1>
      <p>Compte : {session.user.email}</p>
      <form onSubmit={save}>
        <p>Test de la règle d'accès : écris un nom et enregistre.</p>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Un nom de test" />{" "}
        <button type="submit">Enregistrer</button>
      </form>
      <p>Lignes visibles pour ce compte : {visibleRows ?? "…"} (attendu : 0 ou 1, jamais celles d'un autre compte)</p>
      {message && <p role="status">{message}</p>}
      <button onClick={() => supabase.auth.signOut()}>Me déconnecter</button>
    </div>
  );
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isConfigured) return;
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setReady(true);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, s) => setSession(s));
    return () => data.subscription.unsubscribe();
  }, []);

  if (!isConfigured)
    return (
      <div style={box}>
        <h1>Auto_Bot</h1>
        <p>
          Le site n'est pas encore relié à Supabase. Il manque les réglages
          VITE_SUPABASE_URL et VITE_SUPABASE_ANON_KEY (voir web/.env.example).
        </p>
      </div>
    );

  return <div style={box}>{!ready ? <p>Chargement…</p> : session ? <Home session={session} /> : <AuthForm />}</div>;
}
