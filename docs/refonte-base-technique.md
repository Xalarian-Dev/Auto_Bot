# Refonte, étape 0 : choisir la base technique

Ticket : [Auto_Bot #6](https://github.com/Xalarian-Dev/Auto_Bot/issues/6) — plan : [#3](https://github.com/Xalarian-Dev/Auto_Bot/issues/3).

Ce document est une **étude**, pas du code. Il propose des choix ; **c'est le propriétaire qui valide**.
Décisions déjà prises (2026-10-15) : direction B (garder ce qui marche, revoir le reste), hébergement
dans le cloud, gratuit au départ, usage d'abord personnel. Le bot n'envoie rien vers l'extérieur.

**Honnêteté sur les chiffres** : je n'ai pas pu consulter les sites des fournisseurs pendant cette
étude. Toute limite gratuite ci-dessous est donc marquée **« à vérifier »** : ce sont des ordres de
grandeur connus, qui changent souvent. À confirmer sur le site du fournisseur avant de s'engager.

---

## 1. Que garde-t-on ?

Constat tiré du code actuel (lu, pas exécuté) :

| Morceau | Fichier | Réutilisable tel quel dans le cloud ? |
|---|---|---|
| Connecteurs vers les plateformes | `scout/sources/*.py` (9 fichiers : SerpAPI, Greenhouse, USAJobs, Jaabz, GlobalJobs, JobBank, ITJobBoard, Indeed, MyCareersFuture) | **Oui, en grande partie.** Ils utilisent `httpx` + `beautifulsoup4` (pas de navigateur piloté), donc ils tournent sur n'importe quel serveur Python. Les pages HTML « scrapées » peuvent casser si le site change : c'est vrai aujourd'hui aussi. |
| Notation par Claude | `scout/scorer.py` | **Oui.** Un appel par offre, avec une « fiche » de sortie imposée (score, relocation, notes). Seule adaptation : le profil du candidat vient de la base au lieu de `assets/candidate.yaml`. |
| Modèle d'une offre | `scout/models.py` | **Oui**, c'est du `pydantic` pur. La partie base de données (`JobListingORM`, SQLAlchemy) est à adapter. |
| Orchestration d'un passage | `scout/runner.py` | **À adapter.** Elle affiche dans un terminal (`rich`) et lit `config/criteria.yaml`. Il faut la découper en fonctions qui renvoient des résultats, appelables depuis une tâche planifiée. |
| Stockage | `scout/db.py` (SQLite, fichier local) | **À remplacer** par la base du cloud. |
| Interface | `app.py` (Streamlit, local) | **À remplacer** (c'est ce qui fait mal aujourd'hui). |
| Réglages | `config/mode_profiles.yaml` → `criteria.yaml` | **À remplacer** par des réglages en base, choisis par lieu. |
| Lettres de motivation | `drafter/` | **Plus tard** (étape ultérieure). Elle lit un PDF de CV et écrit des PDF sur disque : à repenser (voir le document RGPD). |

**À adapter dans les connecteurs** : les lieux et mots-clés sont lus dans un dictionnaire de config ;
il faudra les alimenter depuis la base. Les règles de région (`COUNTRY_REGION`, `scout/sources/base.py`)
sont limitées à APAC / Amérique du Nord : à remplacer par la liste continent → pays → ville (étape 2 du plan).

**Recommandation** : garder `scorer.py`, `models.py` (partie pydantic) et les connecteurs ; réécrire le
reste. Rien n'est supprimé du dépôt actuel tant que la nouvelle base n'est pas validée.

---

## 2. Où ça tourne ?

Il y a trois besoins distincts : **l'interface**, **les recherches programmées**, **la base**.

### 2a. L'interface (ce que l'utilisateur voit)

| Option | Avantages | Inconvénients |
|---|---|---|
| **A. Application web hébergée sur Vercel** (le propriétaire utilise déjà Vercel pour d'autres projets) | Gratuit pour un usage personnel (**à vérifier**) ; déploiement automatique à chaque fusion ; connexion facile à Supabase | Écrire une vraie interface web (plus de travail que Streamlit) |
| **B. Garder Streamlit, hébergé** (Streamlit Community Cloud ou autre) | On réutilise `app.py` ; moins de travail au départ | Mise en veille après inactivité (**à vérifier**) ; peu de contrôle sur la connexion des utilisateurs et la sécurité ; ce qu'on voulait justement quitter |
| **C. Rester en local** | Simple, privé | Contraire à la décision « cloud » |

**Recommandation : A.** C'est cohérent avec la décision « revoir entièrement » et avec l'outillage déjà connu.

### 2b. Les recherches programmées

Un passage complet (plusieurs sources + une notation Claude par offre) peut durer plusieurs minutes.
C'est le point le plus contraignant du gratuit.

| Option | Avantages | Inconvénients |
|---|---|---|
| **A. Tâche planifiée GitHub Actions** (le dépôt appelle le code Python 1 fois par jour) | Gratuit pour un dépôt public, minutes limitées pour un dépôt privé (**à vérifier**) ; pas de limite de durée courte ; Python tel quel, donc connecteurs réutilisés sans réécriture | Le dépôt est privé : le quota gratuit de minutes compte. Les secrets (clés) se règlent dans GitHub, ce qui convient. Pas de « bouton lancer maintenant » natif (il existe un déclenchement manuel à vérifier) |
| **B. Fonctions planifiées (cron) Vercel** | Même plateforme que l'interface | Durée maximale d'une fonction courte en gratuit (**à vérifier**) ; le code serait à écrire en JavaScript/TypeScript ou en Python limité ; mauvais choix pour un passage long |
| **C. Fonctions planifiées Supabase** (pg_cron + Edge Functions) | Tout au même endroit que la base | Fonctions en TypeScript (Deno), donc les connecteurs Python ne sont pas réutilisables tels quels ; limites de durée (**à vérifier**) |
| **D. Petit serveur toujours allumé** (Render, Fly, Railway...) | Aucune limite de durée | Souvent payant ou en veille en gratuit (**à vérifier**) |

**Recommandation : A (GitHub Actions)**, car elle garde le Python existant. Point à décider avec le
propriétaire : le dépôt est privé, donc il faut confirmer que le quota gratuit de minutes suffit
pour 1 passage par jour.

### 2c. La base de données

| Option | Avantages | Inconvénients |
|---|---|---|
| **A. Supabase (Postgres) gratuit** | Déjà évoqué par le propriétaire ; connexion des utilisateurs et règles « chacun ne voit que ses données » incluses (Row Level Security) | Projet gratuit mis en veille après une période d'inactivité et taille limitée (ordre de grandeur 500 Mo, **à vérifier**) |
| **B. SQLite sur un disque hébergé** | Aucun changement de code | Pas de disque persistant en gratuit sur la plupart des hébergeurs ; pas de comptes |
| **C. Autre Postgres gratuit** (Neon, etc.) | Alternative si Supabase gêne | Il faudrait ajouter soi-même la connexion des utilisateurs |

**Recommandation : A.** Pour contenir le poids : ne garder que les offres utiles (description tronquée
comme aujourd'hui à 1 500 caractères dans `scorer.py`), et purger les offres anciennes (le code
actuel passe déjà les offres de plus de 21 jours à « ignorée », `expire_old_listings`).

---

## 3. Comment on gère les accès ?

Règles proposées (elles découlent du cadre légal, voir `docs/refonte-cadre-legal.md`) :

1. **Connexion obligatoire** pour tout écran qui montre des données. Supabase Auth fournit cela.
2. **Chaque utilisateur ne voit que ses données** : règles de sécurité de la base (Row Level Security)
   activées sur chaque table, avec une colonne `user_id`. Même avec un seul utilisateur au départ, on le
   prévoit dès le début (décision du PO : « structure prête pour plusieurs comptes »).
3. **Clés d'accès** (Claude, SerpAPI, USAJobs) :
   - stockées dans les « secrets » de la plateforme (GitHub Actions / Vercel), **jamais** dans le code,
     jamais dans la base, jamais affichées dans l'interface ;
   - la clé de service de la base (qui contourne les règles de sécurité) n'est utilisée **que** par la
     tâche planifiée, jamais envoyée au navigateur.
4. **Le développeur automatique ne touche pas aux identifiants** (décision du 2026-10-14) : c'est le
   propriétaire qui renseigne les secrets et teste.

---

## 4. Quel coût réel ?

| Poste | Ordre de grandeur | Source |
|---|---|---|
| Notation par Claude (modèle Haiku, `scorer.py`) | 1 appel par offre ; ~1 500 caractères de description + profil en entrée, ~500 tokens max en sortie. Quelques centimes par centaine d'offres | **À vérifier** sur la grille tarifaire d'Anthropic (payant à l'usage, **pas gratuit**) |
| SerpAPI (Google Jobs) | 250 recherches/mois gratuites d'après le `README` du dépôt (le `.env.example` dit 100 : **les deux chiffres se contredisent**, à vérifier) | `README.md`, `.env.example` |
| USAJobs, Greenhouse, scrapers HTML | Gratuits | — |
| Supabase, Vercel, GitHub Actions | Gratuits dans leurs limites | **À vérifier** |

**Point de vigilance** : « gratuit » ne couvre pas Claude. Il faut prévoir un **plafond** (nombre maximal
d'offres notées par passage) pour éviter une facture surprise. Les recherches SerpAPI sont le facteur
limitant : avec 250 par mois, 1 passage par jour ne tient que si chaque passage fait au plus ~8 recherches.

**À décider par le propriétaire** : accepte-t-il un petit budget Claude (quelques euros par mois) ?

---

## 5. Quelle migration ?

La base actuelle est un fichier SQLite (`data/scout.db`, ignoré par git : il n'est pas dans le dépôt).

| Option | Avantages | Inconvénients |
|---|---|---|
| **A. Repartir de zéro** | Le plus simple ; pas de lien avec l'ancien schéma | On perd l'historique des offres notées et leur statut (« postulé », etc.) |
| **B. Importer l'ancienne base une fois** | On garde l'historique | Un petit script d'import, **à lancer par le propriétaire** (le développeur automatique ne touche pas aux données ni ne lance le bot) |

**Recommandation : B si le propriétaire tient à l'historique des offres déjà « postulées » ; sinon A.**
Les offres de plus de 21 jours sont de toute façon périmées, donc la perte d'un historique ancien est faible.
La colonne `fingerprint` (empreinte de l'offre) permet d'éviter les doublons à l'import.

---

## Synthèse des recommandations

| Question | Recommandation | À valider par le propriétaire |
|---|---|---|
| Que garde-t-on | Notation, modèles, connecteurs | oui |
| Interface | Application web sur Vercel | oui |
| Recherches programmées | GitHub Actions (Python existant) | quota de minutes du dépôt privé |
| Base | Supabase Postgres | taille et mise en veille du gratuit |
| Accès | Connexion + règles par utilisateur + secrets hors code | oui |
| Coût | Claude payant à l'usage, avec plafond | budget accepté ? |
| Migration | Import unique (ou départ de zéro) | tenir à l'historique ? |

Prochaine étape (après validation) : le PO crée les tickets « Profil », « Recherches par lieu »,
« Recherches programmées » et « Liste des offres ».
