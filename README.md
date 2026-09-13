# MaricaCity - Sistema de turismo local

Este projeto é um **remake** de um aplicativo feito para o projeto Qualifica Maricá
O repositório original pode ser encontrado aqui: [Marica-City](https://github.com/GabrielaPeroni/Marica-City).

- Projeto criado para fins acadêmicos para a matéria 'Desenvolvimento Rápido em Python'
- A estrutura permite adicionar múltiplos apps e páginas facilmente.
- Todas as dependências gerenciadas com [uv](https://docs.astral.sh/uv/).

Para mais detalhes sobre a implementação do CRUD, consulte [CRUD.md](./documentacao/CRUD.md), e para uma visão completa da estrutura do projeto e arquitetura, consulte [STRUCTURE.md](./documentacao/STRUCTURE.md)

- Exercicios da materia se encontram na pasta [aula_exercicios](./aula_exercicios)

# 🚀 Como rodar o projeto

### Pre-requisitos

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado

### 1. Instale as dependências:

```bash
uv sync
```

### 2. Rode migrations:

```bash
uv run python manage.py migrate
```

### 3. Crie um superuser (opcional):

```bash
uv run python manage.py createsuperuser
```

### 4. Rode o servidor:

```bash
uv run python manage.py runserver
```

## 📜 Licença

- **Código Django**: [MIT](./documentacao/LICENSE.txt).
