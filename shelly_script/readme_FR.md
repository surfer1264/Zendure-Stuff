<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

🌐 [Deutsch](readme.md) · [English](readme_EN.md) · **Français**

# Piloter les batteries Zendure en local – avec deux Shelly

Vos batteries Zendure (appareils compatibles zenSDK à partir du SolarFlow 800) sont pilotées sans cloud : un Shelly maintient votre consommation réseau à zéro, un second fournit les données pour un tableau de bord et vous alerte en cas de problème.

## 👉 Commencer ici

1. **[Télécharger l'assistant](https://github.com/surfer1264/Zendure-Stuff/releases/latest)** (Windows ou Mac avec Apple Silicon) et le lancer.
2. Le Configurator s'ouvre dans votre navigateur. Choisissez **« Nouvelle configuration ou mise à jour manuelle »** et répondez aux questions.
3. Pour finir, cliquez sur **« ⚡ Charger directement »** – c'est terminé.

Les instructions détaillées (y compris mise à jour, remplacement d'un Shelly et messages d'erreur) se trouvent avec le **[Configurator](Multiconfigurator/readme_FR.md)** · [Deutsch](Multiconfigurator/readme.md) · [English](Multiconfigurator/readme_EN.md)

## Structure du système

| Shelly | Script | Rôle |
|---|---|---|
| **Shelly contrôleur** | [Controller](Controller/readme.md) (allemand) | pilote la charge et la décharge de vos batteries |
| **Shelly tableau de bord** | [zenDash API + Watchdog](zendash_watch_API_ZenSDK/readme_FR.md) | fournit les données du tableau de bord et signale batterie pleine, surchauffe, sous-tension ou pannes |

S'y ajoute le **[Configurator](Multiconfigurator/readme_FR.md)** avec l'assistant local sur votre ordinateur : il gère la configuration initiale, les mises à jour et l'enregistrement des journaux pour les deux Shelly.

**Un seul script** tourne sur chaque Shelly. Les Shelly disposent de peu de mémoire pour les scripts – deux scripts sur un même appareil peuvent se faire planter mutuellement.

Le **[tableau de bord](zendash_watch_API_ZenSDK/dashboard.md)** (allemand) est lui-même une page web que vous ouvrez via un petit proxy sur un PC, un NAS ou Home Assistant.

## Autres outils

| Dossier | Utilité |
|---|---|
| [Script_poller](Script_poller/readme.md) (allemand) | mesure à long terme de la mémoire et du CPU d'un script Shelly, enregistrement des logs sur plusieurs heures (pour le dépannage et le développement) |
| [testController](testController/README.md) (allemand) | environnement de test pour le Controller (pour les développeurs) |
| [thingsboard](thingsboard) | tableaux de bord et chaînes de règles prêts à importer dans ThingsBoard, pour l'[envoi vers ThingsBoard](zendash_watch_API_ZenSDK/thingsboard.md) (allemand) |
| [Einordnung](Einordnung.md) (allemand) | comparaison avec d'autres solutions multi-appareils (ioBroker, Z-HA, EMS SolarFlow …) |

## Obsolète – merci de ne plus utiliser

Ces dossiers sont conservés uniquement pour consultation et ne sont plus développés :

| Dossier | Remplacé par |
|---|---|
| AkkuWatchDogMulti, WatchdogZenSDK | [zenDash API + Watchdog](zendash_watch_API_ZenSDK/readme_FR.md) |
| zendash | [zenDash API + Watchdog](zendash_watch_API_ZenSDK/readme_FR.md) |
| Upload_Controller | [Configurator avec assistant](Multiconfigurator/readme_FR.md) (téléversement direct et mise à jour) |
| [Datenmonitor](Datenmonitor/readme.md) | – (moniteur de données basique via MQTT et zenSDK, sans support) |

## Termes

| Terme | Signification |
|---|---|
| **Batterie** | votre appareil Zendure (SolarFlow 800, SolarFlow 2400 Pro …) |
| **Controller** | le script de régulation `zerooutput_multi_kvs` |
| **Assistant** | petit programme pour votre ordinateur qui lance le Configurator et téléverse les scripts sur les Shelly |
| **KVS** | stockage clé-valeur dans le Shelly pour les réglages modifiables en cours de fonctionnement (p. ex. depuis le tableau de bord) |

Plus d'informations dans le [Wiki](https://github.com/surfer1264/Zendure-Stuff/wiki/Simple-Zendure-Shelly-Cloudless-System_FR).

