import os

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import StaticFilesStorage


class VersionedStaticFilesStorage(StaticFilesStorage):
    """Development counterpart of the manifest storage used in production.

    Every {% static %} URL carries the file's modification time (?v=...), so the
    browser can cache it for good and still picks up an edit right away, because
    the edit changes the URL. Production gets the same effect from
    CompressedManifestStaticFilesStorage, which puts a content hash in the name.
    """

    def url(self, name):
        url = super().url(name)
        path = finders.find(name)
        if not path:
            return url
        version = format(int(os.stat(path).st_mtime), "x")
        return f"{url}{'&' if '?' in url else '?'}v={version}"
