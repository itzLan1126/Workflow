"""Disposable mutation copies inside a disposable parent directory."""
from contextlib import contextmanager
from pathlib import Path
import shutil
import tempfile


@contextmanager
def isolated(project, enabled):
    if not enabled:
        yield project
        return
    # The parent is disposable so siblings such as Muter's <project>_mutated stay inside it.
    with tempfile.TemporaryDirectory(prefix='workflow-overlay-') as directory:
        target = Path(directory) / project.name
        # shortcut: every file is a private copy because a link is writable into the original;
        # add read-only links only if a project proves too large to copy.
        shutil.copytree(project, target, ignore=shutil.ignore_patterns('.git'))
        yield target
