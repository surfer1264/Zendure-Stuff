[:de: Deutsch](szscs.md) · [:gb: English](szscs_EN.md) · :fr: **Français**

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

## Trois fonctions sur deux Shelly – sans cloud

Le **Shelly Controller** assure la régulation, le **Shelly Dashboard** l'API zenDash et le watchdog – chaque fonction pouvant y être désactivée séparément. Quel script va où : [Structure du système](readme_FR.md#structure-du-système).

### 1. Le Controller – la régulation

* régule sur une **consigne** (par ex. 0 W de soutirage réseau)
* avec **hystérésis** et **amortissement**, pour éviter les oscillations
* **charge & décharge**, réparties sur tous les SolarFlow
* réglages modifiables en fonctionnement (KVS) – depuis le tableau de bord ou par ex. depuis Home Assistant

📖 [Premiers pas](Controller/readme_FR.md) · [Au quotidien](Controller/benutzerdoku.md) (en allemand) · [Tous les détails](Controller/gesamtdoku.md) (en allemand)

### 2. Le tableau de bord – la vue d'ensemble

* **affichage en direct** de la puissance réseau, du niveau de charge et de la puissance de chaque SolarFlow
* **intervenir :** consigne, réserve (minSoc), autoriser décharge/charge, puissance de décharge fixe
* **charge manuelle avec arrêt automatique** – dès que la batterie est pleine, le SolarFlow repasse de lui-même en régulation (même quand le tableau de bord est fermé)
* **« 100 % : il y a N jours »** – indique quand chaque batterie a été pleine pour la dernière fois
* en allemand, anglais et français, sur PC, tablette ou téléphone

Le tableau de bord est une page web qui passe par un petit **proxy** – sous forme de programme prêt à l'emploi pour Windows et Mac (voir [Téléchargements](#téléchargements)), de script Python, sur un Synology ou comme application dans Home Assistant.

📖 [Installer et utiliser le tableau de bord](zendash_watch_API_ZenSDK/dashboard_FR.md)

### 3. Le watchdog – les notifications

* **résumé du matin et du soir** avec niveau de charge, température et tension des cellules
* notification quand une **batterie est pleine**
* **alerte** quand une tension de cellule est trop basse ou la température trop élevée
* notification quand un SolarFlow est **injoignable** – et fin d'alerte dès qu'il est de retour
* avertissement quand une batterie **n'a pas été pleine depuis 20 jours**
* envoi par **Signal**, **WhatsApp** ou **webhook** ; réglable pour chaque SolarFlow s'il doit être surveillé

📖 [API zenDash + watchdog](zendash_watch_API_ZenSDK/readme_FR.md)

---

## Mise en place

Comment les éléments interagissent : [Comment les éléments fonctionnent ensemble](architektur_FR.md).

### Avec un Shelly Pro 3EM

Le Pro 3EM sert en même temps de Shelly Controller. On y ajoute un second Shelly comme Shelly Dashboard.

<img width="350" alt="IMG_1246" src="https://github.com/user-attachments/assets/c8821089-7e87-437f-ad29-6715f1554cfb" />

### Avec un autre compteur intelligent

Le Controller tourne sur n'importe quel Shelly et lit le compteur intelligent via le réseau. On y ajoute le Shelly Dashboard – là aussi, deux Shelly donc.

<img width="600" alt="IMG_1247" src="https://github.com/user-attachments/assets/4758a842-f361-47d7-8260-c23fc1ae1bde" />

---

## 👉 Pour commencer

Télécharger l'assistant, répondre aux questions, charger – en 10 minutes ta régulation tourne. Les trois étapes sont sur la **[page d'accueil](readme_FR.md#-commencer-ici)**, les instructions détaillées dans le **[configurateur](Multiconfigurator/readme_FR.md)**.

---

## Ce qu'il te faut

Deux Shelly (idéalement l'un d'eux est un **Shelly Pro 3EM**, qui mesure aussi la puissance réseau), un compteur intelligent et des SolarFlow compatibles zenSDK dans le même réseau. Les appareils qui conviennent et ce qu'il faut d'autre : **[Appareils compatibles](kompatible_geraete_FR.md)**.

**Important :** retire tes SolarFlow du **HEMS** dans l'application Zendure, sinon le cloud envoie en parallèle ses propres commandes.

---

## Téléchargements

Tous les programmes se trouvent sur la **[page des versions](https://github.com/surfer1264/Zendure-Stuff/releases/latest)**. Ce qu'il te faut pour quoi, et comment autoriser les fichiers au premier lancement :

- **Assistant local avec configurateur** – configure tout, charge les scripts sur les Shelly, fait les mises à jour : [Configurateur → téléchargement](Multiconfigurator/readme_FR.md#recommandé--lassistant-local-installateur-exe)
- **Proxy du tableau de bord** – ouvre le tableau de bord dans le navigateur, sans installer Python : [Tableau de bord → en tant que programme](zendash_watch_API_ZenSDK/dashboard_FR.md#en-tant-que-programme-sous-windows-ou-macos)
- **Sans l'assistant :** le [configurateur web](Multiconfigurator/readme_FR.md#alternative--le-configurateur-web-seul) dans le navigateur – tu charges alors le script toi-même.

---

## Mise à jour

Lance l'assistant local, choisis **« Mettre à jour »** – tes réglages sont conservés. Détails, y compris le passage des anciens scripts séparés : [Configurateur → mise à jour](Multiconfigurator/readme_FR.md#4-mise-à-jour). Si tu utilises le tableau de bord, la page du tableau de bord et le script doivent avoir le même numéro de version ([tableau de bord](zendash_watch_API_ZenSDK/dashboard_FR.md)).

---

**Attention :** le configurateur ne remplace pas la lecture de la documentation – surtout pour les paramètres de régulation.

## Conclusion

* Tout en local
* aucun cloud
* plus d'excuses : « Mon système ne marche pas, le cloud est encore en panne »
* pour tous les hubs avec zenSDK
