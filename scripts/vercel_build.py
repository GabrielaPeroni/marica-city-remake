"""Vercel build step (pyproject [tool.vercel.scripts]): migrate, demo content, admin.

Runs with the project's environment variables (DATABASE_URL, R2 keys...). The
superuser is created only when DJANGO_SUPERUSER_USERNAME/PASSWORD/EMAIL are set.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.management import call_command  # noqa: E402

call_command("migrate", interactive=False)
call_command("load_demo_data")

username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
if username and not get_user_model().objects.filter(username=username).exists():
    call_command("createsuperuser", interactive=False)
