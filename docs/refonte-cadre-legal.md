# Refonte, étape 0 : cadre légal (données personnelles, CGU)

Ticket : [Auto_Bot #7](https://github.com/Xalarian-Dev/Auto_Bot/issues/7) — plan : [#3](https://github.com/Xalarian-Dev/Auto_Bot/issues/3).

> **Avertissement important.** Ce document est un **document de travail** écrit par une IA, pas par
> un juriste. Il ne remplace **pas** un avis professionnel. Les textes de la partie 4 sont des
> **brouillons** à faire relire avant toute ouverture à d'autres personnes. Les références à la CNIL
> et au RGPD sont données de mémoire : **à vérifier** sur les sites officiels (cnil.fr, eur-lex.europa.eu).

Rappel en une phrase : le **RGPD** est la loi européenne qui encadre l'usage des données personnelles ;
les **CGU** sont les conditions d'utilisation que l'utilisateur accepte.

Décisions du propriétaire prises en compte (2026-10-15) :
- un CV peut servir à **pré-remplir** le profil ; il est **lu une fois, relu par l'utilisateur, puis détruit** ;
- on ne garde que le contenu utile (expériences, diplômes) et, au besoin, nom et prénom pour les lettres ;
- **l'import depuis un fichier n'est qu'une idée, optionnelle** : l'utilisateur doit toujours pouvoir
  **saisir ses informations à la main** dans une interface dédiée ;
- le bot n'envoie rien vers l'extérieur tout seul.

---

## 1. Quelles données on garde, lesquelles on ne garde jamais

| Donnée | On la garde ? | Pourquoi | Où |
|---|---|---|---|
| Fichier du CV (PDF ou autre) | **Jamais** | Inutile une fois le profil extrait ; c'est la donnée la plus sensible | Mémoire le temps de la lecture seulement |
| Texte brut extrait du CV | **Jamais** | Idem | Mémoire seulement, pas dans les journaux |
| Profil relu et validé (expériences, diplômes, compétences, langues) | Oui | Sert à noter les offres | Base, rattaché au compte |
| Nom et prénom | Oui, **seulement si** utile aux lettres de motivation | Personnalisation des lettres | Base, rattaché au compte |
| Coordonnées (e-mail, téléphone, adresse) | À éviter : à ne demander que si une fonction en a besoin | Minimisation | Base si besoin |
| Offres trouvées et leur note | Oui | Fonction principale | Base, rattachées au compte |
| Statut d'une offre (postulée, ignorée...) | Oui | Suivi | Base |
| Résultats de l'appel à Claude (note, commentaire) | Oui | Affichés à l'utilisateur | Base |
| Journaux techniques | Sans donnée personnelle (voir partie 5) | Dépannage | Plateforme |

Principe appliqué : **minimisation** (ne collecter que le nécessaire) et **durée limitée** (purger les
offres anciennes ; le code actuel passe déjà les offres de plus de 21 jours à « ignorée »,
`scout/db.py`, `expire_old_listings`).

**Constat dans le code actuel** (à corriger dans la nouvelle version) : `drafter/resume.py` lit le
premier PDF du dossier `assets/` et `drafter/writer.py` écrit des PDF de lettres sur disque (`output/`).
C'est acceptable en local, mais **pas** dans une application hébergée : le fichier ne doit pas être écrit
durablement sur un serveur.

---

## 2. Les droits de l'utilisateur

À prévoir dans l'interface (liste classique du RGPD, **à vérifier** par un juriste) :

1. **Voir** toutes ses données (profil, offres, notes) : une page « Mes données ».
2. **Corriger** son profil à tout moment.
3. **Exporter** ses données dans un format lisible (par exemple un fichier JSON ou CSV).
4. **Tout effacer en un geste** : un bouton « Supprimer mon compte et mes données » qui supprime le
   profil, les offres et le compte, avec confirmation. La suppression doit être **réelle** (pas un simple
   masquage) et couvrir toutes les tables.
5. **Retirer son accord** et s'opposer à un traitement : même bouton, ou contact indiqué dans la politique.
6. Un **contact** (e-mail) pour exercer ces droits.

---

## 3. Les services tiers qui voient des données

| Service | Ce qu'il voit | Point de vigilance |
|---|---|---|
| **Anthropic (Claude)** | Pour la notation : titre, entreprise, lieu, début de description de l'offre, et le **profil du candidat** (`scout/scorer.py` envoie `get_scorer_profile()` comme consigne système). Pour une éventuelle extraction du CV : le **contenu du CV** | **À vérifier** : durée de conservation chez le fournisseur, utilisation ou non pour l'entraînement, options de « zéro conservation », localisation des données (hors Union européenne ?). À lire dans les conditions d'Anthropic avant de décider |
| **Supabase** (base et connexion) | Toutes les données stockées | **À vérifier** : région d'hébergement (choisir une région européenne si possible), accord de traitement des données |
| **Vercel / GitHub** (hébergement, tâches) | Le trafic ; les secrets | **À vérifier** : où sont traités les journaux |
| **SerpAPI et plateformes d'emploi** | Les mots-clés et lieux recherchés | Ne jamais y envoyer de donnée personnelle du candidat (le code actuel n'y envoie que des requêtes de recherche) |

**Transfert hors de l'Union européenne** : plusieurs de ces services sont américains. Le RGPD l'encadre
(clauses contractuelles, etc.). **À faire vérifier par un juriste** avant d'ouvrir à d'autres personnes.

---

## 4. Brouillons de CGU et de politique de confidentialité

> **Brouillons non validés.** Les passages entre `[crochets]` sont à compléter par le propriétaire.
> Ne pas publier sans relecture par une personne compétente.

### 4a. Brouillon de conditions générales d'utilisation (CGU)

**1. Objet.** [Nom du service] aide à rechercher des offres d'emploi, à les classer selon votre profil
et à suivre vos candidatures. Il n'envoie aucune candidature à votre place.

**2. Compte.** L'accès demande un compte. Vous êtes responsable de la confidentialité de vos identifiants.

**3. Vos contenus.** Vous restez propriétaire des informations que vous saisissez. Vous nous autorisez
seulement à les utiliser pour faire fonctionner le service.

**4. Notation par intelligence artificielle.** Les notes sont produites par un modèle d'IA. Elles sont
**indicatives**, peuvent être fausses, et ne garantissent ni un entretien ni un emploi. Vérifiez toujours
l'offre d'origine.

**5. Offres de tiers.** Les offres viennent de sites tiers. Nous n'en garantissons ni l'exactitude ni la
disponibilité, et nous ne sommes pas partie à la relation entre vous et l'employeur.

**6. Utilisations interdites.** [À compléter : usage abusif, automatisation excessive, tentative d'accès aux
données d'autrui...]

**7. Disponibilité.** Le service est fourni « en l'état », sans garantie de disponibilité continue
[à ajuster].

**8. Suppression.** Vous pouvez supprimer votre compte et vos données à tout moment depuis [page].

**9. Responsabilité.** [À faire rédiger par un juriste : limites de responsabilité valables en droit français.]

**10. Droit applicable et contact.** [Droit français ; adresse de contact.]

### 4b. Brouillon de politique de confidentialité

**Qui est responsable ?** [Nom ou pseudonyme du responsable, adresse de contact.]

**Quelles données ?** Les informations de votre profil (expériences, diplômes, compétences, langues, et si
vous le choisissez nom et prénom), les offres enregistrées pour vous, leurs notes et leur statut.

**Ce que nous ne conservons pas.** Si vous importez un CV, **le fichier n'est pas conservé** : il est lu
une fois pour proposer un profil, que vous relisez et corrigez, puis il est détruit. Vous pouvez aussi
saisir vos informations à la main, sans jamais importer de fichier.

**Pourquoi ?** Pour rechercher et classer des offres pour vous. [Base légale : votre consentement et/ou
l'exécution du service : à faire confirmer par un juriste.]

**Qui reçoit vos données ?** Nos prestataires techniques : hébergement et base de données [Supabase,
Vercel, GitHub : à confirmer], et le fournisseur d'IA [Anthropic] qui reçoit le contenu nécessaire à la
notation [et à l'extraction du CV]. [Préciser les transferts hors Union européenne.]

**Combien de temps ?** Tant que votre compte existe ; les offres anciennes sont supprimées après
[durée à fixer]. À la suppression du compte, toutes vos données sont effacées.

**Vos droits.** Accès, correction, export, suppression, opposition : depuis la page « Mes données » ou à
[contact]. Vous pouvez aussi saisir la CNIL (autorité française) en cas de désaccord.

**Sécurité.** Connexion obligatoire, chaque utilisateur ne voit que ses données, secrets hors du code.

---

## 5. Règles pour le développement

À respecter dans toutes les étapes de la refonte :

1. **Connexion obligatoire** pour tout écran ou toute interface de programmation qui touche aux données.
2. **Chaque utilisateur ne voit que ses données** : colonne `user_id` sur chaque table et règles de
   sécurité de la base (Row Level Security) activées, avec **un test** qui vérifie qu'un utilisateur ne
   lit pas les données d'un autre.
3. **Aucune donnée personnelle dans les journaux** : ne jamais journaliser le texte d'un CV, un nom, un
   e-mail ou un profil. Les journaux actuels (`scout/scorer.py`) affichent des titres d'offres, pas de
   données du candidat : à conserver ainsi.
4. **Le CV n'est jamais écrit sur disque de façon durable** : traitement en mémoire, fichier temporaire
   supprimé aussitôt si inévitable, jamais dans un dossier versionné ni sauvegardé.
5. **Pas de CV réel ni de donnée réelle** dans un ticket, un test ou un exemple : utiliser des données
   fictives. (`assets/candidate.yaml` est déjà ignoré par git ; garder cette protection.)
6. **Secrets** (clés Claude, SerpAPI, base) uniquement dans les secrets de la plateforme ; la clé de
   service de la base n'est jamais envoyée au navigateur.
7. **Saisie manuelle toujours possible** : l'import de CV est optionnel, jamais obligatoire.
8. **Suppression complète** testée : après « tout supprimer », plus aucune ligne liée à l'utilisateur.
9. **Purge** des offres anciennes et durée de conservation écrites dans la politique.
10. Le développeur automatique ne touche pas aux identifiants ni aux vraies données (décision du 2026-10-14).

---

## 6. À décider par le propriétaire

- [ ] **Relecture juridique externe** avant d'ouvrir à d'autres personnes ? **Recommandation : oui**, dès
  que quelqu'un d'autre que le propriétaire utilise le service (ses CV deviennent des données sensibles,
  sa responsabilité est engagée). Tant que le service reste **personnel**, le risque est bien plus faible.
- [ ] Garder nom et prénom en base (lettres de motivation) ou les demander à chaque lettre ?
- [ ] Région d'hébergement de la base (Union européenne de préférence).
- [ ] Durée de conservation des offres.
