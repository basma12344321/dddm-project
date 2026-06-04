# Contexte du projet DDDM

Ce fichier sert de contexte de reprise pour une autre IA ou un autre agent de developpement.

## 1. Architecture actuelle du projet

Le projet DDDM est une application d'aide a la decision basee sur les donnees. Il contient deux grands domaines fonctionnels :

- Finance : analyse de donnees financieres, prediction de ROIC, interpretation de resultats et analyse par ticker.
- Logistique : ordonnancement de taches sur machines avec une approche hybride heuristiques + recuit simule.

### Backend Flask

Le backend se trouve dans `backend/`.

Fichiers et dossiers importants :

- `backend/main.py` : point d'entree Flask. Il cree l'application, configure CORS, JWT, SQLAlchemy, enregistre les blueprints et cree les tables.
- `backend/config.py` : configuration globale, notamment `UPLOAD_FOLDER`, extensions autorisees, chemins des modeles.
- `backend/app/routes/api.py` : routes principales API.
  - `/upload` : upload de fichiers CSV/PDF.
  - `/analyze` : analyse finance ou logistique selon le domaine.
  - `/analyze-ticker` : analyse finance via yfinance.
  - `/simulate` : simulation generique.
  - `/schedule` : endpoint principal du nouveau module logistique.
  - `/schedule/rules` : liste des heuristiques disponibles.
  - `/schedule/history` : historique des ordonnancements.
  - `/schedule/compare/<id1>/<id2>` : comparaison de deux sessions.
  - `/schedule/simulate` : simulation what-if logistique.
  - `/dashboard-data` : donnees dashboard finance.
- `backend/app/routes/auth.py` : authentification, inscription, login, profil, liste utilisateurs.
- `backend/app/plugins/` : plugins metier.
  - `base_plugin.py` : interface abstraite.
  - `finance_plugin.py` : logique finance.
  - `logistic_plugin.py` : plugin logistique refactorise sans PPO/PyTorch.
- `backend/app/core_engine/` : moteurs et chargeurs.
  - `core_engine.py` : nettoyage et preparation des donnees.
  - `plugin_loader.py` : chargement dynamique des plugins.
  - `model_loader.py` : chargement des modeles ML finance.
  - `scheduling_engine.py` : nouveau moteur d'ordonnancement logistique.
- `backend/app/models/__init__.py` : modeles SQLAlchemy réellement importés par Python.
- `backend/app/models.py` existe aussi, mais attention : comme il y a un dossier `backend/app/models/`, `import app.models` charge le package `models/__init__.py`, pas le fichier `models.py`.

### Base de donnees PostgreSQL

Le projet utilise SQLAlchemy avec PostgreSQL par defaut.

Configuration :

- Variable d'environnement prioritaire : `DATABASE_URL`
- Valeur par defaut dans `backend/main.py` :
  `postgresql://postgres:dddm1234@localhost:5432/dddm_db`

Tables principales :

- `users`
- `analyses`
- `simulations`
- `scheduling_sessions`
- `scheduling_results`
- `scheduling_simulations`

Les tables logistiques `scheduling_*` sont destinees a stocker les executions de `/schedule`, leurs resultats, et les simulations what-if.

### Frontend Angular

Le frontend se trouve dans `dashboard_sandbox/`.

Fichiers et dossiers importants :

- `dashboard_sandbox/src/app/services/api.service.ts` : service HTTP vers Flask.
- `dashboard_sandbox/src/app/analyze/` : page d'upload/analyse.
- `dashboard_sandbox/src/app/simulation/` : page de simulation finance/logistique.
- `dashboard_sandbox/src/app/analyze-result/` : affichage resultats finance.
- `dashboard_sandbox/src/app/components/gantt-chart/` : nouveau composant Gantt pour l'ordonnancement.
- `dashboard_sandbox/src/app/components/logistics-dashboard/` : nouveau dashboard metriques logistiques.
- `dashboard_sandbox/src/app/layouts/admin-layout/admin-layout.module.ts` : module qui declare/importe les composants de l'espace admin.
- `dashboard_sandbox/src/app/layouts/admin-layout/admin-layout.routing.ts` : routes Angular, dont `/simulation`.

Le frontend Angular est base sur Angular 14 et utilise Angular Material et ng-apexcharts.

### Scripts Data Science

Les scripts se trouvent dans `scripts/`.

- `scripts/train_finance_model.py` : entrainement du modele finance.
- `scripts/train_dummy_model.py` : modele factice/test.

Modeles et donnees :

- `backend/app/models/finance/regression_model.pkl`
- `backend/app/models/finance/classification_model.pkl`
- `backend/app/data/df_final.csv`
- `backend/data/` : fichiers de test/upload, dont des CSV logistiques.

## 2. Resume de ce qui a ete fait

Le travail recent s'est concentre sur le plugin logistique.

### Ancien probleme

Le plugin logistique utilisait PPO via Stable-Baselines3/PyTorch/Gymnasium. Sur Windows, cela provoquait des erreurs DLL, notamment au chargement de PyTorch. L'analyse logistique ne fonctionnait donc pas correctement.

### Nouvelle direction confirmee

Le choix confirme est d'abandonner PPO/PyTorch pour la logistique et de continuer avec une approche hybride :

- heuristiques de dispatching ;
- recuit simule ;
- pas de dependance active a Stable-Baselines3, PyTorch ou Gymnasium pour le plugin logistique.

### Backend logistique

Un nouveau moteur a ete ajoute :

- `backend/app/core_engine/scheduling_engine.py`

Il gere :

- preprocessing des taches ;
- validation des colonnes ;
- support des champs `Task`, `Duration`, `Deadline`, `Priority`, `Dependencies`, `SetupTime`, `MachineConstraint` ;
- detection de cycles dans les dependances ;
- verification des dependances inexistantes ;
- heuristiques `SPT`, `EDD`, `LPT`, `WSPT` ;
- affectation de taches sur plusieurs machines ;
- prise en compte des dependances ;
- calcul du Gantt ;
- metriques :
  - makespan ;
  - utilisation machine ;
  - balance index ;
  - taux de respect des deadlines ;
  - retard total ;
  - overhead setup ;
  - chemin critique ;
- optimisation par recuit simule ;
- donnees de convergence ;
- interpretation et recommandations.

Le plugin logistique a ete refactorise :

- `backend/app/plugins/logistic_plugin.py`

Il utilise maintenant `SchedulingEngine` au lieu de PPO.

Des routes ont ete ajoutees dans :

- `backend/app/routes/api.py`

Routes ajoutees ou ameliorees :

- `/schedule`
- `/schedule/rules`
- `/schedule/history`
- `/schedule/compare/<session_id_1>/<session_id_2>`
- `/schedule/simulate`

Des modeles SQLAlchemy logistiques ont ete ajoutes dans le package réellement importe :

- `backend/app/models/__init__.py`

Modeles :

- `SchedulingSession`
- `SchedulingResult`
- `SchedulingSimulation`

### Frontend logistique

La page d'analyse lit maintenant les CSV logistiques localement cote navigateur apres upload, puis redirige vers `/simulation` avec les taches en `history.state`.

Fichier modifie :

- `dashboard_sandbox/src/app/analyze/analyze.component.ts`

La page simulation a ete enrichie pour la logistique :

- formulaire de configuration ;
- nombre de machines ;
- choix de regle heuristique ;
- activation/desactivation du recuit simule ;
- edition simple des taches ;
- appel API `/schedule` ;
- affichage Gantt ;
- affichage dashboard metriques.

Fichiers concernes :

- `dashboard_sandbox/src/app/simulation/simulation.component.ts`
- `dashboard_sandbox/src/app/simulation/simulation.component.html`
- `dashboard_sandbox/src/app/simulation/simulation.component.css`
- `dashboard_sandbox/src/app/services/api.service.ts`

Deux nouveaux composants Angular ont ete ajoutes :

- `dashboard_sandbox/src/app/components/gantt-chart/gantt-chart.component.ts`
- `dashboard_sandbox/src/app/components/logistics-dashboard/logistics-dashboard.component.ts`

Correction importante :

- `SimulationComponent` a ete remis en composant Angular classique non-standalone, car il est declare dans `AdminLayoutModule`.
- Les composants Gantt et dashboard restent standalone et sont importes dans `AdminLayoutModule`.

### Dependances

`requirements.txt` a ete nettoye pour ne plus inclure les dependances logistiques PPO :

- `stable-baselines3` retire ;
- `gymnasium` retire.

## 3. Etat actuel du serveur backend et du frontend

### Backend

Le backend a ete valide par test local avec une base SQLite temporaire pour eviter de dependre de PostgreSQL pendant le test.

Validation effectuee :

```powershell
$env:DATABASE_URL='sqlite:///:memory:'
backend\venv\Scripts\python.exe -c "... appel test client /schedule ..."
```

Resultat obtenu :

```text
200 success 2
```

Cela confirme que :

- l'app Flask peut etre creee ;
- les routes `/schedule*` sont enregistrees ;
- l'endpoint `/schedule` repond ;
- le moteur logistique produit un Gantt JSON.

Le moteur a aussi ete teste directement avec un CSV logistique :

```text
10 taches planifiees
makespan = 9.0
```

Commande normale pour lancer le backend :

```powershell
cd C:\Users\HP\Desktop\dddm_project_v2\dddm-project\backend
.\venv\Scripts\python.exe main.py
```

Backend attendu :

```text
http://127.0.0.1:5000
```

Remarque : le test client Flask a necessite un petit contournement local a cause d'une incompatibilite entre Flask 2.2.5 et Werkzeug 3.1.3 (`werkzeug.__version__` absent). Ce probleme affecte le test client, pas forcement le lancement normal du serveur.

### Frontend

Le build Angular a ete valide avec optimisation desactivee :

```powershell
cd C:\Users\HP\Desktop\dddm_project_v2\dddm-project\dashboard_sandbox
npm.cmd run build -- --optimization=false
```

Resultat :

```text
Build OK
```

Le build normal :

```powershell
npm.cmd run build
```

a compile le code TypeScript, mais a echoue a l'etape d'inlining des Google Fonts parce que l'environnement n'avait pas acces au reseau :

```text
Inlining of fonts failed ... fonts.googleapis.com ... connect EACCES
```

Ce n'est pas une erreur du plugin logistique.

Commande normale pour lancer Angular :

```powershell
cd C:\Users\HP\Desktop\dddm_project_v2\dddm-project\dashboard_sandbox
npm.cmd start -- --host 127.0.0.1
```

Frontend attendu :

```text
http://127.0.0.1:4200
```

## 4. Prochaines etapes recommandees

### Priorite 1 : verification bout en bout

1. Lancer PostgreSQL et verifier que `DATABASE_URL` pointe vers la bonne base.
2. Lancer Flask avec `backend\venv\Scripts\python.exe main.py`.
3. Lancer Angular avec `npm.cmd start -- --host 127.0.0.1`.
4. Aller sur `http://127.0.0.1:4200`.
5. Uploader un CSV logistique.
6. Verifier la redirection vers `/simulation?plugin=logistic`.
7. Lancer l'ordonnancement.
8. Verifier :
   - diagramme de Gantt ;
   - metriques ;
   - recommandations ;
   - absence d'erreur console navigateur ;
   - insertion en base dans `scheduling_sessions` et `scheduling_results`.

### Priorite 2 : ameliorer l'interface logistique

La simulation logistique fonctionne conceptuellement, mais l'UI peut encore etre amelioree :

- ajouter les colonnes editables `Dependencies`, `SetupTime`, `MachineConstraint` dans le tableau de taches ;
- permettre l'import CSV directement depuis la page simulation ;
- ajouter un bouton reset/exemple ;
- afficher les erreurs de validation de facon plus claire ;
- afficher l'historique `/schedule/history` ;
- ajouter une vue de comparaison entre deux sessions ;
- ajouter un formulaire what-if connecte a `/schedule/simulate`.

### Priorite 3 : robustesse backend

Points a verifier ou renforcer :

- clarifier le conflit potentiel entre `backend/app/models.py` et le dossier `backend/app/models/`.
  - Actuellement `import app.models` charge `backend/app/models/__init__.py`.
  - Les modeles utiles doivent donc rester dans `models/__init__.py`, ou alors il faut restructurer proprement.
- ajouter des tests unitaires pour `SchedulingEngine`.
- ajouter des tests API pour `/schedule`, `/schedule/rules`, `/schedule/simulate`.
- verifier les migrations ou la creation des tables PostgreSQL en environnement reel.
- gerer les erreurs SQLAlchemy avec rollback en cas d'echec.
- verifier la compatibilite Flask 2.2.5 / Werkzeug 3.1.3, ou aligner les versions.

### Priorite 4 : nettoyage du projet

Le `git status` contient beaucoup de fichiers modifies ou generes, notamment :

- `__pycache__/`
- `backend/venv/`
- logs potentiels ;
- fichiers de conversation ;
- donnees de test.

Il faut eviter de commiter les artefacts generes. Ajouter ou verifier `.gitignore` pour :

```text
__pycache__/
*.pyc
backend/venv/
*.log
.env
conversation claude code.txt
```

### Priorite 5 : finance

Le module finance n'etait pas l'objectif principal de cette reprise.

Points connus :

- l'analyse par ticker depend de yfinance ;
- Yahoo Finance peut renvoyer des erreurs 429 Too Many Requests ;
- SHAP doit etre installe pour le plugin finance ;
- la cle API Anthropic/Claude mentionnee dans l'ancienne session avait des problemes 401, mais ce n'est pas bloquant pour la logistique.

