# Psychologie de l'enfant et de l'adolescent

Outils pédagogiques fondés sur les preuves, pour comprendre les enfants et les adolescents et agir avec eux.
Site statique, en français, destiné d'abord aux parents, aux bénévoles d'association et aux personnes qui
encadrent des jeunes, à Madagascar.

Auteur : **Dr. FENOHASINA Toto Jean Felicien** — psychiatre, analyste de donnée, développeur d'application web.

Première session publiée : **Comprendre et agir face au harcèlement scolaire** (5 septembre 2026), 18 modules
en 5 étapes, avec glossaire sourcé, bibliographie APA 7 et fonctionnement hors ligne.

## Principes

- **Deux niveaux de lecture dans la même page.** Le texte principal se suffit à lui-même. Les encadrés
  « Approfondir » donnent la source, la méthode et le chiffre exact. Aucun accordéon, aucun « lire plus » :
  tout est visible, et un réglage global permet de masquer les encadrés pour tout le site.
- **Chaque affirmation scientifique porte sa source**, au format APA 7, avec DOI ou URL vérifiée, et un
  niveau de preuve explicite (preuve établie, consensus, hypothèse, opinion d'expert, preuve faible, lacune).
- **Chaque terme technique est défini.** Les termes sont liés automatiquement à leur entrée de glossaire :
  survol pour la définition courte, ouverture pour la définition complète et sa source, puis retour exact
  à la position de lecture.
- **Ce qu'on ne sait pas est dit.** Les lacunes de la recherche malgache sont énoncées comme telles.
- **Sobriété technique.** Aucun framework, aucune dépendance npm, aucun traceur. Le site fonctionne sur un
  téléphone bas de gamme et reste consultable hors ligne après une première visite.

## Structure

```
index.html                     hub (généré)
harcelement-scolaire/          session 1 : sommaire, 18 modules, méthode et limites, éthique (générés)
glossaire.html  references.html   pages partagées (générées)
assets/css  assets/js  assets/fonts  assets/icons
data/                          glossaire, références, figures, schémas, quiz, interactifs, index de recherche
src/site.json                  manifeste : sessions, étapes, pages
src/shell/                     coquille commune (head, en-tête, navigation, pied)
src/body/                      corps des pages, en HTML
src/css/  src/js/  src/figures/  sources du design system, des modules ES et des figures
src/research/                  sources vérifiées, liens contrôlés à la main, rapports de relecture
scripts/                       build.py et les outils d'assemblage
manifest.webmanifest  sw.js    application web installable, hors ligne
```

Les fichiers générés portent un en-tête « ne pas éditer » : la source de vérité est `src/` et `data/`.

## Construire le site

```bash
python scripts/build.py            # assemble tout ; échoue sur toute erreur de validation
python scripts/build.py --lenient  # signale sans arrêter, pendant la rédaction
python scripts/build.py --check    # n'écrit rien, liste ce qui changerait
python scripts/serve.py            # http://localhost:8765/Psychologie_de_l_enfant_et_de_l_adolescent/
```

Le build refuse de produire une page si un terme de glossaire ou une clé de référence est inconnu, si un
lien interne est cassé, si un `h2` n'a pas d'identifiant, si un accordéon apparaît, si les encadrés
« Approfondir » dépassent 40 % des mots d'un module, ou si un module n'a ni « Ce que je retiens », ni quiz,
ni section de références.

## Outils

| Script | Rôle |
|---|---|
| `build.py` | assemble les pages, résout citations et termes, génère l'index de recherche, le sitemap et le service worker |
| `figures.py` | produit les graphiques de données depuis `data/figures.json` |
| `schemas.py` | produit les schémas conceptuels depuis `data/schemas.json` |
| `build_references.py` | construit `data/references.json` depuis les sources vérifiées et les corrections manuelles |
| `check_links.py` | vérifie les DOI auprès de Crossref et les URL par requête HTTP |
| `fetch_fonts.py` | télécharge les polices Literata et Public Sans en WOFF2 auto-hébergés |
| `serve.py` | sert le dépôt sous le sous-chemin de GitHub Pages, avec gzip et vrais 404 |
| `extract_malgache.py` | page de relecture des 54 passages en malgache, avec leur contexte français |
| `pwa_offline_test.py`, `viewport_check.py` | Chrome headless indépendant : service worker hors ligne ; aucun défilement horizontal de 280 à 768 px et à 200 % de zoom texte |

Les outils qui ont servi une fois à fabriquer le contenu — extraction des recherches, préparation des
entrées d'agents, intégration de leurs sorties, contrôle de migration de l'ancien outil — ont été retirés
du dépôt et de son historique après publication, avec leurs fichiers de travail : ce qui reste ici suffit
à reconstruire le site à l'identique.

## Choix techniques

**Pas de framework.** Le contenu est documentaire et sans état complexe : React aurait alourdi le
chargement sur les téléphones bas de gamme sans rien apporter. Le site est du HTML, du CSS et quelques
modules JavaScript chargés seulement quand la page en a besoin. Tout le contenu reste lisible sans
JavaScript.

**GitHub Pages.** Hébergement gratuit, flux identique aux autres dépôts de l'auteur, aucune configuration.
Cloudflare Pages offrirait un point de présence à Antananarivo et une bande passante illimitée : la bascule
resterait possible sans changer une ligne de code.

## Licence

Contenu et code sous licence [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.fr) :
partage et adaptation libres pour un usage non commercial, avec attribution et sous la même licence.
Polices Literata et Public Sans sous SIL Open Font License 1.1.

Cet outil est pédagogique. Il ne remplace pas une consultation.
