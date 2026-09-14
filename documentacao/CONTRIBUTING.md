# Contribuindo com o MaricaCity

Guia prático para configurar o ambiente, rodar testes/lint e abrir PRs neste
repositório. Assume familiaridade básica com Django; para a arquitetura
completa veja [STRUCTURE.md](./STRUCTURE.md) e [CRUD.md](./CRUD.md).

## Setup do ambiente

Pré-requisitos: Python 3.10+ e [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone <repo>
cd marica-city-remake
uv sync                      # cria .venv/ e instala deps (inclui o grupo dev)
cp .env.example .env         # preencha SECRET_KEY e GOOGLE_OAUTH_CLIENT_ID no mínimo
uv run python manage.py migrate
uv run python manage.py createsuperuser   # opcional
uv run python manage.py runserver
```

Não existe Makefile neste projeto — todos os comandos passam por `uv run`.
`config.settings.dev` é o módulo de settings padrão (SQLite, `DEBUG=True`,
hosts permissivos); produção usa `config.settings.prod` (ver
[DEPLOYMENT.md](./DEPLOYMENT.md)).

### Alternativa: docker-compose

```bash
docker compose up --build
```

Sobe o app (settings `prod`) + Postgres + Redis. Útil para testar mais perto
de produção; a rota `uv run manage.py runserver` continua funcionando sem
Docker para o dia a dia. Detalhes em [DEPLOYMENT.md](./DEPLOYMENT.md).

## Rodando os testes

```bash
uv run python manage.py test apps            # suíte completa (127 testes)
uv run python manage.py test apps.explore    # um app específico
uv run python manage.py test apps.explore.tests.PlaceModelTests  # uma classe
```

Cobertura, com o piso de 70% que a CI aplica:

```bash
uv run coverage run manage.py test apps
uv run coverage report --fail-under=70
```

Os testes ainda vivem em um único `apps/<app>/tests.py` por app (não em
pacotes `tests/`) — ao adicionar testes para uma feature nova, siga o padrão
já usado no arquivo do app correspondente.

## Lint e formatação

Python:

```bash
uv run black .
uv run isort .
uv run autoflake --in-place --remove-all-unused-imports --remove-unused-variables \
  --remove-duplicate-keys --ignore-init-module-imports --recursive apps/ config/ manage.py
uv run flake8 --select=TMS010,TMS011,TMS012,TMS013,TMS020,TMS021,TMS022 apps/ config/ manage.py
uv run mypy .          # opcional, não é gate de CI
uv run pip-audit       # auditoria de vulnerabilidades nas dependências
```

JavaScript (`static/js/`):

```bash
npm install
npm run lint:js        # ESLint
npm run build:js       # bundle esbuild (só necessário ao testar o build de produção)
```

Markdown/JSON/CSS/HTML: `prettier` (config em `.github/.prettierrc`), aplicado
via pre-commit.

### Pre-commit

```bash
uv run pre-commit install
```

Depois disso, cada commit roda automaticamente: trailing-whitespace,
end-of-file-fixer, check-yaml/json/toml/xml, check-merge-conflict,
debug-statements, black, isort, autoflake, flake8, prettier e uma checagem
customizada de arquivos `__init__.py` (`.github/check_innit.py`). Rode
`uv run pre-commit run --all-files` para validar o repo inteiro de uma vez.

## Migrações

Qualquer alteração em `apps/*/models.py` precisa de uma migração no mesmo PR:

```bash
uv run python manage.py makemigrations
uv run python manage.py makemigrations --check --dry-run   # o que a CI roda
```

A CI falha se houver mudanças de model sem migração correspondente.

## Commits e branches

O projeto usa [Conventional Commits](https://www.conventionalcommits.org/)
(`commitizen` está configurado em `[tool.commitizen]` no `pyproject.toml` para
gerar `CHANGELOG.md` e tags `vX.Y.Z`). Prefixos comuns:

- `feat:` — nova funcionalidade
- `fix:` — correção de bug
- `docs:` — apenas documentação
- `test:` — apenas testes
- `refactor:` / `perf:` / `chore:` / `ci:`

Use `uv run cz commit` para montar a mensagem interativamente, se preferir.

Branches: crie a partir de `main` atualizada (`git pull` antes de ramificar),
com um nome descritivo (`fix/…`, `feat/…`, `docs/…`). Abra o PR contra `main`.

## O que a CI verifica

Todo PR roda `.github/workflows/pr-checks.yml`:

- **Linters**: checagem de `__init__.py`, `black --check`, `isort --check-only`,
  `autoflake --check`, `flake8`, `pip-audit`, `prettier --check`.
- **Tests**: `check --deploy`, `makemigrations --check --dry-run`, a suíte
  Django completa contra Postgres, e `coverage report --fail-under=70`.

`.github/workflows/codeql.yml` roda CodeQL (Python + JS/TS) em push/PR para
`main` e semanalmente. O Dependabot (`.github/dependabot.yml`) abre PRs de
atualização de dependências pip/npm/Actions automaticamente — revise se o
`uv.lock`/`package-lock.json` foi regenerado antes de aprovar.

Um PR só é mergeável se todos os checks acima passarem. Rode a suíte de lint
e os testes localmente antes de abrir o PR para evitar voltas.

## Documentação

Ao alterar models, views, permissões ou fluxos principais, atualize também
[CRUD.md](./CRUD.md) e [STRUCTURE.md](./STRUCTURE.md) no mesmo PR — é a
convenção estabelecida no `CLAUDE.md` do projeto e o checklist do PR cobra
isso.
