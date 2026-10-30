[:de: Deutsch](dashboard.md) · [:gb: English](dashboard_EN.md) · :fr: **Français**

# Installer et utiliser le tableau de bord

[← retour à zenDash API + Watchdog](readme_FR.md)

Le tableau de bord affiche en direct la consommation réseau, l'état de charge et la puissance de vos batteries. Il permet aussi de modifier les réglages du Controller et de charger manuellement une batterie depuis le réseau.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/b6a8b3ed-5828-4f12-9628-eee2a1e03df8" />

**Sommaire**

- [Installer et utiliser le tableau de bord](#installer-et-utiliser-le-tableau-de-bord)
  - [Comment tout cela s'articule](#comment-tout-cela-sarticule)
  - [Utilisation](#utilisation)
    - [Organisation de la page](#organisation-de-la-page)
    - [Verrouiller et déverrouiller](#verrouiller-et-déverrouiller)
    - [Menu « Affichage »](#menu--affichage-)
    - [Ce que vous pouvez régler](#ce-que-vous-pouvez-régler)
    - [Ce qu'affiche l'écran](#ce-quaffiche-lécran)
  - [Quelle variante vous convient ?](#quelle-variante-vous-convient-)
  - [Prérequis](#prérequis)
  - [Le tableau de bord en 4 étapes](#le-tableau-de-bord-en-4-étapes)
  - [En tant que programme sous Windows ou macOS](#en-tant-que-programme-sous-windows-ou-macos)
  - [Fonctionnement permanent sur un Synology](#fonctionnement-permanent-sur-un-synology)
  - [En tant qu'app dans Home Assistant](#en-tant-quapp-dans-home-assistant)
  - [Options de démarrage](#options-de-démarrage)
  - [Bon à savoir](#bon-à-savoir)
  - [En cas de problème](#en-cas-de-problème)

> Les messages de la console du proxy et sa page de configuration sont en allemand. Le tableau de bord lui-même peut être passé en français (bouton DE/EN/FR en haut à droite).

---

## Comment tout cela s'articule

Le navigateur n'a pas le droit d'interroger directement le Shelly – le firmware du Shelly refuse ce type d'accès venant d'une page web étrangère. C'est pourquoi un petit **proxy** tourne sur un ordinateur du réseau domestique : il fournit la page du tableau de bord et interroge le Shelly à la place du navigateur.

```text
Navigateur  ──►  Proxy (PC/NAS/HA/Raspi)  ──►  Shelly tableau de bord (zenDash API)  ──►  Shelly Controller (KVS)
```

---

## Utilisation

Ce qui suit décrit la mise en page par défaut à l'adresse `http://<adresse-du-proxy>:8000/`.

### Organisation de la page

| Zone | Contenu |
|---|---|
| **En-tête** | état de la connexion (p. ex. « En direct · relevé toutes les 4 s »), heure et date, le **cadenas** et le menu **⚙ Affichage** |
| **Vue d'ensemble – Maintenant** | mesures : soutirage/injection réseau et puissance Solarflow (somme de toutes les batteries) avec courbe d'historique |
| **Vue d'ensemble – Régulation** | réglages communs à toutes les batteries : consigne, blocage de décharge et décharge fixe |
| **Appareils** | une carte par batterie avec mesures, état, « Commandes » et « Charge manuelle » |
| **Pied de page** | versions, heure de la dernière actualisation, lien **Aide** (cette page), données brutes et envoi cloud |

Toucher la ligne **« ▾ Vue d'ensemble »** replie la vue d'ensemble. Repliée, elle affiche un résumé, p. ex. `Consigne 0 W · Réseau 12 W · Stockage 340 W` – pratique sur un petit écran quand seules les cartes des appareils comptent. L'état est mémorisé.

### Verrouiller et déverrouiller

La page démarre **verrouillée** – elle ne fait alors qu'afficher, avec la mention « Affichage seul » sous la régulation. Toucher le **cadenas** dans l'en-tête déverrouille les commandes ; l'icône passe à un cadenas ouvert. Après 60 secondes sans saisie, la page se reverrouille d'elle-même, de même après chaque rechargement. C'est prévu pour les tableaux de bord affichés en permanence sur une tablette ou un second écran.

Sur les appareils tactiles, le curseur **Réserve (`minSoc`)** a en plus son propre petit cadenas à côté de la valeur. Il ne libère que ce seul curseur et le reverrouille après 5 secondes sans contact, après l'enregistrement ou lors d'un défilement. La valeur ne change qu'en faisant glisser le point – un appui ou un balayage sur la barre est annulé.

### Menu « Affichage »

| Entrée | Effet |
|---|---|
| **Taille d'affichage** (A1–A4) | texte et commandes en quatre niveaux : Normale, Grande (par défaut), Très grande, Maximale |
| **Mode jour/nuit** | affichage clair ou sombre. Sans basculer, la page suit le réglage de l'appareil. |
| **Langue** | DE → EN → FR. Par défaut : langue du navigateur. |
| **Plein écran** | masque les barres du navigateur ; n'apparaît que si le navigateur le permet |
| **Détails techniques** | affiche les clés KVS (p. ex. `zdmc_setpoint`), les adresses IP et les codes bruts (`acMode`, `socLimit`, `gridReverse`). Sans cet interrupteur, le tableau de bord n'affiche que du texte en clair. |
| **Réinitialiser l'affichage** ↺ | taille, jour/nuit, détails techniques et vue d'ensemble par défaut. La langue est conservée. |
| **Design** ⇄ | bascule entre le tableau de bord classique (`/`) et le nouveau design (`/neu`) |

Toutes les entrées sont mémorisées **par navigateur** – une tablette murale retrouve donc son affichage après un rechargement. Le verrouillage, lui, n'est volontairement pas mémorisé.

### Nouveau design (`/neu`)

`http://<adresse-du-proxy>:8000/neu` propose une alternative au tableau de bord classique. En-tête, vue d'ensemble, régulation, verrouillage et toutes les écritures sont identiques – seule la zone des appareils change, avec en plus l'affichage **Flux d'énergie**. Le sélecteur **Appareils | Flux d'énergie** se trouve à côté du titre ; le choix est mémorisé par navigateur.

- **Cartes des appareils :** état en toutes lettres, puissance en grand, barre de charge avec la réserve (sous `minSoc`) et la zone au-dessus de la limite de charge hachurées, PV · batterie · hors réseau (batterie = PV − sortie − hors réseau), température et cellule la plus faible sur une petite ligne.
- **Remarques** uniquement en cas d'écart (plein/vide bloqué, `socSet`/`minSoc` différent, export interdit, décharge désactivée, charge manuelle active), sinon « Aucune remarque ».
- **Réglages** (interrupteurs, réserve, puissance de charge, charge manuelle) visibles seulement quand les commandes sont déverrouillées ; chaque carte peut être repliée. Les **détails techniques** forment un bloc à part, affiché uniquement avec l'interrupteur du menu.
- **Flux d'énergie :** PV, appareil, batterie, maison, réseau et hors réseau avec des lignes animées (sens, vitesse et épaisseur selon la puissance), pour tous les appareils ou un seul (choix mémorisé par navigateur). Réseau et maison couvrent toujours tous les appareils (maison = solde réseau + somme des sorties). Sur écran étroit, le schéma défile latéralement.

### Ce que vous pouvez régler

Tous les réglages sont envoyés au Controller et prennent effet à son prochain cycle de régulation. Après l'enregistrement, une brève confirmation s'affiche, p. ex. « Enregistré : Batterie 1 · Réserve (minSoc) 20 % ».

**Dans la vue d'ensemble, sous « Régulation »** (pour toutes les batteries ensemble) :

| Commande | Effet | Plage |
|---|---|---|
| **Consigne** | Valeur cible pour le soutirage réseau. Négatif = injecter un peu, positif = soutirer un peu. En dessous figure la tolérance (hystérésis) : l'écart de soutirage toléré avant que le Controller ne corrige. | −40 à +40 W, par pas de 5 W |
| **Blocage de décharge** | Un appareil déchargé jusqu'à la réserve (`minSoc`) ne fournit à nouveau de l'énergie qu'à partir de réserve (`minSoc`) + cette valeur. Évite les commutations permanentes à la réserve (`minSoc`). Après un redémarrage du Controller, le blocage de décharge n'agit qu'une fois la batterie de nouveau déchargée jusqu'à la réserve (`minSoc`) – si l'état de charge se situe entre les deux au démarrage, elle peut d'abord se décharger. Saisir la valeur dans le champ et valider avec ↵ ou « OK » ; les valeurs invalides sont rejetées avec un message. Si la plage limite de charge (`maxSoc`) − réserve (`minSoc`) d'une batterie est inférieure à 14 points, le champ est verrouillé et 3 s'applique. N'agit qu'à partir du Controller 5.2.4 – les versions plus anciennes ignorent la valeur. | 3 à (plus petite plage limite de charge (`maxSoc`) − réserve (`minSoc`) de toutes les batteries) − 11 %, nombres entiers |
| **Décharge fixe** | Puissance de décharge fixe au lieu de la régulation. Saisir la valeur dans le champ et valider avec ↵ ou « OK ». Tant qu'elle est active, la tuile de consigne indique que la consigne n'est pas régulée pour l'instant. | `0` = arrêt, sinon à partir de `dischargeStartupPower` (p. ex. 35 W) |

**Sur chaque carte d'appareil, sous « Commandes » :**

| Commande | Effet | Plage |
|---|---|---|
| **Décharge autorisée** | Cette batterie peut-elle alimenter la maison ? Si le watchdog a bloqué la décharge pour sous-tension, l'interrupteur est sur arrêt et doit être réactivé à la main ([blocage de la décharge](readme_FR.md#blocage-de-la-décharge-en-cas-de-sous-tension)). | marche/arrêt |
| **Charge depuis le réseau autorisée** | Cette batterie peut-elle absorber un surplus venant du réseau ? | marche/arrêt |
| **Réserve (`minSoc`)** | En dessous de cet état de charge, pas de décharge. Est également réglée dans la batterie elle-même. La limite haute est indiquée sous la valeur (« max … % »). Une hausse n'est pas enregistrée si le blocage de décharge ne convient plus ensuite (réserve (`minSoc`) au maximum limite de charge (`maxSoc`) − 11 − blocage de décharge) – un message apparaît et le curseur revient en arrière. Baisser fonctionne toujours. | 10 % jusqu'à 5 points sous la limite de charge effective, c.-à-d. la plus petite des deux limites : limite de charge (`maxSoc`) et limite de charge réglée sur l'appareil (`socSet`) |

**Sur chaque carte d'appareil, sous « Charge manuelle » :**

| Commande | Effet | Plage |
|---|---|---|
| **Puissance de charge réseau** | choisit seulement la puissance, sans effet pour l'instant | 0 à `maxInputPower`, par pas de 50 W |
| **Démarrer / Arrêter la charge manuelle** | démarre ou arrête la charge avec la puissance choisie | – |

Au démarrage, le tableau de bord demande une confirmation, puis désactive « Décharge autorisée » et « Charge depuis le réseau autorisée » pour cette batterie – elle est ainsi retirée de la régulation, et l'indication à côté du bouton affiche « Active à … W ». À l'arrêt, il rétablit l'état précédent. Quand la batterie est pleine, le script arrête la charge de lui-même, même tableau de bord fermé ([arrêt automatique](readme_FR.md#charge-manuelle-et-arrêt-automatique)). Si l'opération est interrompue en cours de route (Shelly injoignable), un avertissement s'affiche – vérifier alors les interrupteurs et la puissance de charge sur la carte.

Après une saisie, la commande concernée est bloquée 4 secondes pour éviter un double déclenchement.

Ne sont pas modifiables dans le tableau de bord : l'**hystérésis** (tolérance autour de la consigne, seulement affichée en dessous – à ne pas confondre avec le blocage de décharge) et la **limite de charge** (`maxSoc`). Les deux se règlent dans le Configurator ou dans le bloc CONFIG.

### Ce qu'affiche l'écran

- **Soutirage / injection réseau :** solde réseau actuel avec le sens (« soutirage » ou « injection ») et comparaison avec la consigne, plus une courbe d'historique des 2 dernières minutes.
- **Puissance Solarflow :** somme de toutes les batteries (+ = fournissent, − = chargent), en dessous l'état de charge moyen (« Charge moy. … % »), également avec courbe d'historique. Les deux courbes ont des échelles différentes et repartent de zéro après un rechargement de la page.
- **Une carte par batterie** avec :
  - le nom et un point d'état (vert = joignable) ; avec « Détails techniques », en plus `[devN]` et l'adresse IP
  - l'état de charge sous forme d'icône de batterie et de nombre, à côté la puissance avec le sens (« fournit », « charge », « veille »)
  - en dessous la plage de travail, p. ex. `Plage 15–100 %` (de la réserve (`minSoc`) à la limite de charge (`maxSoc`))
  - l'entrée PV, la puissance hors réseau (uniquement sur les appareils avec prise hors réseau), la température de l'appareil en °C et la cellule la plus faible (« Cellule min 3,28 V ») – significative seulement sous charge. Pour les batteries surveillées par le watchdog, le seuil de blocage suit, p. ex. « blocage < 2,90 V », et la couleur dépend des seuils du watchdog : jaune sous `minVoltReset`, rouge sous `minVoltWarn`. Sinon : jaune sous 3,0 V, rouge sous 2,8 V.
  - « 100 % : il y a N jours » – quand la batterie a été pleine pour la dernière fois ; un appui affiche la date ([en savoir plus](readme_FR.md#dernière-charge-complète))
  - l'état en clair, p. ex. « injecte », « pleine, charge bloquée », « vide, décharge bloquée », « export interdit ». Il explique les cas les plus fréquents de « Pourquoi la batterie ne fait-elle rien ? ». Avec « Détails techniques », le code brut est affiché devant (`socLimit 1`, `gridReverse 2` …).
  - des indications lorsque l'appareil est réglé autrement que la configuration, p. ex. « Limite de charge 90 % · différent, configuration 100 % » (`socSet` ≠ `maxSoc`) ou « Réserve sur l'appareil 15 % · différent, KVS 20 % ». Le plus souvent, la valeur a été modifiée de l'extérieur (application, Home Assistant).
  - en dessous « Décharge : autorisée · Charge réseau : bloquée », résumé des deux interrupteurs
- **Pied de page :** versions de la page et du script (jaune si elles ne correspondent pas), heure de la dernière actualisation, lien **Aide** vers ce guide. `config_api` et `status_api` ouvrent les données brutes en JSON dans un nouvel onglet. **ThingSpeak** et **ThingsBoard** mènent aux pages de configuration de l'envoi cloud ([ThingSpeak](thingspeak.md), [ThingsBoard](thingsboard.md), en allemand).

**Explications au toucher :** de nombreux libellés et valeurs sont soulignés en pointillés – consigne, blocage de décharge, décharge fixe, les deux tuiles de la vue d'ensemble, puissance, plage de travail, ligne complémentaire, seuil de blocage ; les étiquettes d'état aussi. Un appui (ou le survol à la souris) affiche une courte explication.

La page actualise les mesures toutes les 4 secondes. Les réglages modifiés par quelqu'un d'autre (p. ex. via Home Assistant) apparaissent au plus tard après environ une demi-minute. Tant que l'onglet est en arrière-plan ou la fenêtre réduite, les relevés sont suspendus.

Les détails techniques sur la fréquence d'interrogation, l'interface et les plages de valeurs se trouvent dans la [description de l'API](API.md) (allemand).

---

## Quelle variante vous convient ?

Il existe **un seul** proxy (`zendure_proxy.py`), qui fonctionne partout de la même façon. Seule la manière de le lancer change :

| Variante | Adaptée pour | Lancement | Le navigateur s'ouvre tout seul |
|---|---|---|---|
| **Programme prêt à l'emploi** | Windows ou Mac avec Apple Silicon, sans Python | double-clic | oui |
| **Script Python** | PC, portable, Raspberry Pi | `python3 zendure_proxy.py` | oui (seulement avec écran) |
| **Synology** | fonctionnement permanent sur le NAS | planificateur de tâches | non |
| **Home Assistant** | si vous utilisez déjà Home Assistant OS | comme app à part entière | non |

La mise en service est identique dans tous les cas : lancer le proxy, l'ouvrir dans le navigateur, saisir l'IP et le numéro de script du Shelly tableau de bord sur la page de configuration. Aucun éditeur de texte n'est nécessaire.

Pour un affichage occasionnel, n'importe quel ordinateur suffit. Si le tableau de bord doit être **toujours** accessible, choisissez un appareil qui tourne en permanence : NAS, Home Assistant, Raspberry Pi ou mini-PC. Un portable que l'on referme convient mal.

---

## Prérequis

- Le script [zenDash API + Watchdog](readme_FR.md) tourne sur votre Shelly tableau de bord, avec **`api.enabled: true`**.
- Pour pouvoir aussi **régler** depuis le tableau de bord (consigne, réserve, charge manuelle …), `kvsEnabled: true` et `kvsForceReseed: false` doivent être définis dans le Controller. Sans KVS, le tableau de bord ne fait qu'afficher.
- Pour le script Python et le Synology : **Python 3.7 ou plus récent** ([python.org](https://www.python.org/downloads/)). Rien d'autre à installer.
- Sauf pour le programme prêt à l'emploi, les deux fichiers de [ce dossier](.) :
  - [`zendure_proxy.py`](zendure_proxy.py) – le proxy
  - [`zendure-dashboard.html`](zendure-dashboard.html) – la page du tableau de bord

  Le fichier HTML peut se trouver **dans le même dossier** que le proxy ou **un niveau au-dessus**. S'il y en a un aux deux endroits, celui du même dossier l'emporte.

> **Important :** la page du tableau de bord et le script sur le Shelly doivent avoir **le même numéro de version**. Si vous mettez à jour le script, récupérez aussi le `zendure-dashboard.html` correspondant (ou le nouveau programme). Si les versions divergent, l'indication dans le pied de page du tableau de bord devient jaune.

---

## Le tableau de bord en 4 étapes

**1. Relever le numéro du script**

Le proxy doit savoir à quelle adresse IP se trouve le Shelly tableau de bord et quel numéro y porte le script. Dans l'interface web du Shelly tableau de bord, sous **Scripts**, figure le numéro (p. ex. `id: 1`). Téléversé via le Configurator, le script s'appelle `zd`.

**2. Tester rapidement si le script répond**

Ouvrir directement dans le navigateur (remplacer IP et numéro) :

```link
http://<IP-du-Shelly-tableau-de-bord>/script/<numéro-du-script>/status_api
```

Une ligne de données doit apparaître. En cas d'erreur, le script ne tourne pas ou le numéro est faux.

**3. Lancer le proxy**

Programme prêt à l'emploi : double-clic (voir [plus bas](#en-tant-que-programme-sous-windows-ou-macos)). Script Python : ouvrir un terminal (Windows : invite de commandes) dans le dossier contenant les fichiers et lancer :

```bash
python3 zendure_proxy.py
```

Sous Windows, la commande s'appelle souvent `python` ou `py` au lieu de `python3`. La fenêtre doit rester ouverte tant que le tableau de bord est utilisé ; arrêt avec `Ctrl+C`.

Au démarrage, le proxy affiche un bref résumé (en allemand) :

```text
Zendure Dashboard Proxy
  Shelly:   noch nicht eingerichtet - Einrichtungsseite oeffnet automatisch
  HTML:     /home/pi/zendure/zendure-dashboard.html
  Konfig:   /home/pi/zendure/zendure_proxy_config.json
  Lokal:    http://localhost:8000/
  Im Netz:  http://192.168.178.21:8000/  (von jedem Rechner im selben Netzwerk)
(Strg+C zum Beenden)
```

- **Shelly** – « noch nicht eingerichtet » signifie pas encore configuré ; la page de configuration s'ouvre automatiquement.
- **HTML** indique quel fichier de tableau de bord a été trouvé.
- **Konfig** indique où les réglages sont enregistrés.
- **Im Netz** (« sur le réseau ») est l'adresse pour le téléphone, la tablette et les autres ordinateurs.

Sur un ordinateur avec écran, le navigateur s'ouvre automatiquement.

**4. Configurer**

Lors du premier accès à `http://localhost:8000/`, c'est la **page de configuration** qui s'affiche à la place du tableau de bord. Saisissez-y :

- **Shelly-IP** – l'IP du **Shelly tableau de bord** (pas celle du Shelly Controller !)
- **Script-ID** – le numéro de l'étape 1

Un clic sur **« Speichern & testen »** (enregistrer et tester) vérifie immédiatement que le script répond bien à cette adresse. En cas de faute de frappe, un message d'erreur s'affiche et rien n'est enregistré. Si le test réussit, la page bascule directement vers le tableau de bord.

Les réglages sont enregistrés dans le fichier `zendure_proxy_config.json` à côté du proxy. Au prochain démarrage, ils sont toujours là – la configuration n'est donc nécessaire qu'une fois. Vous pouvez les modifier à tout moment sous :

```link
http://<adresse-du-proxy>:8000/setup
```

Le tableau de bord est ensuite accessible depuis tout autre appareil du réseau domestique – avec l'adresse de la ligne **« Im Netz »**, p. ex. `http://192.168.178.21:8000/`.

- toujours `http://`, pas `https://`
- la page démarre **verrouillée** – le cadenas en haut à droite déverrouille les commandes
- si Windows pose la question du pare-feu au premier lancement : **« Autoriser l'accès »** (réseau privé)

---

## En tant que programme sous Windows ou macOS

Pour les ordinateurs sans Python, le proxy existe en programme prêt à l'emploi. La page du tableau de bord y est déjà intégrée – vous n'avez besoin que de ce seul fichier :

- [Windows](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-windows.exe)
- [macOS](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-macos) – uniquement les Mac avec Apple Silicon (M1 ou plus récent)

1. Placer le fichier dans un **dossier dédié** où vous avez les droits d'écriture, p. ex. `C:\Users\<nom>\zendure\`. Pas sous `C:\Program Files` : le proxy ne peut pas y enregistrer ses réglages.
2. Lancer par **double-clic**. Une fenêtre de console s'ouvre (la laisser ouverte), ainsi que le navigateur avec la page de configuration.
3. Si Windows SmartScreen met en garde contre une application inconnue : **« Informations complémentaires » → « Exécuter quand même »**. Sous macOS, les mêmes étapes que pour l'assistant s'appliquent – voir le [guide macOS](../Multiconfigurator/local_helper/mcos_helper.md) (allemand ; y utiliser le nom de fichier `zendure_proxy-macos`).
4. Si le pare-feu Windows le demande : **« Autoriser l'accès »** (réseau privé), sinon le tableau de bord n'est pas accessible depuis le téléphone.
5. Configurer comme décrit à l'[étape 4](#le-tableau-de-bord-en-4-étapes). Le fichier `zendure_proxy_config.json` est créé à côté du programme.

Arrêt : fermer la fenêtre de console ou `Ctrl+C`.

Pour chaque fichier, la [page des releases](https://github.com/surfer1264/Zendure-Stuff/releases/latest) propose un fichier `.sha256` de contrôle – comme décrit pour l'assistant sous [Vérifier l'intégrité du téléchargement](../Multiconfigurator/readme_FR.md#vérifier-lintégrité-du-téléchargement).

---

## Fonctionnement permanent sur un Synology

1. **Vérifier Python.** DSM en fournit généralement un :

    ```bash
    which python3 && python3 --version
    ```

    La version 3.7 ou plus suffit – le proxy n'utilise que la bibliothèque standard. L'interpréteur se trouve souvent sous `/bin/python3`. Si rien ne s'affiche, installer **Python 3** depuis le Centre de paquets ; le chemin est alors `/var/packages/Python3*/target/bin/python3`.

2. **Déposer les fichiers.** `zendure_proxy.py` dans un dossier dédié, p. ex. `/volume1/homes/<utilisateur>/zendure`, et `zendure-dashboard.html` à côté ou un niveau au-dessus. Pas dans le dossier `web` – il appartient à Web Station.
3. **Créer une tâche.** Panneau de configuration → Planificateur de tâches → Créer → **Tâche déclenchée** → Script défini par l'utilisateur. Événement **Démarrage**, utilisateur **root**, et comme commande le chemin complet :

    ```bash
    /bin/python3 /volume1/homes/<utilisateur>/zendure/zendure_proxy.py -q
    ```

4. **Lancer tout de suite**, sans redémarrer : sélectionner la tâche → **Exécuter**.
5. **Pare-feu.** S'il est actif sous Panneau de configuration → Sécurité → Pare-feu, créer une règle pour TCP **8000**. Le port 8000 n'entre pas en conflit avec DSM lui-même (5000/5001).
6. **Configurer.** Depuis un PC ou un téléphone, ouvrir `http://<IP-du-Synology>:8000/` et saisir IP et numéro de script comme à l'[étape 4](#le-tableau-de-bord-en-4-étapes).

La tâche reste affichée en permanence comme « en cours », car le proxy ne se termine pas. C'est normal.

Comme la tâche tourne en tant que `root`, le fichier `zendure_proxy_config.json` créé appartient aussi à `root`. Cela n'a aucune importance pour le fonctionnement ; seule la suppression ou la modification manuelle ultérieure du fichier nécessite des droits d'administrateur.

Le planificateur lance la tâche au démarrage, mais **ne la relance pas si le processus plante**. Si vous le souhaitez, utilisez à la place un conteneur dans Container Manager (`python:3-slim`, dossier monté en volume, port 8000, politique de redémarrage « toujours »). Les réglages sont alors enregistrés dans le dossier monté et survivent même à la recréation du conteneur.

---

## En tant qu'app dans Home Assistant

Si vous utilisez Home Assistant OS, vous pouvez y faire tourner le proxy comme app à part entière. Il démarre alors avec Home Assistant et est relancé automatiquement en cas de plantage.

👉 **[Guide de l'app Home Assistant](HA_zendure_proxy/INSTALLATION.md)** (allemand)

[![Ajouter le dépôt à Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fsurfer1264%2Fha-zendure-apps)

En bref : ajouter le dépôt `https://github.com/surfer1264/ha-zendure-apps` dans la boutique d'apps (bouton ci-dessus), installer l'app « Zendure Dashboard Proxy », la démarrer, ouvrir `http://<IP-de-Home-Assistant>:8000/` et configurer comme à l'[étape 4](#le-tableau-de-bord-en-4-étapes). Home Assistant propose ensuite lui-même les nouvelles versions comme mises à jour.

> **Attention :** les réglages se trouvent dans le stockage permanent de l'app et survivent aux mises à jour. Installez donc toujours les nouvelles versions via **Mettre à jour** – si l'app est désinstallée puis réinstallée, la configuration est à refaire une fois.

---

## Options de démarrage

Valable pour le script Python (et pour le programme si vous le lancez depuis une console) :

| Option | Effet |
|---|---|
| *(aucune)* | normal, avec une ligne de journal par requête |
| `-q` | discret : résumé de démarrage oui, journal non – pratique en fonctionnement permanent |
| `-s` | silencieux : aucune sortie (les erreurs s'affichent quand même) |
| `--browser` | toujours ouvrir le navigateur au démarrage |
| `--no-browser` | ne jamais ouvrir le navigateur au démarrage |
| `--bericht=CHEMIN` | emplacement de `bericht.html` (fichier ou dossier) pour `/bericht_zendure`, voir ci-dessous |
| `-h` | afficher l'aide |

Sans `--browser`/`--no-browser`, le proxy décide lui-même : sous Windows, macOS et sur un bureau Linux, il ouvre le navigateur ; sur un Synology, dans Home Assistant ou dans une session SSH, non.

Le port (`PORT`, 8000 par défaut) et l'interface réseau (`BIND_ADDRESS`) se règlent si besoin en haut du script Python.

### Rapport de l'analyse des journaux

Le proxy affiche aussi le rapport de l'[analyse des journaux](../stat/auswertung/readme.md) (`bericht.html` produit par `analyse.py`) :

```
http://<adresse-du-proxy>:8000/bericht_zendure
```

L'analyse elle-même ne tourne pas dans le proxy. Il cherche le fichier `bericht.html` déjà généré :

1. à l'emplacement indiqué par `--bericht=CHEMIN` ou la variable d'environnement `ZENDURE_BERICHT` (fichier ou dossier) – alors uniquement là,
2. sinon à côté de `zendure-dashboard.html`, à côté de sa configuration, à côté du script ou du programme, et dans le dossier `stat/auswertung` du dépôt.

Dans l'app Home Assistant, placez le fichier sous `/share/zendure/bericht.html`. Un rapport nouvellement généré s'affiche au prochain appel, sans redémarrage. Le résumé de démarrage du proxy indique quel fichier il a trouvé.

Si le proxy trouve un rapport, le tableau de bord affiche le lien **« Analyse : rapport des journaux »** en bas de page. Sans rapport, le lien n'apparaît pas.

---

## Bon à savoir

- **Pas de mot de passe :** toute personne du réseau domestique connaissant l'adresse peut ouvrir le tableau de bord et modifier les réglages – y compris l'adresse du Shelly sous `/setup` – et lire le rapport sous `/bericht_zendure`. Ne **jamais** exposer le proxy sur Internet par une redirection de port.
- **Numéro du script :** lors d'une **mise à jour** via le Configurator, le numéro reste le même. Si le script est **recréé** (première installation, « supprimer les autres », changement de Shelly ou téléversement manuel), il reçoit un nouveau numéro. Si le tableau de bord ne fonctionne plus ensuite, saisir le nouveau numéro sous `http://<adresse-du-proxy>:8000/setup`. Pas besoin de redémarrer le proxy.
- **Mise en page :** à l'adresse `http://<adresse-du-proxy>:8000/`, le tableau de bord utilise désormais la nouvelle mise en page – structure plus claire, bouton de verrouillage bien visible, état en langage courant, vue d'ensemble repliable, détails techniques (clés KVS, adresses IP) seulement sur demande via le menu « Affichage ». Les réglages choisis y sont mémorisés – voir [Utilisation](#utilisation). L'ancienne mise en page sous `/b` a été supprimée en 3.5.12 ; l'adresse redirige vers le tableau de bord.
- **Nouvelle version du tableau de bord :** avec le script Python et sur le Synology, il suffit de remplacer `zendure-dashboard.html` et de recharger la page dans le navigateur – le proxy relit le fichier à chaque requête. Dans le programme prêt à l'emploi, la page est intégrée ; elle arrive avec un nouveau téléchargement. Dans Home Assistant, l'app doit être reconstruite.

---

## En cas de problème

| Symptôme | Solution |
|---|---|
| Page vide, « Failed to fetch » | Le fichier HTML a été ouvert par double-clic. Toujours l'ouvrir via `http://localhost:8000/`. |
| La page de configuration s'affiche au lieu du tableau de bord | Le proxy n'est pas encore configuré, ou `zendure_proxy_config.json` manque ou est endommagé. Il suffit de refaire la configuration. |
| « Speichern & testen » signale une erreur | IP ou numéro de script incorrect – vérifier avec le test de l'[étape 2](#le-tableau-de-bord-en-4-étapes). L'IP doit être celle du **Shelly tableau de bord**. |
| Message rouge « Erreur au chargement de la configuration » | Le Shelly n'est pas (ou plus) joignable, ou le numéro de script a changé – vérifier sous `/setup`. |
| L'indication de version dans le pied de page est jaune | La page du tableau de bord et le script ont des versions différentes. Récupérer le `zendure-dashboard.html` correspondant ou le nouveau programme. |
| 404 sous `http://localhost:8000/` | `zendure-dashboard.html` ne se trouve ni à côté du proxy ni un niveau au-dessus. Au démarrage, le proxy liste tous les emplacements où il a cherché. |
| Impossible d'enregistrer la configuration | Le proxy n'a pas le droit d'écrire dans son dossier (p. ex. sous `C:\Program Files`). Choisir un dossier avec droits d'écriture. |
| Les réglages n'ont aucun effet | Définir `kvsEnabled: true` dans le Controller. |
| Réglages perdus après redémarrage du Controller | Définir `kvsForceReseed: false` dans le Controller. |
| Inaccessible depuis le téléphone | `http://` au lieu de `https://`, bonne IP de la ligne « Im Netz », vérifier l'autorisation du pare-feu. |
| Rien n'est utilisable | La page est verrouillée – toucher le cadenas dans l'en-tête. |
| Clés KVS, adresses IP ou `acMode`/`socLimit` absents | Activer les **Détails techniques** dans le menu « Affichage ». |
| « Konnte Port 8000 nicht oeffnen » (impossible d'ouvrir le port 8000) | Le proxy tourne déjà (p. ex. dans une deuxième fenêtre), ou un autre programme occupe le port. |
