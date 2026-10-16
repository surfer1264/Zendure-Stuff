🌐 [Deutsch](szscs.md) · [English](szscs_EN.md) · **Français**

# Simple Zendure Shelly Cloudless System

**Offre-moi un café !**

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

<img width="1000" alt="image" src="https://github.com/user-attachments/assets/0267db3d-7941-472e-87de-e134ada66dea" />

* Tu as **un** ou **plusieurs** SolarFlow (SF800 ou plus récent, compatible zenSDK) ?
* Tu as un Shelly Pro 3EM ou un autre compteur intelligent avec une interface locale ?
* Tu veux une régulation locale – sans cloud ?
* Tu veux peu d'effort et quelque chose qui fonctionne tout simplement ?
* Home Assistant & co. ne sont pas (encore) une option pour toi ?

_Principe_ : **Installer** – **Lancer** – **Oublier**

🎉 TU Y ES 🎉

---

## 👉 Pour commencer

1. **Télécharge l'assistant local** (voir [Téléchargements](#téléchargements)) et lance-le. Le configurateur s'ouvre dans le navigateur.
2. Choisis **« Nouvelle configuration »** et réponds aux questions sur tes batteries, ton compteur intelligent et les notifications.
3. À la fin, **« ⚡ Charger directement »** – les scripts arrivent entièrement configurés sur tes deux Shelly.

Instructions détaillées : **[Configurateur](Multiconfigurator/readme_FR.md)**

---

## Ce qu'il te faut

* **Deux Shelly** (Gen2 ou plus récent). Idéalement, l'un d'eux est un **Shelly Pro 3EM** – il mesure alors aussi la puissance réseau. Sinon, un autre compteur intelligent avec interface JSON, par ex. Zendure Smart Meter 3CT, une tête de lecture Tasmota ou un Shelly 3EM (sans Pro).
* Les **adresses IP** de tes SolarFlow et de tes Shelly – idéalement fixées dans ton routeur.
* Un **PC Windows ou un Mac** pour l'assistant local. Sans l'assistant local, n'importe quel navigateur suffit.
* **Facultatif pour les notifications :** une clé API gratuite de [CallMeBot](https://www.callmebot.com) pour Signal ou WhatsApp – ou un webhook, par ex. dans Home Assistant.

**Important :** retire tes SolarFlow du **HEMS** dans l'application Zendure, sinon le cloud envoie en parallèle ses propres commandes.

---

## Trois fonctions sur deux Shelly – sans cloud

| Shelly | Script | Rôle |
|---|---|---|
| **Shelly Controller** | Controller (`zerooutput_multi_kvs`) | régule la charge et la décharge de tes SolarFlow |
| **Shelly Dashboard** | API zenDash + watchdog (`zendash_watch`) | fournit les données du tableau de bord et envoie les notifications – chaque fonction désactivable séparément |

Sur chaque Shelly tourne **exactement un script**. Les Shelly ont peu de mémoire de script – c'est pourquoi le Controller et le script du tableau de bord tournent toujours sur deux appareils séparés.

### 1. Le Controller – la régulation

* régule sur une **consigne** (par ex. 0 W de soutirage réseau)
* avec **hystérésis** et **amortissement**, pour éviter les oscillations
* **charge & décharge**, réparties sur tous les SolarFlow
* réglages modifiables en fonctionnement (KVS) – depuis le tableau de bord ou par ex. depuis Home Assistant

📖 [Premiers pas](Controller/readme.md) · [Documentation utilisateur](Controller/benutzerdoku.md) · [Tous les détails](Controller/gesamtdoku.md) (en allemand)

### 2. Le tableau de bord – la vue d'ensemble

* **affichage en direct** de la puissance réseau, du niveau de charge et de la puissance de chaque SolarFlow
* **intervenir :** consigne, réserve (minSoc), autoriser décharge/charge, puissance de décharge fixe
* **charge manuelle avec arrêt automatique** – dès que la batterie est pleine, le SolarFlow repasse de lui-même en régulation (même quand le tableau de bord est fermé)
* **« 100 % : il y a N jours »** – indique quand chaque batterie a été pleine pour la dernière fois
* en allemand, anglais et français, sur PC, tablette ou téléphone

Le tableau de bord est une page web qui passe par un petit **proxy** – sous forme de programme prêt à l'emploi pour Windows et Mac (voir [Téléchargements](#téléchargements)), de script Python, sur un Synology ou comme application dans Home Assistant.

📖 [Installer et utiliser le tableau de bord](zendash_watch_API_ZenSDK/dashboard_FR.md) (en allemand)

### 3. Le watchdog – les notifications

* **résumé du matin et du soir** avec niveau de charge, température et tension des cellules
* notification quand une **batterie est pleine**
* **alerte** quand une tension de cellule est trop basse ou la température trop élevée
* notification quand un SolarFlow est **injoignable** – et fin d'alerte dès qu'il est de retour
* avertissement quand une batterie **n'a pas été pleine depuis 20 jours**
* envoi par **Signal**, **WhatsApp** ou **webhook** ; réglable pour chaque SolarFlow s'il doit être surveillé

📖 [API zenDash + watchdog](zendash_watch_API_ZenSDK/readme_FR.md) (en allemand)

---

## Mise en place

### Avec un Shelly Pro 3EM

Le Pro 3EM sert en même temps de Shelly Controller. On y ajoute un second Shelly comme Shelly Dashboard.

<img width="350" alt="IMG_1246" src="https://github.com/user-attachments/assets/c8821089-7e87-437f-ad29-6715f1554cfb" />

### Avec un autre compteur intelligent

Le Controller tourne sur n'importe quel Shelly et lit le compteur intelligent via le réseau. On y ajoute le Shelly Dashboard – là aussi, deux Shelly donc.

<img width="600" alt="IMG_1247" src="https://github.com/user-attachments/assets/4758a842-f361-47d7-8260-c23fc1ae1bde" />

---

## Téléchargements

**Assistant local avec configurateur** – configure tout, charge les scripts sur les Shelly, fait les mises à jour, vérifie la mémoire et enregistre un journal en cas de problème. Aucune installation nécessaire : télécharger, lancer, c'est tout.

| Assistant local | pour |
|---|---|
| **[⬇️ zendure_local_helper-windows.exe](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows.exe)** | Windows 64 bits |
| **[⬇️ zendure_local_helper-windows-x86.exe](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows-x86.exe)** | Windows 32 bits |
| **[⬇️ zendure_local_helper-macos](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-macos)** | Mac avec Apple Silicon (M1 ou plus récent) |

**Proxy du tableau de bord** – ouvre le tableau de bord dans le navigateur, sans installer Python.

| Proxy du tableau de bord | pour |
|---|---|
| **[⬇️ zendure_proxy-windows.exe](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-windows.exe)** | Windows 64 bits |
| **[⬇️ zendure_proxy-macos](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-macos)** | Mac avec Apple Silicon (M1 ou plus récent) |

Au premier lancement, ton système d'exploitation affiche un avertissement, car les fichiers ne sont pas signés – comment les lancer quand même est expliqué dans la [documentation du configurateur](Multiconfigurator/readme_FR.md#recommandé--lassistant-local-installateur-exe). Tous les fichiers et sommes de contrôle : [Releases](https://github.com/surfer1264/Zendure-Stuff/releases/latest).

**Sans l'assistant local :** le [configurateur web](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Multiconfigurator/zendure-multi-configurator_multilang.html) fonctionne directement dans le navigateur. Tu peux tout configurer et enregistrer le script terminé – mais tu dois ensuite le charger toi-même via l'interface web du Shelly. La mise à jour, la vérification de la mémoire et l'enregistrement du journal ne sont disponibles qu'avec l'assistant local.

---

## Mise à jour

Quand une nouvelle version est disponible, lance l'assistant local et choisis **« Mettre à jour »**. Il compare les versions de tes Shelly avec GitHub, lit tes réglages directement sur le Shelly et installe la nouvelle version – tes réglages sont conservés.

Si tu utilises le tableau de bord, récupère aussi le nouveau proxy ou la nouvelle page du tableau de bord après une mise à jour : les deux doivent avoir le même numéro de version que le script.

**Passer des anciens scripts séparés au nouveau script :** auparavant, l'API zenDash et le watchdog étaient deux scripts séparés. La marche à suivre se trouve dans la [documentation du configurateur](Multiconfigurator/readme_FR.md#passer-des-anciens-scripts-séparés-au-nouveau-script).

---

**Attention :** le configurateur ne remplace pas la lecture de la documentation – surtout pour les paramètres de régulation.

## Conclusion

* Tout en local
* aucun cloud
* plus d'excuses : « Mon système ne marche pas, le cloud est encore en panne »
* pour tous les hubs avec zenSDK
