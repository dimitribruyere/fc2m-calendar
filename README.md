# FC2M - Synchronisation calendrier Sportcorico

Génère automatiquement un calendrier `.ics` à partir des événements Sportcorico
du club, abonnable depuis Google Agenda / Apple Calendrier.

## Mise en place (une seule fois)

1. Créer ce repo sur GitHub (public, requis pour GitHub Pages gratuit)
2. Settings -> Pages -> Source = "Deploy from a branch", Branch = `main`, dossier = `/docs`
3. Settings -> Secrets and variables -> Actions -> New repository secret
   - Nom : `SPORTCORICO_AUTH`
   - Valeur : `Bearer xxxxxxxxxxxx` (récupéré depuis les devtools du navigateur,
     onglet Réseau, requête vers api.sportcorico.com, header "Authorization")
4. Aller dans l'onglet "Actions" -> choisir le workflow "Synchronisation calendrier
   Sportcorico" -> "Run workflow" pour le premier lancement manuel
5. Une fois le premier run terminé, le fichier est disponible à :
   `https://VOTRE-PSEUDO.github.io/NOM-DU-REPO/fc2m.ics`

## Abonnement (pour chaque membre du club)

- **Google Calendar** (web) : Autres calendriers (+) -> Depuis une URL -> coller
  le lien ci-dessus (en `https://`, pas `webcal://`)
- **iPhone** : Réglages -> Calendrier -> Comptes -> Ajouter un compte -> Autre ->
  Ajouter un abonnement calendrier -> coller le lien en `webcal://`
  (remplacer `https://` par `webcal://` dans l'URL)

## Si le token expire

Un message d'erreur apparaîtra dans l'onglet Actions du repo (run en échec).
Il suffit de :
1. Se reconnecter à Sportcorico dans le navigateur
2. Récupérer le nouveau token (devtools -> Réseau -> header Authorization)
3. Mettre à jour le secret `SPORTCORICO_AUTH` sur GitHub
