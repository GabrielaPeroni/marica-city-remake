import os
import sys


def main():
    # Defaults to dev settings so local workflows keep working unchanged;
    # set DJANGO_SETTINGS_MODULE=config.settings.prod explicitly in
    # production deployments (see config/settings/README or CLAUDE.md).
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. Você tem certeza de que está instalado e "
            "disponível na sua variável de ambiente PYTHONPATH? Você "
            "esqueceu de ativar o ambiente virtual?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
