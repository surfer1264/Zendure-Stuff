[:de: Deutsch](kompatible_geraete.md) · [:gb: English](kompatible_geraete_EN.md) · :fr: **Français**

# Appareils compatibles

Ce qu’il te faut pour la suite : deux Shelly, un compteur intelligent et des batteries Zendure compatibles zenSDK.

## Shelly

Il te faut **deux Shelly** Gen2 ou plus récents (Plus, Pro, Gen3, Gen4) avec fonction script – un pour le [Controller](Controller/readme.md), un pour [l’API zenDash + Watchdog](zendash_watch_API_ZenSDK/readme_FR.md). Les deux scripts ensemble ne tiennent pas dans la mémoire d’un seul Shelly.

Ce qui compte, c’est la **mémoire script** : à partir de **25 000 octets**, tout va bien.

| Appareil | Résultat |
|---|---|
| Shelly Pro 3EM | ✅ testé |
| Shelly 3EM-63W Gen3 | ✅ testé |
| Shelly 3EM 3ct63 | ✅ testé |
| Shelly 1PM Gen4 | ✅ testé |
| Shelly Plus 1PM (PM1Plus) | ✅ testé |
| Shelly Plus Plug S | ✅ testé |
| Shelly Plug S Gen3 | ❌ mémoire insuffisante |
| Shelly 1PM Gen3 | ❌ mémoire insuffisante |
| Shelly Mini Gen3 | ❌ mémoire insuffisante |

Ton appareil n’est pas dans la liste ? Vérifie toi-même la mémoire :

- **Avec le configurateur** (assistant lancé) : à l’étape résultat, **« 🔍 Vérifier la mémoire »** – voir le [guide du configurateur](Multiconfigurator/readme_FR.md).
- **Dans le navigateur :** ouvre `http://<IP-du-Shelly>/rpc/Script.GetStatus?id=<ID-du-script>`. La réponse contient `mem_free` – sur un Shelly sans script en cours, la valeur devrait être d’au moins 25 000.

Le nombre de batteries qu’un Shelly peut piloter est expliqué dans [l’analyse des besoins en mémoire](zendash_speichermodell.md) (en allemand).

!!! warning "Pas de mot de passe sur le Shelly du Controller"
    L’API zenDash lit et écrit les réglages du Controller. Avec une protection par mot de passe sur le Shelly du Controller, cela ne fonctionne pas.

## Compteur intelligent

Le Controller a besoin de la puissance réseau actuelle :

- **Shelly Pro 3EM** – le meilleur choix : si le Controller tourne directement dessus, il lit les valeurs sans requête réseau.
- **Un autre Shelly Pro 3EM** du réseau.
- **Compteurs avec interface JSON** (`http_json`), par ex. Zendure Smart Meter 3CT et D0, everHome EcoTracker, tête de lecture Tasmota, Shelly 3EM sans Pro. Le [configurateur](Multiconfigurator/readme_FR.md) propose des modèles prêts à l’emploi pour ces appareils.

## Batteries Zendure

- Uniquement des **appareils compatibles zenSDK** (à partir du SolarFlow 800), dans le même réseau et de préférence avec une **adresse IP fixe** (à régler dans ton routeur).
- Retire les batteries du **HEMS** dans l’app Zendure – sinon le cloud envoie en parallèle ses propres commandes. Exception Zendure Smart Meter D0 : son interface locale s’active une fois via HEMS. Cela ne concerne que le compteur, les batteries restent hors du HEMS.
- **Il ne peut en rester qu’un :** aucun second régulateur ne doit piloter les mêmes batteries – pas de HEMS, pas de Z-HA, pas d’autre automatisme.

## Réseau

Le Shelly du Controller doit joindre toutes les batteries et le compteur dans le réseau local (même LAN/Wi-Fi, pas de pare-feu entre les deux). Attribue de préférence des **adresses IP fixes** aux batteries et aux Shelly dans ton routeur. Le Shelly n’a besoin d’Internet que pour les notifications optionnelles.

## Également nécessaire

- Un **PC Windows ou un Mac** (Apple Silicon) pour [l’assistant local avec le configurateur](Multiconfigurator/readme_FR.md). Sans l’assistant, n’importe quel navigateur suffit – tu charges alors le script toi-même.
- **Facultatif pour les notifications :** une clé API gratuite de [CallMeBot](https://www.callmebot.com/blog/free-api-signal-send-messages/) pour Signal ou WhatsApp – ou un webhook, par ex. dans Home Assistant.
