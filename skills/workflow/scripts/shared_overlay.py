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
        shutil.copytree(project, target, symlinks=True, ignore=shutil.ignore_patterns('.git'))
        for link in target.rglob('*'):
            if link.is_symlink():
                relocate_link(link, project, target)
        yield target


def relocate_link(link, project, target):
    original = project / link.relative_to(target)
    # A dangling link inside the project stays dangling; one pointing outside fails the copy.
    destination = original.resolve()
    link.unlink()
    if destination.is_relative_to(project):
        # shortcut: Windows directory links need target_is_directory; add it if overlays run there.
        link.symlink_to(target / destination.relative_to(project))
    elif destination.is_dir():
        shutil.copytree(destination, link)
    else:
        shutil.copy2(destination, link)
