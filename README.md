# LocalGames

Jeux à deux joueurs dans le terminal, sur le même réseau local. **Aucune installation** : seul Python 3.8+ est requis (aucune dépendance externe).

## Jouer

Sur chacun des deux postes :

```bash
python3 play.py        # Linux / macOS  (ou ./play.sh)
python play.py         # Windows        (ou play.bat)
```

1. Entre ton pseudo.
2. Choisis un jeu dans le menu : tu vois qui attend sur chaque jeu.
3. Dès que deux joueurs ont rejoint le même jeu, la partie démarre.
4. Personne ne te rejoint ? Pendant l'attente, appuie sur **1** (facile), **2** (moyen) ou **3** (difficile) pour jouer contre l'ordinateur.

### Comment les postes se trouvent

Le premier à lancer le programme démarre automatiquement un serveur dans un **processus détaché** ; les suivants le détectent par broadcast UDP (port 50505) puis se connectent en TCP (port 50506). Si le pare-feu demande une autorisation sur le poste hôte, accepte-la.

Le serveur est indépendant du premier joueur : celui-ci peut quitter sans interrompre les autres parties. Il s'arrête de lui-même après 60 s sans aucun joueur connecté (tant qu'au moins un joueur est connecté, il reste actif). Plusieurs parties peuvent se dérouler en même temps.

> Si le poste hôte est éteint ou perd le réseau, le serveur disparaît avec lui.

Options utiles :

| Option | Effet |
| --- | --- |
| `--host IP` | se connecter à une IP précise si la détection automatique échoue (réseau qui bloque le broadcast) |
| `--server` | lancer uniquement un serveur dédié, sans interface |
| `--idle-timeout S` | avec `--server` : arrêt après S secondes sans joueur (60 par défaut, `0` pour ne jamais s'arrêter) |
| `--name PSEUDO` | pré-remplir le pseudo |
| `--port N` | port TCP du serveur |

### Éteindre ou redémarrer le serveur

Le serveur s'éteint tout seul 60 s après la déconnexion du dernier joueur. Pour le faire à la main (par exemple après une mise à jour du code : un ancien serveur encore actif ignore les nouvelles fonctions) :

1. Quitte tous les clients (Échap dans le menu).
2. Arrête le serveur :

```bash
pkill -f "localgames --server"                      # Linux / macOS
taskkill /F /IM python.exe                          # Windows : arrête TOUS les processus Python
```

Sous Windows, tu peux aussi le terminer depuis le Gestionnaire des tâches (processus `python.exe`).
Un serveur lancé avec `--server` dans un terminal s'arrête avec Ctrl+C.

3. Redémarre : relance simplement `python3 play.py`, un serveur neuf démarre automatiquement. Pour un serveur dédié : `python3 play.py --server`.

## Jeux

| Jeu | Contrôles |
| --- | --- |
| Morpion | flèches + Entrée, ou touches 1-9 |
| Pong | ↑/↓ (ou W/S) pour déplacer la raquette ; premier à 7 points. Terminal d'au moins 52×22. |

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

## Architecture

```
localgames/
├── protocol.py        # messages JSON (une ligne par message) sur TCP
├── discovery.py       # détection du serveur par broadcast UDP
├── games/             # tout ce qui est propre aux jeux
│   ├── base.py        # contrats : Game, GameView, GameDefinition
│   ├── registry.py    # catalogue des jeux disponibles
│   ├── tictactoe/     # logic.py (règles, serveur) + view.py (affichage, client)
│   └── pong/          # jeu temps réel : le serveur appelle Game.tick() 30 fois par seconde
├── server/            # lobby (pseudos, files d'attente), sessions, serveur TCP
└── client/            # terminal, connexion, écrans (login, menu, partie), boucle
```

Un jeu temps réel (comme Pong) met `real_time = True` et implémente `tick()` : le serveur l'appelle à intervalle fixe et diffuse l'état à chaque pas.

Les règles (`Game`) ne connaissent ni le réseau ni l'affichage ; le serveur est l'unique source de vérité et valide chaque coup.

### Ajouter un jeu

1. Créer `localgames/games/<mon_jeu>/` avec :
   - `logic.py` : une classe héritant de `Game` (`play(player_index, move)` qui lève `InvalidMove`, et `state()` JSON contenant `"over"`) ;
   - `view.py` : une classe héritant de `GameView` (`render(state)` → lignes, `on_key(key, state)` → coup à envoyer ou `None`) ;
   - `__init__.py` : un `GameDefinition(id, name, player_count, create_game, create_view)`.
2. L'ajouter au tuple `GAME_DEFINITIONS` de `games/registry.py`.

Le menu, la file d'attente, le lancement de la partie et le réseau fonctionnent sans autre modification.
