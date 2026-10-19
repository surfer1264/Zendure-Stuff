[:de: Deutsch](readme.md) · [:gb: English](readme_EN.md) · :fr: **Français**

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

# Controller – Premiers pas

Le Controller (`zerooutput_multi_kvs`) est le script de régulation sur ton **Shelly contrôleur**. Il mesure ta consommation réseau et répartit la charge et la décharge entre tes batteries Zendure de sorte que le moins possible vienne du réseau et que rien ne parte inutilisé dans le réseau.

Cette page t'amène jusqu'au **premier fonctionnement**. Comment le contrôler et le modifier ensuite au quotidien est décrit dans [Le Controller au quotidien](benutzerdoku.md) (en allemand), tous les détails sont dans la [documentation complète](gesamtdoku.md) (en allemand). Les dernières modifications figurent dans le [changelog](CHANGELOG.md).

> 🤖 Cette version française a été traduite de l'[original allemand](readme.md) par Claude (l'IA d'Anthropic). En cas de doute ou de contradiction, la version allemande fait foi. Les messages du journal du script sont en allemand et sont cités ici tels quels.

---

## Liste de contrôle avant de commencer

- [ ] **Deux Shelly** Gen2 ou plus récents avec fonction script ([appareils compatibles](../kompatible_geraete_FR.md)) – un pour le Controller, un pour l'API zenDash + Watchdog. Le Controller tourne toujours **seul** sur son Shelly.
- [ ] **Batteries avec zenSDK** (à partir du SolarFlow 800) dans le même réseau, idéalement avec une adresse IP fixe (à régler dans le routeur).
- [ ] **Important :** retirer les batteries du **HEMS** (Home Energy Management System) dans l'application Zendure – sinon le cloud envoie en parallèle ses propres commandes. Exception Zendure Smart Meter D0 : son interface locale est activée une seule fois via le HEMS. Cela ne concerne que le compteur, les batteries restent malgré tout hors du HEMS.
- [ ] Un **compteur intelligent** pour la consommation réseau. Le plus simple : le Controller tourne directement sur un Shelly Pro 3EM.

---

## Configuration avec le configurateur (recommandé)

1. **[Télécharger l'assistant local](https://github.com/surfer1264/Zendure-Stuff/releases/latest)** et le lancer. Le configurateur s'ouvre dans le navigateur.
2. Choisir **« Nouvelle configuration ou mise à jour manuelle »** et répondre aux questions : batteries, source réseau, notifications, paramètres de régulation.
3. Dans le résultat, **« ⚡ Charger directement »**. Le script arrive sur le Shelly contrôleur, démarre et est configuré pour le démarrage automatique.
4. Continuer avec [Démarrer & vérifier](#démarrer--vérifier).

Le guide complet – y compris mise à jour, remplacement d'un Shelly et messages d'erreur – se trouve chez le [configurateur](../Multiconfigurator/readme_FR.md).

---

## Sans le configurateur (à la main)

Uniquement pour ceux qui veulent maintenir leur script eux-mêmes.

### 1. Récupérer le script

Télécharge la version **minifiée** [`zerooutput_multi_kvs_mini.js`](zerooutput_multi_kvs_mini.js). Seule celle-ci peut être chargée dans le Shelly. La version source `zerooutput_multi_kvs_src.js` est destinée à la lecture – elle est trop grande pour le Shelly.

### 2. Adapter le bloc CONFIG

En haut du script se trouve le bloc `let CONFIG = { ... };`. Tu dois adapter au moins ces parties :

**Batteries** – une entrée par appareil Zendure dans `devices`, séparées par des virgules :

```js
devices: [
  {
    ip: "192.168.178.143",   // adresse IP de la batterie
    label: "SF2400",         // nom court pour le journal et les messages
    minSoc: 15,              // réserve en %
    maxSoc: 100,             // objectif de charge en %
    dischargeAllowed: true,  // peut décharger
    reverse: true,           // peut absorber le surplus du réseau
    maxInputPower: 1000,     // puissance de charge max. en W
    maxOutput: 800,          // puissance de décharge max. en W
    dryRun: false            // true = calculer seulement, ne rien écrire (test)
  },
  // ... autres batteries
],
```

Pour le premier fonctionnement, il suffit en général de régler `ip`, `label`, `maxInputPower` et `maxOutput` selon ton appareil. Plus d'infos : [chapitre 4b](gesamtdoku.md#4b-mehrere-solarflow-geräte-einpflegen) (en allemand).

**Compteur intelligent** – `gridSource` :

- `"local"` (par défaut) : le script tourne directement sur un **Shelly Pro 3EM**. Rien d'autre à faire.
- `"remote"` : un **autre** Shelly Pro 3EM dans le réseau, régler en plus `gridSourceIp`.
- `"http_json"` : un compteur avec interface JSON (par ex. Zendure Smart Meter 3CT ou D0, everHome EcoTracker, Tasmota, Shelly 3EM sans Pro), régler en plus `gridSourceUrl` et `gridSourceField`. Champs imbriqués sous forme de tableau, par ex. `["StatusSNS","DVS7420","power"]`. Le configurateur propose des modèles prêts à l'emploi.

Détails : [chapitre 5](gesamtdoku.md#5-smartmeter-anbindung---die-drei-grid-quellen-im-überblick) (en allemand).

**Seuils** – pour démarrer, les valeurs par défaut suffisent. Elles figurent deux fois dans le bloc CONFIG, séparément pour la décharge (`discharge: { ... }`) et la charge (`charge: { ... }`). Pour les avoir tout de suite adaptées ([chapitre 7b](gesamtdoku.md#7b-empfehlung-für-ersteinstellung), en allemand) :

- `spreadAbove` ≈ puissance nominale d'une batterie (par ex. 800 W pour un SF800, 2400 W pour un SF2400)
- `concentrateBelow` ≈ 0,6 × `spreadAbove`

### 3. Charger

1. Ouvrir l'interface web du Shelly contrôleur (`http://<IP-du-Shelly>`) → **Scripts**.
2. Arrêter et supprimer les autres scripts sur ce Shelly – le Controller a besoin de toute la mémoire.
3. Créer un nouveau script (« Create script », sur un firmware plus ancien « Add script »), lui donner un nom, coller le code, **Save**.

À quoi cela ressemble en détail : [Install and Run Shelly Script](https://github.com/surfer1264/Zendure-Stuff/wiki/Install-and-Run-Shelly-Script).

### Pour utilisateurs avancés : avec `deploy.cmd`

Le dossier [Deploy](Deploy) contient des outils (Windows, Python 3 nécessaire) qui insèrent ta propre configuration, minifient le script et le chargent :

1. Dans le dossier `Deploy` (à côté de `deploy.cmd`), **crée toi-même le fichier `myconfig.js`** – il n'est volontairement pas dans le dépôt. Il contient uniquement ton bloc `let CONFIG = { ... };`. Le plus simple est de l'obtenir depuis le [configurateur](../Multiconfigurator/readme_FR.md#les-fonctions-de-létape-résultat) via « 💾 Enregistrer seulement le bloc CONFIG » ; sinon copier le bloc de `zerooutput_multi_kvs_src.js` et l'adapter. Des lignes de commentaire avant ou après ne gênent pas.

    ```js
    // myconfig.js – uniquement le bloc CONFIG
    let CONFIG = {
      devices: [ /* tes batteries */ ],
      gridSource: "local",
      // ... tous les autres réglages
    };
    ```

    `myconfig.js` figure dans le `.gitignore` du dépôt. Ainsi, tes IP et identifiants ne se retrouvent pas par erreur dans un commit.

2. Renseigner dans `deploy.cmd` : `SHELLY_IP` (Shelly contrôleur) et `SKRIPTNAME` (par défaut `ctrl`). `MEINE_CONFIG` pointe déjà sur `myconfig.js` – à modifier seulement si ton fichier porte un autre nom.
3. Lancer `deploy.cmd`. Déroulement : insérer la CONFIG (`swap_config.py`) → minifier (`minify_keep_config.py`) → charger et démarrer (`upload_shelly.py`).

> **Important :** `deploy.cmd` prend toujours le bloc CONFIG de **ton** fichier. Il écrit la version minifiée dans `..\zerooutput_multi_kvs_mini.js` – donc par-dessus le fichier du dépôt. Si tu mets à jour le dossier via Git, ne commite pas cette modification ou fais pointer `FERTIG` vers un fichier à toi. `minify.cmd` crée uniquement la version minifiée sans configuration propre.

---

## Démarrer & vérifier

1. **Démarrer** le script et activer **« Run on startup »** (avec le chargement direct, cela se fait automatiquement). Au premier démarrage, le Controller synchronise une fois `minSoc`/`maxSoc` avec les appareils, puis régule toutes les 4 secondes.
2. Ouvrir le journal et vérifier la bannière de démarrage : elle commence par `Version …` et `Multi-Device Controller gestartet` et affiche d'un coup d'œil toutes les valeurs actives ([chapitre 8.7](gesamtdoku.md#87-startprotokoll-banner), en allemand).
3. Si une ligne comme celle-ci apparaît régulièrement

    ```text
    Netzsaldo: 12 W | Ist-Summe: 340 W | Regelsignal: 352 W | Ladekorrektur: 0 W
    ```

    (solde réseau | somme réelle | signal de régulation | correction de charge)

    ✅ Terminé – le Controller régule.

4. Avec `"http_json"`, **vérifier le signe** une fois : allumer un consommateur important – la valeur réseau dans le journal doit **monter**. Si elle baisse, régler `gridSourceInvert: true`.

Si la consommation réseau reste stable assez longtemps, le Controller signale « Sparmodus » (mode économie) et interroge les batteries moins souvent. C'est normal.

---

## Pour aller plus loin (optionnel)

- Réglages en direct via KVS, par ex. depuis le [tableau de bord](../zendash_watch_API_ZenSDK/dashboard_FR.md) ou Home Assistant – [chapitre 13](gesamtdoku.md#13-live-override-der-regelparameter-per-kvs-z-b-home-assistant) (en allemand)
- Notification Signal/WhatsApp – [chapitre 8.5](gesamtdoku.md#85-signal-benachrichtigung-callmebot--inkl-whatsapp) (en allemand)
- Mode test `dryRun` – [chapitre 4c](gesamtdoku.md#4c-testmodus-dryrun) (en allemand)
- Messages et tableau de bord : [API zenDash + Watchdog](../zendash_watch_API_ZenSDK/readme_FR.md) sur le second Shelly

---

## Comment va le Shelly ?

À ouvrir dans le navigateur, en remplaçant `<IP>` par l'adresse du Shelly :

| Objet | Appel |
| --- | --- |
| Lister les scripts (numéro, nom, état) | `http://<IP>/rpc/Script.List` |
| Mémoire utilisée par un script | `http://<IP>/rpc/Script.GetStatus?id=<numéro>` |
| Temps de fonctionnement, RAM du système | `http://<IP>/rpc/Sys.GetStatus` |

Plus pratique avec l'assistant local : « 🔍 Vérifier la mémoire » et « Enregistrer le journal » dans le [configurateur](../Multiconfigurator/readme_FR.md#7-guides-pratiques).

---

## Ce que contient encore le dossier

| Fichier / dossier | Objet |
|---|---|
| [`zerooutput_multi_kvs_src.js`](zerooutput_multi_kvs_src.js) | version source lisible du Controller |
| [`zerooutput_multi_kvs_mini.js`](zerooutput_multi_kvs_mini.js) | version minifiée à charger |
| [`CHANGELOG.md`](CHANGELOG.md) | modifications par version |
| [`Deploy`](Deploy) | pipeline de déploiement personnelle, voir [plus haut](#pour-utilisateurs-avancés--avec-deploycmd) |
| [`yaml`](yaml) | Exemple pour Home Assistant : lit les valeurs KVS du Controller via REST (`rest.yaml`), les réécrit via `rest_command` (`rest_commands.yaml`) et les met à disposition sous forme de curseurs (`template/kvs.yaml`). Remplacer l'IP `192.168.178.117` par celle de ton Shelly contrôleur. `configuration.yaml` inclut dans Home Assistant le dossier `templates/` (`!include_dir_merge_list templates/`) – c'est là que va le fichier `kvs.yaml` du dossier `template` du dépôt. Contexte : [chapitre 13.6](gesamtdoku.md#136-nutzung-über-home-assistant) (en allemand) |

---

## Téléchargement

**Voir** ouvre le fichier sur GitHub, **Télécharger** fournit le fichier brut. Si le navigateur l'ouvre seulement comme texte : clic droit → « Enregistrer le lien sous … ».

| Fichier | Objet | Liens |
|---|---|---|
| `zerooutput_multi_kvs_mini.js` | à charger sur le Shelly | [Voir](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/zerooutput_multi_kvs_mini.js) · [Télécharger](https://raw.githubusercontent.com/surfer1264/Zendure-Stuff/main/shelly_script/Controller/zerooutput_multi_kvs_mini.js) |
| `zerooutput_multi_kvs_src.js` | version source lisible | [Voir](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/zerooutput_multi_kvs_src.js) · [Télécharger](https://raw.githubusercontent.com/surfer1264/Zendure-Stuff/main/shelly_script/Controller/zerooutput_multi_kvs_src.js) |
| `CHANGELOG.md` | modifications par version | [Voir](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/CHANGELOG.md) · [Télécharger](https://raw.githubusercontent.com/surfer1264/Zendure-Stuff/main/shelly_script/Controller/CHANGELOG.md) |
