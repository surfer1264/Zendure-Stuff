[:de: Deutsch](architektur.md) · [:gb: English](architektur_EN.md) · :fr: **Français**

# Comment les éléments fonctionnent ensemble

La suite distingue cinq domaines – chacun a sa propre couleur dans le schéma :

| Couleur | Domaine | Ce qui en fait partie |
|---|---|---|
| Ambre | **Matériel piloté** | vos batteries Zendure |
| Bleu | **Matériel de fonctionnement** | Shelly 1, Shelly 2, compteur |
| Turquoise | **Logiciel de fonctionnement** | script Controller, script zendash_watch |
| Violet | **Logiciel de pilotage** | tableau de bord, proxy, Home Assistant, statistiques, notifications |
| Gris | **Logiciel d'installation** | Configurator avec assistant local |

La régulation n'a besoin que de l'ambre, du bleu et du turquoise. Tout ce qui est violet relève du confort et peut tomber en panne. Le gris ne sert qu'à l'installation et aux mises à jour. Tout tourne dans votre réseau local – aucun cloud n'est nécessaire.

![Architecture de la Shelly Suite](img/architektur_FR.svg)

## Matériel piloté : les batteries

Vos batteries Zendure disposent d'une interface locale intégrée, le **zenSDK**. Les scripts s'adressent directement à elle via son adresse IP :

- `/properties/report` renvoie l'état de charge, les puissances, la tension des cellules, la température et des limites comme `minSoc`.
- `/properties/write` reçoit les consignes, par ex. charger ou décharger et avec combien de watts. Le Controller utilise `smartMode: 1` afin que les consignes fréquentes ne soient pas écrites dans la mémoire flash de l'appareil.

Les batteries n'ont pas besoin d'Internet pour fonctionner. Vous pouvez leur bloquer l'accès dans votre routeur.

## Matériel de fonctionnement : Shelly et compteur

**Compteur** – Le Controller doit savoir combien d'énergie est prélevée sur le réseau ou injectée. Le plus simple est un **Shelly Pro 3EM** – compteur et Shelly 1 sont alors le même appareil. Sinon, un autre compteur intelligent est lu via le réseau (`http_json`), voir [Controller](Controller/readme_FR.md).

**Shelly 1 (Shelly contrôleur)** – héberge le script Controller et ses réglages (KVS).

**Shelly 2 (Shelly tableau de bord)** – héberge le script zendash_watch.

**Un seul script** tourne sur chaque Shelly. Les Shelly disposent de peu de mémoire pour les scripts ; deux scripts sur un même appareil peuvent se faire planter mutuellement. C'est pourquoi il y a toujours deux Shelly.

Conseil : attribuez des adresses IP fixes aux batteries et aux Shelly dans votre routeur.

### Deux variantes

**Avec un Shelly Pro 3EM** – Le Pro 3EM est à la fois compteur et Shelly 1. On y ajoute le Shelly 2.

<img width="350" alt="IMG_1246" src="https://github.com/user-attachments/assets/c8821089-7e87-437f-ad29-6715f1554cfb" />

**Avec un autre compteur intelligent** – Le Shelly 1 est un Shelly quelconque qui lit le compteur via le réseau. On y ajoute le Shelly 2 – là aussi, deux Shelly donc.

<img width="600" alt="IMG_1247" src="https://github.com/user-attachments/assets/4758a842-f361-47d7-8260-c23fc1ae1bde" />

## Logiciel de fonctionnement : deux scripts

Le **script Controller** (sur le Shelly 1) régule. Toutes les quelques secondes, il lit la puissance réseau sur le compteur et répartit charge et décharge entre vos batteries, de sorte que le moins possible soit injecté ou prélevé. Il fonctionne de manière totalement autonome.

**KVS** – Les réglages que vous modifiez en fonctionnement (consigne, réserve, décharge autorisée …) sont stockés dans le KVS du Shelly 1. Le script Controller les lit à chaque cycle de régulation – les modifications prennent donc effet en quelques secondes, sans redémarrage. Le KVS est le seul point par lequel le pilotage agit sur la régulation.

Le **script zendash_watch** (sur le Shelly 2) affiche et surveille. Il lit les reports des batteries, fournit les données du tableau de bord et écrit les modifications faites dans le tableau de bord dans le KVS du Controller (`KVS.Set`). En tant que watchdog, il surveille vos batteries et signale batterie pleine, surchauffe, sous-tension ou panne. Si la tension des cellules passe sous le seuil, il bloque en plus la décharge.

## Logiciel de pilotage

**Proxy du tableau de bord** – un petit programme sur PC, Raspberry Pi, NAS ou en tant qu'application Home Assistant. Il fournit le [tableau de bord](zendash_watch_API_ZenSDK/dashboard_FR.md) et transmet ses requêtes au script zendash_watch. Le navigateur ne communique donc jamais directement avec les Shelly.

**Tableau de bord (SMDC)** – la page web dans le navigateur ou en application sur l'écran d'accueil du téléphone : valeurs en direct, consigne, réserve, charge manuelle.

**Notifications** – Le script zendash_watch envoie les alertes par Signal, WhatsApp ou webhook.

**Statistiques cloud (option)** – Sur demande, le proxy envoie chaque minute les mesures à [ThingSpeak](zendash_watch_API_ZenSDK/thingspeak.md) et/ou [ThingsBoard](zendash_watch_API_ZenSDK/thingsboard.md) (allemand) – y compris auto-hébergé dans votre réseau local. Seules des mesures sont transmises, aucun nom, adresse ou numéro de série. Si aucun envoi n'est activé, le proxy n'interroge rien. Pour un historique sans trous, il doit tourner en permanence (NAS ou Home Assistant).

**Home Assistant (option)** – lit et écrit directement le KVS du Controller via REST (`KVS.GetMany`, `KVS.Set`). Vous pouvez ainsi piloter consigne, réserve, etc. depuis des automatisations.

## Logiciel d'installation

Le **[Configurator](Multiconfigurator/readme_FR.md)** avec l'assistant local tourne sur votre ordinateur. Il vérifie la mémoire libre des Shelly, crée les réglages, télécharge les scripts depuis GitHub et les installe sur les deux Shelly. Pour les mises à jour, il compare les versions présentes sur les Shelly avec les versions actuelles sur GitHub. Il n'est pas nécessaire au quotidien.

## Que se passe-t-il en cas de panne ?

| En panne … | Domaine | Conséquence |
|---|---|---|
| Proxy ou PC | pilotage | Pas de tableau de bord, pas de statistiques. **La régulation continue.** |
| Internet | – | Pas de statistiques, pas de notifications Signal/WhatsApp. Régulation et tableau de bord continuent. |
| Shelly 2 (zendash_watch) | fonctionnement | Pas de tableau de bord, pas de notifications. **La régulation continue.** |
| Une batterie | piloté | Le Controller continue avec les autres, le watchdog signale la panne. |
| Shelly 1 (Controller) | fonctionnement | Plus de régulation. Le tableau de bord ne peut plus modifier les réglages. |

## Pour aller plus loin

- [Ce que fait la suite](szscs_FR.md)
- [Controller](Controller/readme_FR.md)
- [zenDash API + Watchdog](zendash_watch_API_ZenSDK/readme_FR.md) · [Référence API](zendash_watch_API_ZenSDK/API.md) (allemand)
- [Appareils compatibles](kompatible_geraete_FR.md) · [Besoins en mémoire](zendash_speichermodell.md) (allemand)
