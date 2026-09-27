[:de: Deutsch](readme.md) · [:gb: English](readme_EN.md) · [:fr: Français](readme_FR.md)

# Le configurateur

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

Quelques clics pour piloter localement ta flotte Zendure – configurer, mettre à jour, terminé.

> 🤖 Cette version française a été traduite de l'[original allemand](readme.md) par Claude (l'IA d'Anthropic). En cas de doute ou de contradiction, la version allemande fait foi. Les captures d'écran montrent l'interface en allemand.

**Sommaire**

1. [Ce que le configurateur met en place](#1-ce-que-le-configurateur-met-en-place)
2. [Où trouver le configurateur](#2-où-trouver-le-configurateur)
   * [Recommandé : l'assistant local (installateur EXE)](#recommandé--lassistant-local-installateur-exe)
   * [Alternative : le configurateur web seul](#alternative--le-configurateur-web-seul)
3. [Première configuration](#3-première-configuration)
   * [Déroulement](#déroulement)
   * [Les fonctions de l'étape Résultat](#les-fonctions-de-létape-résultat)
4. [Mise à jour](#4-mise-à-jour)
   * [Comment faire](#comment-faire)
   * [Ce que deviennent tes réglages lors d'une mise à jour](#ce-que-deviennent-tes-réglages-lors-dune-mise-à-jour)
   * [Mise à jour sans l'assistant local](#mise-à-jour-sans-lassistant-local)
   * [Passer des anciens scripts séparés au nouveau script](#passer-des-anciens-scripts-séparés-au-nouveau-script)
5. [Remplacer un Shelly](#5-remplacer-un-shelly)
6. [Messages d'erreur et situations problématiques](#6-messages-derreur-et-situations-problématiques)
   * [Plusieurs scripts sur un Shelly](#plusieurs-scripts-sur-un-shelly)
   * [Aperçu des messages](#aperçu-des-messages)
   * [Problèmes avec l'assistant local](#problèmes-avec-lassistant-local)
7. [Guides pratiques](#7-guides-pratiques)
   * [Importer une configuration existante](#importer-une-configuration-existante)
   * [Charger un script manuellement](#charger-un-script-manuellement)
   * [Vérifier la mémoire d'un Shelly](#vérifier-la-mémoire-dun-shelly)
   * [Sauvegarder la configuration](#sauvegarder-la-configuration)
   * [Enregistrer le journal](#enregistrer-le-journal)
   * [Réinitialiser les IP mémorisées](#réinitialiser-les-ip-mémorisées)
   * [Vérifier l'intégrité du téléchargement](#vérifier-lintégrité-du-téléchargement)

Les dernières modifications figurent dans le [changelog](CHANGELOG.md) (en allemand).

---

## 1. Ce que le configurateur met en place

Le configurateur est un assistant qui te guide pas à pas dans la mise en place de ta régulation Zendure. Tu réponds à quelques questions sur tes appareils – à la fin, les scripts adaptés tournent, entièrement configurés, sur tes Shelly.

Ton système se compose toujours de **deux Shelly** :

| Shelly | Script | Rôle |
|---|---|---|
| **Shelly Controller** | Controller (`zerooutput_multi_kvs`) | le moteur de régulation – pilote la charge et la décharge de tes batteries et conserve les réglages modifiables en direct (KVS) |
| **Shelly Dashboard** | zenDash-API + Watchdog (`zendash_watch`) | un script commun avec deux fonctions désactivables séparément |

Trois fonctions y tournent :

* **Controller** – régule ton import/export réseau via tes batteries Zendure
* **zenDash-API** – fournit les données du tableau de bord avec une vue d'ensemble en direct ; il permet aussi de modifier le comportement du Controller
* **Watchdog** – signale les situations exceptionnelles (batterie pleine, température, tension des cellules, appareil injoignable) et envoie un récapitulatif matin et soir

Les fonctions se combinent librement – zenDash-API et Watchdog peuvent par exemple être ajoutés plus tard, quand le Controller tourne déjà. Les informations nécessaires à plusieurs fonctions (liste des appareils, source réseau, notifications) ne sont demandées **qu'une seule fois** et reportées correctement dans les deux scripts.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/487e63fb-734d-4bb1-b795-19f81921acb6" />

Le configurateur est disponible en **allemand, anglais et français**.

---

## 2. Où trouver le configurateur

Il existe deux possibilités. L'**assistant local** (fichier EXE) est recommandé, car le chargement direct, la mise à jour, la vérification de la mémoire et l'enregistrement du journal ne fonctionnent qu'avec lui.

### Recommandé : l'assistant local (installateur EXE)

Un petit programme pour ton ordinateur. Il ouvre automatiquement le configurateur dans le navigateur et se charge de la connexion à tes Shelly. Pas d'installation, pas besoin de Python – télécharger, lancer, terminé.

👉 **[Version actuelle (latest release)](https://github.com/surfer1264/Zendure-Stuff/releases/latest)**

Téléchargements directs :

* [Windows (64 bits)](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows.exe)
* [Windows (32 bits)](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows-x86.exe)
* [macOS](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-macos)

Au premier lancement, ton système d'exploitation affiche un avertissement, car le fichier n'est pas signé :

* **Windows :** à « Windows a protégé votre ordinateur » (SmartScreen), clique sur « Informations complémentaires » → « Exécuter quand même ».
* **macOS :** clic droit sur le fichier → « Ouvrir » → confirme à nouveau « Ouvrir » dans la boîte de dialogue.

Si tu veux t'assurer que le fichier n'a pas été modifié, tu peux le [vérifier](#vérifier-lintégrité-du-téléchargement).

**Important :** la fenêtre de l'assistant local doit rester ouverte pendant la configuration ou la mise à jour. Ensuite, tu peux la fermer (ou `Ctrl+C`).

**Ce que fait l'assistant local – et ce qu'il ne fait pas :** il tourne uniquement sur ton propre ordinateur (`http://127.0.0.1:8787`) et n'est pas accessible depuis ton réseau. Après un chargement réussi, il mémorise seulement les **adresses IP** de tes deux Shelly – aucune configuration, aucun mot de passe.

### Alternative : le configurateur web seul

Fonctionne directement dans le navigateur, sans téléchargement :

👉 [Ouvrir le configurateur web](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Multiconfigurator/zendure-multi-configurator_multilang.html)

Il te permet de tout configurer et de télécharger le script terminé – **mais tu dois ensuite le charger toi-même** via l'interface web du Shelly ([instructions](#charger-un-script-manuellement)). La mise à jour et la vérification de la mémoire ne sont pas disponibles sans l'assistant local.

> Astuce : si l'assistant local tourne en arrière-plan, le configurateur web le détecte aussi et débloque les fonctions supplémentaires.

---

## 3. Première configuration

Lance l'assistant local. Dans la boîte de dialogue de démarrage, choisis **« Nouvelle configuration »**.

### Déroulement

1. **Démarrage** – choisir « Nouvelle configuration »
2. **Fonctions** – sélectionner Controller, zenDash-API et/ou Watchdog et saisir les **adresses IP de tes deux Shelly**. Si tu as déjà une configuration, tu peux l'[importer](#importer-une-configuration-existante) ici au lieu de tout ressaisir.
3. **Appareils** – tes batteries Zendure avec IP, puissance maximale et minSoc/maxSoc ; pour chaque appareil, si le Watchdog doit le surveiller
4. **Source réseau** – d'où vient la mesure de puissance réseau : le Controller tourne directement sur un Shelly Pro 3EM, un autre Pro 3EM du réseau, ou un compteur avec interface JSON (par ex. Zendure Smart Meter 3CT, Tasmota, Shelly 3EM sans Pro)
5. **Charge depuis le réseau** – quels appareils peuvent absorber le surplus d'autres installations
6. **Notifications** – webhook, Signal ou WhatsApp ; commun au Controller et au Watchdog
7. **Batterie pleine / KVS** – comment l'export réseau est géré quand les batteries sont pleines, et si tu veux modifier les réglages en direct plus tard (par ex. depuis le tableau de bord ou Home Assistant)
8. **Paramètres de régulation** – consigne, hystérésis et seuils de répartition de la puissance, déjà préremplis avec des valeurs pertinentes
9. **Résultat** – récapitulatif de tes saisies avec les numéros de version et les scripts terminés

Les étapes inutiles pour ta sélection sont sautées.

**À propos des paramètres de régulation :** les valeurs sont reprises de ta configuration importée ou calculées à partir de ta liste d'appareils selon une règle empirique. Si tu modifies plus tard les appareils ou les puissances, elles ne sont **pas** ajustées automatiquement – vérifie-les toi-même. Leur signification et les recommandations se trouvent dans la [documentation du Controller](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/readme.md) (en allemand).

**Sans KVS :** si tu désactives les réglages en direct (KVS), le tableau de bord ne peut plus qu'afficher – les modifications faites depuis le tableau de bord n'ont alors aucun effet sur le Controller.

### Les fonctions de l'étape Résultat

Pour chacun des deux Shelly, tu disposes de plusieurs possibilités :

**⚡ Charger directement** *(uniquement avec l'assistant local)*

Le moyen le plus pratique : un clic, terminé. Le script va automatiquement sur le bon Shelly (script Controller sur le Shelly Controller, zenDash-API + Watchdog sur le Shelly Dashboard), est démarré et configuré pour le démarrage automatique. S'il y a déjà d'autres scripts sur le Shelly, le configurateur te demande d'abord – voir [Plusieurs scripts sur un Shelly](#plusieurs-scripts-sur-un-shelly).

Après le premier chargement réussi, l'assistant local mémorise les IP et les saisit automatiquement la fois suivante.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/5082cdf4-1a6c-43a1-825c-8fc51bf18173" />

**🔗 Enregistrer le script complet depuis GitHub**

Charge le script original actuel depuis GitHub, y insère ta configuration et te propose le script terminé sous forme de fichier. Il ne te reste plus qu'à le [charger manuellement](#charger-un-script-manuellement). Nécessite brièvement une connexion internet.

Le nom du fichier contient la version du script, par ex. `zerooutput_multi_kvs_mini_v5.0.8.js` ou `zendash_watch_mini_v3.3.1.js`. Tu peux ainsi conserver plusieurs versions côte à côte et les [réimporter](#importer-une-configuration-existante) à tout moment.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/d839f5b2-7433-4941-977c-a7c173ab7af2" />

**📋 Copier / 💾 Enregistrer seulement le bloc CONFIG**

Uniquement la configuration – pour ceux qui ont adapté leur script eux-mêmes ou préfèrent travailler à la main. Tu remplaces ainsi le bloc `let CONFIG = { ... };` dans ton script. C'est aussi ta **copie de sauvegarde** : enregistre-la et tu pourras la réimporter à tout moment.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/1ccd9b90-9d83-42b8-892b-932ad12df4db" />

**🔍 Vérifier la mémoire** *(uniquement avec l'assistant local)*

Indique combien de mémoire de script est encore libre sur un Shelly – voir [Vérifier la mémoire d'un Shelly](#vérifier-la-mémoire-dun-shelly).

<img width="800" alt="image" src="https://github.com/user-attachments/assets/49d74a5d-cfd2-4541-932f-54c40b60ff5b" />

---

## 4. Mise à jour

Quand une nouvelle version d'un script est disponible, tu mets tes Shelly à jour en quelques clics – **tes réglages sont conservés**. La mise à jour ne fonctionne qu'avec l'[assistant local](#recommandé--lassistant-local-installateur-exe).

### Comment faire

1. Lance l'assistant local et choisis **« Mettre à jour »** dans la boîte de dialogue de démarrage.
2. Les IP de tes Shelly sont normalement déjà saisies (mémorisées lors du dernier chargement). Sinon, saisis-les une fois – au moins une.
3. Le configurateur compare les versions installées avec GitHub et affiche un tableau :

   | Statut | Signification |
   |---|---|
   | **Mise à jour disponible** | Une version plus récente existe – les modifications sont listées juste en dessous. Cochée automatiquement. |
   | **à jour** | Rien à faire. |
   | **plus récent que GitHub** | Tu as une version de test ou préliminaire – rien à faire. |
   | **non installé** / **pas de script unique** | Mise à jour impossible, choisis [« Nouvelle configuration »](#3-première-configuration). |
   | **Shelly injoignable** | voir [Messages d'erreur](#6-messages-derreur-et-situations-problématiques) |

   En dessous, tu vois aussi s'il existe une nouvelle version du configurateur/de l'assistant local lui-même – avec un lien de téléchargement.
4. Coche les scripts souhaités → **« Mettre à jour »**. Le configurateur lit ta configuration actuelle directement sur le Shelly et passe au résultat.
5. Là, clique sur **« ⚡ Charger directement »**. Le nouveau script remplace l'ancien au même emplacement (le numéro de script reste identique – important par ex. pour le proxy du tableau de bord) et est redémarré.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/fb19b123-4555-4be9-bc5d-39c16310bf12" />

### Ce que deviennent tes réglages lors d'une mise à jour

Tout est repris – y compris les valeurs que l'assistant ne demande pas (par ex. `dampingFactor`, `interval` ou les seuils d'alerte du Watchdog). Les nouveaux réglages qui n'existaient pas encore dans ton ancienne version reçoivent leur valeur par défaut.

### Mise à jour sans l'assistant local

Sans l'assistant local, passe par **« Nouvelle configuration »** : [importe](#importer-une-configuration-existante) ta configuration, clique jusqu'au bout, enregistre le nouveau script et [charge-le manuellement](#charger-un-script-manuellement).

<img width="800" alt="image" src="https://github.com/user-attachments/assets/e23c3b85-03a4-4502-9868-81c742d8e7c5" />

### Passer des anciens scripts séparés au nouveau script

zenDash-API et Watchdog forment désormais **un seul** script (`zendash_watch`). Les configurations des anciens scripts séparés (zenDash-API 2.x, Watchdog 1.x) **ne peuvent pas** être importées. Voici comment faire la transition :

1. Choisis « Nouvelle configuration » et importe la **configuration du Controller** – elle fournit les appareils, la source réseau et les notifications. Tu complètes le reste dans l'assistant.
2. Lors du chargement direct sur le Shelly Dashboard, le configurateur détecte les anciens scripts et demande s'il faut les supprimer → **« Oui, supprimer les autres et installer »**.
3. Si d'anciens scripts se trouvent sur un autre Shelly (ou si tu charges manuellement) : **arrête-les là-bas et désactive le démarrage automatique** – sinon ils continuent de tourner en parallèle et les messages arrivent en double.

---

## 5. Remplacer un Shelly

Tu remplaces un Shelly (défectueux, nouveau modèle) ou il a reçu une nouvelle adresse IP ? Voici comment emporter ta configuration :

1. **Sauvegarder la configuration.** Si tu as déjà enregistré le bloc CONFIG, utilise-le. Sinon, ouvre le script dans l'interface web de l'ancien Shelly, sous « Scripts », et copie le bloc complet `let CONFIG = { ... };`.
2. Lance l'assistant local et choisis **« Nouvelle configuration »** (la mise à jour ne fonctionne pas ici, car rien n'est encore installé sur le nouveau Shelly).
3. À l'étape « Fonctions », **importe** la configuration – idéalement Controller puis zenDash-API + Watchdog, l'un après l'autre.
4. **Seulement ensuite**, saisis l'adresse IP du nouveau Shelly. L'import reprend les IP de l'ancienne configuration et écraserait une IP saisie auparavant.
5. Parcours l'assistant et **charge directement** sur le nouveau Shelly. L'assistant local mémorise désormais la nouvelle IP.
6. Sur l'**ancien** Shelly, arrête le script et désactive le démarrage automatique (ou supprime le script) s'il reste sur le réseau.

Points d'attention :

* **Ton Shelly Controller est aussi ton Pro 3EM ?** Alors la mesure réseau change également d'appareil. Vérifie à l'étape « Source réseau » que le réglage est toujours correct.
* **Nouvelle IP du Shelly Controller :** la zenDash-API lit ses valeurs sur le Shelly Controller. Recharge donc aussi le script sur le Shelly Dashboard pour qu'il connaisse la nouvelle adresse.
* **Nouvelle IP d'une batterie Zendure :** ce n'est pas un remplacement de Shelly, mais c'est tout aussi rapide – « Nouvelle configuration », importer la configuration, modifier l'IP à l'étape « Appareils », recharger les deux scripts.
* Astuce : attribue à tes Shelly et à tes batteries une **adresse IP fixe** dans ton routeur, et cela n'arrivera plus.

---

## 6. Messages d'erreur et situations problématiques

### Plusieurs scripts sur un Shelly

⚠️ **Un seul script doit tourner par Shelly.** Les Shelly ont très peu de mémoire de script. S'il y a d'autres scripts – même arrêtés, anciens ou de test – le nouveau script peut ne pas démarrer ou planter en cours de fonctionnement. Pour le Controller, cela signifie : **ta régulation s'arrête**.

C'est pourquoi le configurateur le vérifie avant chaque chargement direct. S'il trouve d'autres scripts, il t'en affiche la liste (avec le statut « en marche »/« arrêté ») et demande :

* **« Oui, supprimer les autres et installer »** – recommandé. Les autres scripts sont supprimés.
* **« Non, garder les autres et installer »** – seulement si tu es sûr que la mémoire suffit. Vérifie-la d'abord avec [Vérifier la mémoire](#vérifier-la-mémoire-dun-shelly).
* **« Annuler »** – rien n'est modifié sur le Shelly.

S'il y a plusieurs scripts **du même type** sur le Shelly (par ex. deux Controller), « garder » n'est pas possible, car on ne saurait pas lequel mettre à jour.

Pour la même raison, le Controller et zenDash-API + Watchdog ne tournent **jamais** ensemble sur un Shelly. Le configurateur vérifie dès la première étape que deux adresses IP différentes sont saisies.

### Aperçu des messages

| Message | Qu'est-ce que cela signifie ? | Que faire ? |
|---|---|---|
| « Mettre à jour » est grisé : *Possible uniquement avec l'assistant local* | L'assistant local ne tourne pas. | Lance l'[assistant local](#recommandé--lassistant-local-installateur-exe) – il ouvre lui-même le configurateur. |
| *Ton assistant local est plus ancien que cette page …* | Une ancienne version de l'assistant local tourne encore. | Ferme l'assistant local, télécharge la version actuelle et relance-le. |
| *Shelly injoignable* | Le Shelly ne répond pas. | Vérifie l'IP (dans l'appli Shelly ou le routeur). Le Shelly est-il allumé ? L'ordinateur est-il sur le même réseau (pas le Wi-Fi invité) ? |
| Le Shelly demande un mot de passe | La protection par mot de passe du Shelly est active. | Désactive temporairement la protection par mot de passe, charge le script, puis réactive-la. |
| *non installé – choisis « Nouvelle configuration »* | Aucun script correspondant sur le Shelly. | Configure via [« Nouvelle configuration »](#3-première-configuration). |
| *pas de script unique – choisis « Nouvelle configuration »* | Plusieurs scripts du même type sur le Shelly. | « Nouvelle configuration » – laisse supprimer les autres scripts lors du chargement. |
| *Impossible de lire la config depuis le Shelly* | La configuration est introuvable dans le script (par ex. modifié à la main). | « Nouvelle configuration » et importe la configuration depuis ta sauvegarde. |
| *Impossible de charger les versions depuis GitHub* / *version GitHub inconnue* | Pas de connexion à GitHub. | Vérifie ta connexion internet, puis relance « Vérifier les versions » plus tard. |
| *Le script « … » est déjà installé sur … – mais cet appareil est prévu ici pour « … ». Les adresses IP sont-elles inversées ?* | Les IP Controller et Dashboard sont probablement inversées. | **Annule** et vérifie les IP. Ne supprime que si tu veux vraiment réaffecter le Shelly. |
| *Il y a n scripts sur …* / *Un autre script est installé sur …* | D'autres scripts sur le Shelly. | voir [Plusieurs scripts](#plusieurs-scripts-sur-un-shelly) |
| *Transfert interrompu – le script sur le Shelly est incomplet* | La connexion a été coupée pendant le chargement. **Le script ne tourne pas actuellement.** | Relance immédiatement « Charger directement ». |
| *Chargé sur …, mais le script ne tourne pas* | Le script a été transféré mais ne démarre pas. | Consulte le journal dans l'interface web du Shelly, sous « Scripts ». Causes fréquentes : mémoire insuffisante (supprimer les autres scripts) ou IP d'appareils erronées. |
| *⚠️ Seulement … octets libres* | La mémoire est juste. | Supprime les autres scripts du Shelly. |
| *Il s'agit d'une configuration dans l'ancien format …* | Configuration des anciens scripts séparés. | voir [Transition](#passer-des-anciens-scripts-séparés-au-nouveau-script) |
| *Impossible de déterminer à quel produit appartient cette configuration* | Copie incomplète. | Colle le bloc complet de `let CONFIG = {` jusqu'à `};`. |
| *Le Shelly Controller et le Shelly Dashboard doivent être deux appareils différents* | La même IP a été saisie deux fois. | Utilise deux Shelly différents. |
| *Erreur : … vérifie ta connexion internet …* lors du téléchargement du script | GitHub injoignable. | Vérifie ta connexion internet. |

### Problèmes avec l'assistant local

| Situation | Que faire ? |
|---|---|
| La fenêtre de l'assistant local se ferme aussitôt ou indique qu'elle n'a pas pu écouter sur 127.0.0.1:8787 | L'assistant local tourne déjà (autre fenêtre, peut-être réduite) – utilise-la, ou ferme-la et relance. |
| Le navigateur ne s'ouvre pas | Ouvre `http://127.0.0.1:8787` dans ton navigateur. |
| Windows/macOS bloque le lancement | voir [Où trouver le configurateur](#recommandé--lassistant-local-installateur-exe) |
| Le configurateur propose de mauvaises IP de Shelly | Écrase simplement l'IP dans le champ – ou [réinitialise](#réinitialiser-les-ip-mémorisées) les IP mémorisées. |

---

## 7. Guides pratiques

### Importer une configuration existante

À l'étape « Fonctions », sous **« Importer une configuration existante pour la mettre à jour »**, colle un bloc complet `let CONFIG = { ... };` **ou** sélectionne un fichier enregistré avec **« 📂 Charger un fichier… »**, puis clique sur « Importer & appliquer ». Tu peux charger soit le fichier issu de « 💾 Enregistrer seulement le bloc CONFIG », soit un script complet issu de « 🔗 Enregistrer le script complet depuis GitHub » – le fichier arrive d'abord dans le champ de texte et n'est appliqué qu'au clic. Le configurateur détecte lui-même s'il s'agit du Controller ou de zenDash-API + Watchdog. Idéalement, importe les deux l'un après l'autre – l'ordre n'a pas d'importance. Les IP des Shelly sont reprises en même temps.

### Charger un script manuellement

Sans l'assistant local (les instructions sont aussi disponibles en section dépliable dans le configurateur) :

1. À l'étape Résultat, clique sur « 🔗 Enregistrer le script complet depuis GitHub ».
2. Ouvre l'IP du Shelly dans le navigateur (par ex. `http://192.168.178.151`) et va dans « Scripts ».
3. Arrête et supprime un ancien script du même nom. **Supprime aussi les autres scripts** (voir [Plusieurs scripts](#plusieurs-scripts-sur-un-shelly)).
4. « Add script », donne un nom, enregistre.
5. Ouvre le fichier téléchargé dans un éditeur de texte, copie tout et colle-le dans l'éditeur de code.
6. « Save », puis « Start », et active **« Enable on boot »**.
7. Vérifie dans le journal que le script tourne sans erreur.

### Vérifier la mémoire d'un Shelly

Avec l'assistant local en marche, saisis à l'étape Résultat l'IP de n'importe quel Shelly et clique sur **« 🔍 Vérifier la mémoire »**. À partir de **25 200 octets** de mémoire libre, tout va bien. Cela fonctionne aussi sur un Shelly neuf sans script.

Pour information : le script zenDash-API + Watchdog occupe, avec deux batteries, environ 13,5 ko en fonctionnement et environ 17,8 ko en pointe.

### Sauvegarder la configuration

Après chaque modification, clique à l'étape Résultat sur « 💾 Enregistrer seulement le bloc CONFIG » ou « 🔗 Enregistrer le script complet depuis GitHub » et conserve le fichier. Le script complet porte la version dans son nom de fichier – pratique si tu veux garder plusieurs versions. Tu peux [réimporter](#importer-une-configuration-existante) les deux fichiers plus tard avec « 📂 Charger un fichier… ». Ainsi, en cas de panne ou de remplacement d'un Shelly, tu es de nouveau opérationnel en quelques minutes.

### Enregistrer le journal

Pour le diagnostic – par exemple quand un script ne démarre pas ou se comporte bizarrement – le configurateur enregistre les messages d'un Shelly. Cela ne fonctionne qu'avec l'[assistant local](#recommandé--lassistant-local-installateur-exe).

1. Dans la boîte de dialogue de démarrage, choisis **« Enregistrer le journal »**.
2. Saisis l'IP du Shelly (ou clique sur Shelly Controller / Shelly Dashboard) puis sur **« Afficher les scripts »**.
3. Sélectionne le script souhaité.
4. Choisis la durée : **140 secondes** ou **600 secondes** (10 minutes).
5. Clique sur **« Démarrer l'enregistrement »**.

L'assistant local arrête le script, le redémarre et enregistre pendant la durée choisie. Le journal est ensuite enregistré automatiquement dans un fichier, par ex. `zerooutput_multi_kvs_v5.0.8_260927-1432.log`. Les dernières lignes s'affichent directement dans le configurateur. Si le script ne tourne pas après l'enregistrement, le configurateur le signale – la cause figure alors généralement dans le journal.

* **Filtré (par défaut) :** « Enregistrer uniquement les sorties du script choisi » est coché – le journal ne contient que ce que le script affiche lui-même.
* **Sans filtre :** décoche la case – tous les messages du Shelly sont alors ajoutés, messages système compris. C'est nécessaire si le script ne démarre pas, car le Shelly signale les erreurs de démarrage ou le manque de mémoire sous forme de messages système. Les lignes du script sont alors marquées `[Script 8]`.

À propos de la taille : pour le Controller, 600 secondes représentent environ 150 cycles de régulation. Filtré, le journal fait environ 100 à 300 Ko selon le nombre de batteries, sans filtre davantage – aucun problème pour un éditeur de texte.

⚠️ Pour le Controller, la régulation s'interrompt quelques secondes pendant le redémarrage. Laisse la page et l'assistant local ouverts jusqu'à la fin. Si le journal de débogage est désactivé sur le Shelly, l'assistant local ne l'active que pour l'enregistrement et le désactive ensuite.

Pour des enregistrements sur plusieurs heures, utilise le [WebSocket Log Grabber](https://github.com/surfer1264/Zendure-Stuff/tree/main/shelly_script/Script_poller) (en allemand).

### Réinitialiser les IP mémorisées

L'assistant local enregistre les IP dans le fichier `zendure_helper_config.json` – soit à côté du fichier de l'assistant local, soit, s'il ne peut pas écrire à cet endroit, ici :

* **Windows :** `%APPDATA%\ZendureHelper\`
* **macOS :** `~/Library/Application Support/ZendureHelper/`

Supprime le fichier, et le configurateur redemandera les IP au prochain démarrage.

### Vérifier l'intégrité du téléchargement

Pour chaque fichier, la [page des releases](https://github.com/surfer1264/Zendure-Stuff/releases/latest) contient un fichier `.sha256` du même nom. Il te permet de vérifier que ton téléchargement est exactement le fichier produit par le build.

**Windows (PowerShell)** – affiche `True` ou `False` :

```powershell
(Get-FileHash .\zendure_local_helper-windows.exe -Algorithm SHA256).Hash -eq (Get-Content .\zendure_local_helper-windows.exe.sha256).Split(' ')[0]
```

Pour la version 32 bits, utilise `zendure_local_helper-windows-x86.exe`.

**macOS (Terminal) :**

```bash
shasum -a 256 -c zendure_local_helper-macos.sha256
```

`OK` = tout est en ordre. `FAILED` = ne **pas** exécuter le fichier, le télécharger à nouveau.
