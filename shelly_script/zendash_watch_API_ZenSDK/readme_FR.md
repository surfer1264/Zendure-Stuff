# zenDash API + Watchdog

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

🌐 [Deutsch](readme.md) · [English](readme_EN.md) · **Français**

Un script Shelly pour votre **Shelly tableau de bord**, qui assure deux tâches autour de vos batteries Zendure :

- **API pour le tableau de bord** – Le [tableau de bord](dashboard.md) (allemand) affiche par ce biais la consommation réseau, l'état de charge et la puissance de vos batteries. Vous pouvez aussi modifier les réglages du Controller et lancer une charge manuelle.
- **Watchdog** – Le script vous prévient par Signal, WhatsApp ou webhook lorsqu'une batterie est pleine, devient trop chaude, qu'une cellule a une tension trop basse ou qu'une batterie n'est plus joignable. Vous recevez en plus un court récapitulatif le matin et le soir.

Les deux parties peuvent être activées et désactivées séparément. Un seul script interroge les batteries et partage les données entre les deux tâches – cela économise la mémoire du Shelly et ménage vos appareils Zendure. Auparavant, il s'agissait de deux scripts séparés (zenDash API 2.x et AkkuVolt Watchdog 1.x) qui, ensemble, atteignaient la limite de mémoire du Shelly selon le nombre de batteries.

La version actuelle et toutes les modifications figurent dans le [changelog](CHANGELOG.md).

---

## Sommaire

- [Ce dont vous avez besoin](#ce-dont-vous-avez-besoin)
- [Fonctionnement du script](#fonctionnement-du-script)
- [Installation](#installation)
- [Configuration](#configuration)
- [Tableau de bord](#tableau-de-bord)
- [Messages](#messages)
- [Charge manuelle et arrêt automatique](#charge-manuelle-et-arrêt-automatique)
- [Dernière charge complète](#dernière-charge-complète)
- [Passer des anciens scripts](#passer-des-anciens-scripts)
- [Besoin en mémoire](#besoin-en-mémoire)
- [Dépannage](#dépannage)

---

## Ce dont vous avez besoin

- **Un Shelly dédié** avec fonction script (génération 2 ou plus récente : Plus, Pro, Gen3 …). Le script tourne toujours sur un autre Shelly que le Controller – les deux ensemble ne tiennent pas dans la mémoire d'un seul Shelly.
- **Des batteries Zendure avec interface locale** (zenSDK), joignables à l'adresse `http://<IP-de-la-batterie>/properties/report`. Testé avec SolarFlow 2400 Pro et SolarFlow 800.
- **Le [Controller](../Controller/readme.md)** (allemand) sur votre Shelly contrôleur si vous voulez utiliser le tableau de bord. Le tableau de bord lit et écrit ses réglages. Si vous n'utilisez que le watchdog, vous n'en avez pas besoin.
- **Pour les messages** (facultatif) :
  - Signal ou WhatsApp : une clé API gratuite de [CallMeBot](https://www.callmebot.com)
  - ou un webhook, par exemple dans Home Assistant

> **Remarque :** **aucune protection par mot de passe** ne doit être active sur le Shelly contrôleur. Sinon, ce script ne peut pas y lire ni écrire les réglages.

---

## Fonctionnement du script

Le script adapte son rythme selon que quelqu'un regarde ou non :

| Situation | Ce qui se passe |
|---|---|
| **Le tableau de bord est ouvert** | Le compteur réseau et toutes les batteries sont interrogés toutes les 8 secondes. Le watchdog vérifie ces valeurs en même temps. |
| **Une charge manuelle est en cours** | Également toutes les 8 secondes, même si le tableau de bord est fermé. Le script détecte ainsi quand la batterie est pleine. |
| **Personne ne regarde** | Seul le watchdog interroge les batteries surveillées toutes les 120 secondes. Le compteur réseau n'est pas interrogé. |

Les requêtes, écritures et messages s'exécutent toujours **l'un après l'autre**, jamais simultanément. Cela maintient un faible besoin en mémoire sur le Shelly.

---

## Installation

### Recommandé : avec le Configurator

Le [Configurator](../Multiconfigurator/readme_FR.md) demande tout ce qu'il faut, reprend la liste des appareils, la source réseau et les notifications depuis la configuration du Controller, puis téléverse le script directement sur votre Shelly tableau de bord avec l'assistant (nom du script `zd`). Les mises à jour se font aussi de cette façon.

### Manuellement via l'interface web du Shelly

1. Télécharger la version **minifiée** [`zendash_watch_mini.js`](zendash_watch_mini.js). Seule celle-ci tient dans le Shelly – `zendash_watch_src.js` est la version source lisible.
2. Adapter le bloc `let CONFIG = { ... };` (voir [Configuration](#configuration)).
3. Ouvrir l'interface web du Shelly tableau de bord (`http://<IP-du-Shelly>`) → **Scripts**. Arrêter et supprimer les autres scripts sur ce Shelly.
4. Créer un nouveau script (« Create script », « Add script » sur les anciens firmwares), lui donner un nom (p. ex. `zd`), coller le code, **Save**, puis **Start**.
5. Activer **« Run on startup »** pour que le script redémarre tout seul après une coupure de courant.

### Pour les utilisateurs avancés : avec `deploy.cmd`

Le dossier [Deploy](Deploy) contient des outils qui insèrent votre propre configuration, réduisent le script et le téléversent :

1. Placer votre configuration dans un fichier séparé, par exemple `myconfig_zenDash_watch.js`. Il ne contient que le bloc `let CONFIG = { ... };`.
2. Renseigner dans `deploy.cmd` : l'IP du Shelly, le nom du script, `QUELLE=..\zendash_watch_src.js` et `MEINE_CONFIG=myconfig_zenDash_watch.js`.
3. Lancer `deploy.cmd`.

> **Important :** `deploy.cmd` prend toujours le bloc CONFIG de **votre** fichier. Les modifications faites directement dans `zendash_watch_src.js` seront écrasées.

### Après le démarrage

Un récapitulatif apparaît dans le journal du script (les sorties du script sont en allemand). Vérifiez que tout est réglé comme vous le souhaitez :

```
--------------------------------
zenDash-API + Watchdog v3.4.1 (Dashboard muss ebenfalls v3.4.1 sein)
Module     : API AN | Watchdog AN
Geraete    : SF2400[W] SF800[W]
Watchdog   : alle 120 s, Offline-Alarm nach 10 min
Nachrichten: SIGNAL -> callmebot | Debug: AUS
--------------------------------
```

`[W]` derrière un appareil signifie : le watchdog le surveille. Le numéro de version est celui de votre script ; le tableau de bord doit avoir la même version.

Si les messages sont activés, vous recevez aussi le message **« ✅ zenDash/Watchdog v… gestartet »** (démarré). Vous savez ainsi immédiatement que l'envoi des messages fonctionne.

---

## Configuration

Tous les réglages se trouvent en haut du script dans le bloc `let CONFIG = { ... }`. Si vous utilisez le Configurator, vous n'avez rien à modifier ici à la main.

### Appareils (`devices`)

Saisissez **les mêmes batteries que dans le Controller** – mêmes adresses IP, **même ordre**. L'ordre est important : le premier appareil est « appareil 0 » dans le Controller, le deuxième « appareil 1 », et ainsi de suite.

```js
devices: [
  {
    ip: "192.168.178.143",
    label: "SF2400",
    minSoc: 15,
    maxSoc: 100,
    dischargeAllowed: true,
    reverse: true,
    maxInputPower: 1000,
    maxOutput: 800,
    inputLimit: 0,
    watch: true          // true = le watchdog surveille cet appareil
  },
  // ... autres appareils
],
```

| Réglage | Signification |
|---|---|
| `ip` | Adresse IP de la batterie |
| `label` | Nom pour l'affichage et les messages. Seuls les 6 premiers caractères apparaissent dans le récapitulatif du matin/soir. |
| `minSoc`, `maxSoc`, `maxInputPower`, `maxOutput`, `dischargeAllowed`, `reverse` | Valeurs comme dans le Controller. Le tableau de bord les utilise comme valeurs de départ et limites des curseurs. |
| `inputLimit` | Puissance de charge depuis le réseau au démarrage, normalement `0`. N'existe pas dans le CONFIG du Controller – là, la valeur ne vient que du KVS. |
| `watch` | `true` : le watchdog surveille cet appareil. `false` : il n'apparaît que dans le tableau de bord. En l'absence de l'entrée, `true` s'applique. |

Si vous copiez le bloc d'appareils depuis le Controller, `dryRun` peut rester – l'entrée est ignorée ici.

### Partie tableau de bord (`api`)

```js
api: {
  enabled: true,
  kvsHost: "192.168.178.117",
  hysteresis: 12,
  dischargeStartupPower: 35,
  gridSource: "remote",
  gridSourceIp: "192.168.178.117",
  gridSourceEmId: 0,
  gridSourceUrl: "http://<IP-of-your-meter>/properties/report",
  gridSourceField: "total_power",
  gridSourceInvert: false,
  pollIntervalSec: 8
},
```

| Réglage | Signification |
|---|---|
| `enabled` | `true` : interface du tableau de bord activée. `false` : watchdog uniquement. |
| `kvsHost` | **IP du Shelly contrôleur** – c'est là que sont stockés les réglages du Controller. |
| `hysteresis` | Uniquement pour l'affichage dans le tableau de bord. Doit avoir **la même valeur** que dans le Controller. |
| `dischargeStartupPower` | Plus petite valeur autorisée pour la décharge fixe (sauf 0). Doit avoir **la même valeur** que dans le Controller. |
| `gridSource` | D'où vient la mesure réseau ? `"remote"` : un Shelly Pro 3EM sur le réseau (généralement le Shelly contrôleur), `"http_json"` : un autre compteur avec interface JSON, `"local"` : seulement si ce Shelly est lui-même un Pro 3EM. |
| `gridSourceIp`, `gridSourceEmId` | pour `"remote"` : IP du compteur et canal (généralement 0) |
| `gridSourceUrl`, `gridSourceField`, `gridSourceInvert` | pour `"http_json"` : adresse, nom du champ de la puissance totale, inverser le signe oui/non |
| `pollIntervalSec` | Intervalle d'interrogation lorsque le tableau de bord est ouvert, en secondes. Par défaut 8. |

Pour pouvoir aussi **modifier des réglages** dans le tableau de bord, `kvsEnabled: true` et `kvsForceReseed: false` doivent être définis dans le Controller. Sans KVS, le tableau de bord ne fait qu'afficher.

### Watchdog (`watchdog`)

```js
watchdog: {
  enabled: true,
  intervalSec: 120,
  vollSchwelle: 99,
  entladeReset: 90,
  minVoltWarn: 2.9,
  minVoltReset: 3.1,
  tempWarn: 45.0,
  tempReset: 30.0,
  offlineAlarmMin: 10,
  sunriseOffset: 0,
  sunsetOffset: 0
},
```

| Réglage | Signification |
|---|---|
| `enabled` | Watchdog activé ou désactivé |
| `intervalSec` | Fréquence de vérification du watchdog lorsque le tableau de bord n'est pas ouvert, en secondes (au moins 60) |
| `vollSchwelle` / `entladeReset` | Message « pleine » à partir de cet état de charge. Le message suivant ne vient qu'après que la batterie est passée entre-temps sous `entladeReset`. |
| `minVoltWarn` / `minVoltReset` | Avertissement lorsqu'une cellule descend sous cette tension (volts). Nouvel avertissement seulement après être repassée au-dessus de `minVoltReset` entre-temps. |
| `tempWarn` / `tempReset` | Avertissement lorsque la température de l'appareil dépasse `tempWarn` (°C). Nouvel avertissement seulement après être repassée sous `tempReset` entre-temps. |
| `offlineAlarmMin` | Message lorsqu'une batterie n'est plus joignable depuis ce nombre de **minutes** |
| `sunriseOffset` / `sunsetOffset` | Décalage du récapitulatif du matin et du soir par rapport au lever et au coucher du soleil, en minutes, p. ex. `30` = une demi-heure plus tard |

> Pour que les heures de lever et de coucher du soleil soient justes, la **localisation** doit être réglée dans le Shelly (Paramètres → Localisation ou fuseau horaire).

### Messages (`notify`)

```js
notify: {
  enabled: true,
  typ: "SIGNAL",
  phone: "+4917XXXXXXXX",
  apiKey: "DEIN_CALLMEBOT_KEY",
  webhookUrl: "http://192.168.178.50:8123/api/webhook/DEINE_ID",
  maxMessageLength: 900,
  apiEvents: true
},
```

| Réglage | Signification |
|---|---|
| `enabled` | Messages activés ou désactivés. Même désactivés, tous les messages apparaissent dans le journal du script. |
| `typ` | `"SIGNAL"`, `"WHATSAPP"` ou `"WEBHOOK"` |
| `phone`, `apiKey` | uniquement pour Signal et WhatsApp : votre numéro avec indicatif du pays et la clé CallMeBot |
| `webhookUrl` | uniquement pour le webhook : adresse complète |
| `maxMessageLength` | Les messages plus longs sont tronqués |
| `apiEvents` | `true` : envoyer aussi les messages concernant l'arrêt automatique lors de la charge manuelle |

Dans le Controller, ce bloc s'appelle `signal`, ici `notify`. `enabled`, `typ`, `phone`, `apiKey` et `webhookUrl` ont la même signification dans les deux ; `maxMessageLength` et `apiEvents` n'existent qu'ici. Si une ancienne configuration contient encore un bloc `signal`, le script l'utilise lorsqu'il n'y a pas de `notify`.

**Format du webhook :** le script envoie une requête POST avec le contenu `{"message": "…"}`. Dans Home Assistant, le texte est alors disponible dans une automatisation avec déclencheur webhook sous `{{ trigger.json.message }}`.

### Général

| Réglage | Signification |
|---|---|
| `httpTimeout` | Nombre maximal de secondes pendant lesquelles le script attend une réponse. Par défaut 5. |
| `debug` | `false` : sortie normale. `true` : journal détaillé pour le dépannage (voir [Dépannage](#dépannage)). |

---

## Tableau de bord

Le tableau de bord est une page web qui récupère ses données auprès de ce script. Vous l'ouvrez via un petit proxy sur un PC, un NAS (p. ex. Synology), Home Assistant ou un Raspberry Pi – pour Windows et Mac, il existe aussi sous forme de programme prêt à l'emploi.

👉 **[Installer et utiliser le tableau de bord](dashboard.md)** (allemand)

L'interface pour vos propres intégrations (p. ex. Home Assistant, Node-RED) est documentée dans la [description de l'API](API.md) (allemand).

### Historique dans ThingSpeak

Le proxy peut en plus envoyer chaque minute les mesures de vos batteries à ThingSpeak. Vous y obtenez un historique permanent avec des graphiques. L'envoi est facultatif et ne nécessite qu'un fichier supplémentaire à côté du proxy. Tant qu'un tableau de bord est ouvert, le proxy se contente de lire ses requêtes. Si l'envoi est désactivé, il n'adresse aucune requête au script.

👉 **[Configurer l'envoi vers ThingSpeak](thingspeak.md)** (allemand)

---

## Messages

Le script peut envoyer les messages suivants. Les textes des messages sont en allemand ; leur signification figure dans la colonne de droite.

| Message | Quand |
|---|---|
| ✅ zenDash/Watchdog v… gestartet (2/2 ueberwacht) | après chaque démarrage du script (démarré, 2 sur 2 surveillés) |
| 🔋 SF2400 voll (99%) | l'état de charge a atteint `vollSchwelle` (pleine) |
| 🔥 SF800 Temp hoch: 46.2C | température de l'appareil au-dessus de `tempWarn` (température élevée) |
| ⚠️ SF800 Zelle BO1234… nur 2.85V | une cellule sous `minVoltWarn`, avec le numéro de série du pack |
| ❌ SF800: nicht erreichbar seit 10 min | la batterie ne répond plus (injoignable depuis 10 min) |
| ❌ SF800: Report unlesbar seit 10 min | la batterie répond, mais avec des données incomplètes ou inutilisables (rapport illisible) |
| ✅ SF800: wieder erreichbar | après l'un des deux messages précédents (de nouveau joignable) |
| ⚠️ SF800 seit 20 Tagen nicht voll | vérifié une fois par jour lors du récapitulatif du matin (pas pleine depuis 20 jours), voir [Dernière charge complète](#dernière-charge-complète) |
| 🌅 Morgen-Update / 🌇 Abend-Update | au lever et au coucher du soleil : état de charge, température et tension de cellule la plus basse par appareil |
| ✅ SF2400: manuelles Laden beendet (voll) … | l'arrêt automatique a fonctionné (avec `apiEvents: true`) |
| ⚠️ SF2400: Auto-Stop fehlgeschlagen … | l'arrêt automatique n'a pas pu rétablir les réglages. Merci de vérifier dans le tableau de bord. |

Chaque avertissement n'arrive **qu'une fois**, pas à chaque interrogation. Il ne peut revenir qu'une fois la valeur revenue à la normale.

Dans le récapitulatif du matin et du soir, `n/a` apparaît lorsqu'aucune valeur actuelle n'est disponible pour un appareil, par exemple parce qu'il est momentanément injoignable.

> **Astuce :** le récapitulatif du matin et du soir est aussi un signe de vie. S'il n'arrive pas, le script ne tourne probablement plus.

---

## Charge manuelle et arrêt automatique

Dans le tableau de bord, vous pouvez faire charger une batterie manuellement depuis le réseau. Pour cela, le script désactive dans le Controller la décharge et la charge réseau de cet appareil et fixe une puissance de charge.

**Arrêt automatique :** dès que la batterie signale qu'elle est pleine, le script met fin lui-même à la charge manuelle et rétablit l'état précédent. Cela fonctionne aussi lorsque le tableau de bord est fermé.

Bon à savoir :
- Le script ne garde l'état précédent qu'en mémoire vive. Si le Shelly redémarre pendant la charge manuelle, la décharge et la charge réseau sont **réactivées** à la fin.
- Vous pouvez arrêter vous-même la charge manuelle à tout moment dans le tableau de bord.

---

## Dernière charge complète

Les batteries lithium devraient de temps en temps être chargées complètement, afin que la batterie estime correctement son état de charge. Le script mémorise donc, pour chaque batterie, quand elle a atteint pour la dernière fois **un vrai 100 %** :

- La date est enregistrée au plus une fois par jour dans le Shelly contrôleur (entrée KVS `zdmc_dev{numéro}_lastFull`) et survit donc à un redémarrage.
- Le **tableau de bord** affiche « 100 % : il y a N jours » pour chaque batterie – vert sous 7 jours, jaune jusqu'à 20 jours, rouge au-delà. Un appui affiche la date.
- Le **watchdog** signale une fois lorsqu'une batterie surveillée n'a pas été pleine depuis 20 jours.

---

## Passer des anciens scripts

Si vous utilisiez jusqu'ici les scripts séparés zenDash API 2.x et AkkuVolt Watchdog 1.x :

1. Effectuer le passage avec le Configurator – les étapes y sont décrites sous [Passer des anciens scripts séparés au nouveau script](../Multiconfigurator/readme_FR.md#passer-des-anciens-scripts-séparés-au-nouveau-script). Les anciennes configurations de ces scripts ne peuvent pas être importées directement ; la configuration du Controller en fournit toutefois l'essentiel.
2. **Arrêter les anciens scripts et désactiver « Run on startup »** (ou les supprimer) – sinon ils continuent de tourner et les messages arrivent en double.
3. Si vous utilisez le tableau de bord : si le nouveau script a un autre numéro de script, saisissez-le dans le proxy sous `/setup`.

---

## Besoin en mémoire

Un script Shelly dispose d'environ **25 Ko** de mémoire vive. Mesuré sur un appareil réel avec deux batteries (version 3.1) :

| | occupé au repos | valeur maximale |
|---|---|---|
| Tableau de bord fermé | env. 13,5 Ko | env. 17,8 Ko |
| Tableau de bord ouvert | env. 13,5 Ko | env. 17,7–18,0 Ko |

Depuis la version 3.4, la charge de base est encore inférieure d'environ 0,9 Ko. Il reste donc, au pire moment, un bon **7 Ko** de libre. À titre de comparaison : les deux anciens scripts ensemble atteignaient déjà presque 25 Ko en pointe.

Vous pouvez mesurer vous-même avec « 🔍 Speicher prüfen » (vérifier la mémoire) dans le [Configurator](../Multiconfigurator/readme_FR.md#vérifier-la-mémoire-dun-shelly).

---

## Dépannage

### Activer la sortie de débogage

Réglez `debug: true` et redémarrez le script – ou cochez « Debug-Ausgaben » (sorties de débogage) dans le Configurator lors de la mise à jour. Le journal affiche alors en plus :

- chaque appel de l'interface du tableau de bord avec les valeurs transmises
- chaque écriture dans les réglages du Controller avec le résultat
- le début et la fin de la charge manuelle
- le passage entre le rythme rapide (tableau de bord ouvert) et le repos
- l'envoi de chaque message
- l'occupation mémoire aux endroits les plus importants
- à chaque passage du watchdog, une ligne par batterie avec tous les packs, par exemple :
  ```
  [DEBUG] SF800: SoC 91%, 26.0C | Packs: CO1234…:91%/3.31V, BO5678…:91%/3.31V
  ```

Désactivez ensuite `debug`. Sinon le journal devient très long. Pour l'enregistrer, « Log aufzeichnen » (enregistrer le journal) dans le [Configurator](../Multiconfigurator/readme_FR.md#enregistrer-le-journal) est pratique.

### Problèmes fréquents

**Le journal affiche sous « Nachrichten » (messages) un autre type que celui que j'ai réglé.**
Le script n'applique les modifications qu'après un **redémarrage** (Stop → Start). Si vous utilisez `deploy.cmd` : le réglage doit se trouver dans **votre** fichier de configuration, pas dans le script lui-même. Vérifiez aussi que `notify:` n'apparaît qu'**une seule fois** dans le bloc CONFIG.

**Je ne reçois aucun message.**
Regardez la ligne « Nachrichten » du récapitulatif :
- `aus` (désactivé) signifie : `notify.enabled` est `false`, ou `typ` est inconnu. Dans le second cas, un WARNUNG (avertissement) apparaît juste au-dessus.
- Pour Signal/WhatsApp : le numéro de téléphone (avec `+33…`) et la clé API sont-ils corrects ?
- Pour le webhook : l'adresse est-elle joignable depuis le Shelly ?

Avec `debug: true`, vous voyez dans le journal si et comment chaque message a été envoyé.

**Je reçois chaque message en double.**
L'ancien watchdog tourne encore. Arrêtez-le et désactivez « Run on startup » pour lui.

**Le tableau de bord affiche une erreur de connexion.**
- Le script tourne-t-il ? (interface web → Scripts)
- L'IP **et** le numéro de script du Shelly tableau de bord sont-ils corrects dans le proxy sous `/setup` ? Voir [Dashboard – Wenn es nicht klappt](dashboard.md#wenn-es-nicht-klappt) (allemand, « si ça ne fonctionne pas »).
- `api.enabled` est-il à `true` ?

**Le tableau de bord n'affiche que des valeurs par défaut, les modifications ne sont pas prises en compte.**
Le script n'atteint pas les réglages du Controller. Vérifiez `api.kvsHost` (IP du Shelly contrôleur), que `kvsEnabled: true` est bien défini dans le Controller et qu'aucune protection par mot de passe n'est active sur le Shelly contrôleur. Avec `debug: true`, le journal affiche `KVS NICHT lesbar` (KVS illisible) ou `KVS.Set … -> FEHLER` (erreur).

**Message « Report unlesbar » (rapport illisible).**
La batterie a répondu, mais les données étaient incomplètes ou dans un format inattendu. Cela arrive ponctuellement et disparaît généralement tout seul. Si cela persiste, le format de données de la batterie a peut-être changé après une mise à jour du firmware. Merci alors d'ouvrir une [issue](https://github.com/surfer1264/Zendure-Stuff/issues) avec la réponse de `http://<IP-de-la-batterie>/properties/report`. Supprimez d'abord les numéros de série.

**Le récapitulatif du matin et du soir arrive à la mauvaise heure ou pas du tout.**
Vérifiez la localisation et le fuseau horaire dans les paramètres du Shelly. Le script crée deux planifications au démarrage. Les autres planifications du Shelly ne sont pas modifiées.
