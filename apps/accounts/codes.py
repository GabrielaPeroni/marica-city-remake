"""Códigos de 6 dígitos enviados por e-mail (confirmação de cadastro e de senha)."""

import json
import re
import secrets
import time
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.crypto import constant_time_compare, salted_hmac

SIGNUP = "signup"
PASSWORD_RESET = "password_reset"

CODE_TTL = 15 * 60
MAX_ATTEMPTS = 5

# A linha do código no e-mail (accounts/emails/code.txt) contém só os 6 dígitos
CODE_LINE = re.compile(r"^\s*(\d{6})\s*$", re.MULTILINE)


def _key(purpose, email):
    return f"email-code:{purpose}:{email.lower()}"


def _digest(purpose, email, code):
    return salted_hmac(_key(purpose, email), code).hexdigest()


def _autofill_mode(email):
    """Modo de preenchimento automático que vale para `email` ("" = nenhum)"""
    mode = settings.EMAIL_CODE_AUTOFILL
    if mode == "mailhog" and not settings.DEBUG:
        return ""
    domains = settings.EMAIL_CODE_AUTOFILL_DOMAINS
    domain = email.rsplit("@", 1)[-1].lower()
    return mode if "*" in domains or domain in domains else ""


def send_code(purpose, email, subject):
    """Gera um código novo (invalida o anterior) e o envia; erros de SMTP sobem"""
    code = f"{secrets.randbelow(10**6):06d}"
    entry = {
        "digest": _digest(purpose, email, code),
        "attempts": 0,
        "expires": time.time() + CODE_TTL,
    }
    server_autofill = _autofill_mode(email) == "server"
    if server_autofill:
        entry["autofill"] = code
    cache.set(_key(purpose, email), entry, CODE_TTL)
    if server_autofill:
        # Domínio de teste (homologação): não existe caixa de entrada para receber
        return
    body = render_to_string(
        "accounts/emails/code.txt",
        {"code": code, "purpose": purpose, "minutes": CODE_TTL // 60},
    )
    send_mail(subject, body, None, [email])


def check_code(purpose, email, code):
    """Consome o código se estiver certo; após MAX_ATTEMPTS erros ele é descartado"""
    key = _key(purpose, email)
    entry = cache.get(key)
    if not entry:
        return False
    if constant_time_compare(entry["digest"], _digest(purpose, email, code.strip())):
        cache.delete(key)
        return True
    entry["attempts"] += 1
    remaining = entry["expires"] - time.time()
    if entry["attempts"] >= MAX_ATTEMPTS or remaining <= 0:
        cache.delete(key)
    else:
        cache.set(key, entry, remaining)
    return False


def autofill_code(purpose, email):
    """Código para pré-preencher a tela, fora de produção (ver EMAIL_CODE_AUTOFILL)"""
    mode = _autofill_mode(email)
    if mode == "server":
        return (cache.get(_key(purpose, email)) or {}).get("autofill", "")
    if mode == "mailhog":
        return _mailhog_code(email)
    return ""


def _mailhog_code(email):
    query = urlencode({"kind": "to", "query": email, "limit": 1})
    try:
        with urlopen(
            f"{settings.MAILHOG_API_URL}/api/v2/search?{query}", timeout=2
        ) as r:
            items = json.load(r).get("items") or []
    except (OSError, ValueError):
        return ""
    if not items:
        return ""
    match = CODE_LINE.search(items[0]["Content"]["Body"])
    return match.group(1) if match else ""
