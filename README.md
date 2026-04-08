# LinkedIn Auto Research

Pipeline automatisé pour:
- générer un lead magnet chaque jour,
- écrire le post LinkedIn associé,
- publier automatiquement via Blotato,
- journaliser les runs dans Notion,
- analyser chaque semaine les performances via Apify.

## Setup

1. Copier `.env.example` en `.env`.
2. Renseigner les clés API (Claude/Anthropic, Notion, Blotato, Apify).
3. Installer les dépendances:

```bash
pip install -r requirements.txt
```

## Exécution locale

Daily:

```bash
python src/main.py --mode daily
```

Weekly:

```bash
python src/main.py --mode weekly
```

## GitHub Actions

Deux workflows sont inclus:
- `.github/workflows/linkedin-daily.yml` (quotidien)
- `.github/workflows/linkedin-weekly-strategy.yml` (hebdomadaire)

Configurer les secrets GitHub suivants:
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
- `NOTION_API_TOKEN`, `NOTION_LEAD_MAGNET_DB_ID`, `NOTION_RUNS_DB_ID`
- `BLOTATO_API_KEY`, `BLOTATO_ACCOUNT_ID`, `BLOTATO_BASE_URL`
- `APIFY_API_TOKEN`, `APIFY_ACTOR_ID_LINKEDIN_METRICS`
- `LINKEDIN_PROFILE_URL`

## Notion: schéma de base recommandé

Lead magnet DB:
- `Name` (title)
- `Type` (select: guide/framework/prompt_pack)
- `CTA Keyword` (rich text)

Runs DB:
- `Name` (title)
- `Status` (select: draft/published/failed/skipped)
- `Asset Title` (rich text)
- `LinkedIn Post` (rich text)
- `Topic` (rich text)

## Notes

- Sans clé `ANTHROPIC_API_KEY`, le système utilise un fallback de génération.
- En `DRY_RUN=true`, il n’y a pas d’autopublication Blotato.
- Les artefacts sont écrits dans `artifacts/` et `reports/`.
