[:de: Deutsch](dashboard.md) · [:gb: English](dashboard_EN.md) · :fr: **Français**

# Installer et utiliser le tableau de bord

[← retour à zenDash API + Watchdog](readme_FR.md)

Le tableau de bord affiche en direct la consommation réseau, l'état de charge et la puissance de vos batteries. Il permet aussi de modifier les réglages du Controller et de charger manuellement une batterie depuis le réseau.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/576c25b9-15c4-432d-8fa4-969413884aa1" />


**Sommaire**

- [Comment tout cela s'articule](#comment-tout-cela-sarticule)
- [Quelle variante vous convient ?](#quelle-variante-vous-convient-)
- [Prérequis](#prérequis)
- [Le tableau de bord en 4 étapes](#le-tableau-de-bord-en-4-étapes)
- [En tant que programme sous Windows ou macOS](#en-tant-que-programme-sous-windows-ou-macos)
- [Fonctionnement permanent sur un Synology](#fonctionnement-permanent-sur-un-synology)
- [En tant qu'app dans Home Assistant](#en-tant-quapp-dans-home-assistant)
- [Options de démarrage](#options-de-démarrage)
- [Bon à savoir](#bon-à-savoir)
- [En cas de problème](#en-cas-de-problème)
- [Utilisation](#utilisation)

> Les messages de la console du proxy et sa page de configuration sont en allemand. Le tableau de bord lui-même peut être passé en français (bouton DE/EN/FR en haut à droite).

---

## Comment tout cela s'articule

Le navigateur n'a pas le droit d'interroger directement le Shelly – le firmware du Shelly refuse ce type d'accès venant d'une page web étrangère. C'est pourquoi un petit **proxy** tourne sur un ordinateur du réseau domestique : il fournit la page du tableau de bord et interroge le Shelly à la place du navigateur.

```
Navigateur  ──►  Proxy (PC/NAS/HA/Raspi)  ──►  Shelly tableau de bord (zenDash API)  ──►  Shelly Controller (KVS)
```

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

```
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

```
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

```
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

👉 **[Guide de l'app Home Assistant](HA_zendure_proxy/readme.md)** (allemand)

En bref : installer l'app depuis le dossier local, la démarrer, ouvrir `http://<IP-de-Home-Assistant>:8000/` et configurer comme à l'[étape 4](#le-tableau-de-bord-en-4-étapes).

> **Attention :** dans Home Assistant, les réglages se trouvent dans le conteneur de l'app. Si l'app est désinstallée puis réinstallée (p. ex. pour une nouvelle version du tableau de bord), la configuration est à refaire une fois.

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
| `-h` | afficher l'aide |

Sans `--browser`/`--no-browser`, le proxy décide lui-même : sous Windows, macOS et sur un bureau Linux, il ouvre le navigateur ; sur un Synology, dans Home Assistant ou dans une session SSH, non.

Le port (`PORT`, 8000 par défaut) et l'interface réseau (`BIND_ADDRESS`) se règlent si besoin en haut du script Python.

---

## Bon à savoir

- **Pas de mot de passe :** toute personne du réseau domestique connaissant l'adresse peut ouvrir le tableau de bord et modifier les réglages – y compris l'adresse du Shelly sous `/setup`. Ne **jamais** exposer le proxy sur Internet par une redirection de port.
- **Numéro du script :** lors d'une **mise à jour** via le Configurator, le numéro reste le même. Si le script est **recréé** (première installation, « supprimer les autres », changement de Shelly ou téléversement manuel), il reçoit un nouveau numéro. Si le tableau de bord ne fonctionne plus ensuite, saisir le nouveau numéro sous `http://<adresse-du-proxy>:8000/setup`. Pas besoin de redémarrer le proxy.
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
| Rien n'est utilisable | La page est verrouillée – toucher le cadenas en haut à droite. |
| « Konnte Port 8000 nicht oeffnen » (impossible d'ouvrir le port 8000) | Le proxy tourne déjà (p. ex. dans une deuxième fenêtre), ou un autre programme occupe le port. |

---

## Utilisation

La page démarre **verrouillée**. Le cadenas en haut à droite déverrouille les commandes ; après 60 secondes sans saisie, elle se verrouille d'elle-même. C'est prévu pour les tableaux de bord affichés en permanence sur une tablette ou un second écran.

### Ce que vous pouvez régler

Tous les réglages sont envoyés au Controller et prennent effet à son prochain cycle de régulation.

| Commande | Effet | Plage |
|---|---|---|
| **Consigne** | Valeur cible pour le soutirage réseau. Négatif = injecter un peu, positif = soutirer un peu. | −40 à +40 W |
| **Décharge fixe** | Puissance de décharge fixe au lieu de la régulation, pour toutes les batteries ensemble. `0` = arrêt, régulation normale. | 0 ou à partir de `dischargeStartupPower` |
| **Décharge autorisée** | Cette batterie peut-elle alimenter la maison ? Si le watchdog a bloqué la décharge pour sous-tension, l'interrupteur est sur arrêt et doit être réactivé à la main ([blocage de la décharge](readme_FR.md#blocage-de-la-décharge-en-cas-de-sous-tension)). | marche/arrêt |
| **Charge depuis le réseau autorisée** | Cette batterie peut-elle absorber un surplus venant du réseau ? | marche/arrêt |
| **Réserve (SoC min.)** | En dessous de cet état de charge, pas de décharge. Est également réglée dans la batterie elle-même. Sur les appareils tactiles, le curseur a son propre petit cadenas à côté de la valeur et ne réagit qu'en faisant glisser le point, pour éviter tout réglage involontaire. | 10 % jusqu'à 1 % sous la plus petite des deux limites : objectif de charge (`maxSoc`) et limite de charge réglée sur l'appareil (`socSet`) |
| **Charge manuelle** | Charge cette batterie depuis le réseau avec la puissance choisie, jusqu'à ce que vous l'arrêtiez ou que la batterie soit pleine. | 0 à `maxInputPower` |

La **charge manuelle** se compose de deux parties : le curseur choisit seulement la puissance, le bouton en dessous démarre ou arrête la charge. Au démarrage, le tableau de bord désactive « Décharge autorisée » et « Charge depuis le réseau autorisée » pour cette batterie ; à l'arrêt, il rétablit l'état précédent. Quand la batterie est pleine, le script arrête la charge de lui-même ([arrêt automatique](readme_FR.md#charge-manuelle-et-arrêt-automatique)). Si l'opération est interrompue en cours de route (Shelly injoignable), un avertissement s'affiche – vérifier alors la carte de la batterie.

Après une saisie, la commande concernée est bloquée 4 secondes pour éviter un double déclenchement.

Ne sont pas modifiables dans le tableau de bord : l'**hystérésis** (seulement affichée à côté de la consigne) et l'**objectif de charge** (`maxSoc`). Les deux se règlent dans le Configurator ou dans le bloc CONFIG.

### Ce qu'affiche l'écran

- **En haut :** solde réseau et somme des batteries, chacun avec une petite courbe d'historique des 2 dernières minutes. Les deux courbes ont des échelles différentes. Après un rechargement de la page, elles repartent de zéro.
- **À côté de la consigne** figure l'hystérésis : l'écart de soutirage toléré avant que le Controller ne corrige.
- **Une carte par batterie** avec :
  - l'état de charge et en dessous la plage de travail, p. ex. `SoC · 15–100 %` (de la réserve à l'objectif de charge)
  - la puissance, l'entrée PV, la puissance hors réseau (uniquement sur les appareils avec prise hors réseau), la température de l'appareil en °C et la tension de la cellule la plus faible – significative seulement sous charge. Pour les batteries surveillées par le watchdog, le seuil de blocage suit, p. ex. « min 3,31 V (blocage < 2,90 V) », et la couleur dépend des seuils du watchdog : jaune sous `minVoltReset`, rouge sous `minVoltWarn`. Sinon : jaune sous 3,0 V, rouge sous 2,8 V.
  - des indications lorsque l'appareil est réglé autrement que la configuration : `socSet` (limite de charge haute sur l'appareil) diffère de `maxSoc`, ou `minSoc` sur l'appareil diffère de la réserve dans la KVS. Le plus souvent, la valeur a été modifiée de l'extérieur (application, Home Assistant). Toucher l'indication explique comment y remédier.
  - « 100 % : il y a N jours » – quand la batterie a été pleine pour la dernière fois ([en savoir plus](readme_FR.md#dernière-charge-complète))
  - l'état brut `acMode`, `socLimit`, `gridReverse`. Il explique les cas les plus fréquents de « Pourquoi la batterie ne fait-elle rien ? » : `socLimit 1` = batterie pleine, charge bloquée ; `socLimit 2` = décharge bloquée ; `gridReverse 2` = injection bloquée.
- **Pied de page :** versions de la page et du script. Jaune si elles ne correspondent pas.

La page actualise les mesures toutes les 4 secondes. Les réglages modifiés par quelqu'un d'autre (p. ex. via Home Assistant) apparaissent au plus tard après environ une demi-minute.

### Boutons en haut à droite

| Bouton | Effet |
|---|---|
| 🔒 Cadenas | déverrouiller / verrouiller les commandes |
| DE/EN/FR | changer de langue (par défaut : langue du navigateur) |
| Clair/Sombre | affichage jour ou nuit. Sans basculer, la page suit le réglage de l'appareil. |
| A | taille du texte en trois niveaux : Normale, Grande (par défaut), Très grande |
| ⛶ | plein écran (seulement si le navigateur le permet) |

Les détails techniques sur la fréquence d'interrogation, l'interface et les plages de valeurs se trouvent dans la [description de l'API](API.md) (allemand).
