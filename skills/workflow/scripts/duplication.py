#!/usr/bin/env python3
"""Check explicitly selected sources against the fixed duplication standard."""
from importlib.metadata import version
import json
import sys

from shared_duplication import calculate
from shared_languages import arguments, evidence_directory, language


def selected_sources(args):
    if not args or args[0] != 'python':
        raise ValueError('Usage: duplication.py python PROJECT SOURCE_FILE...; only Python is supported')
    if '--timeout-ms' in args:
        raise ValueError('Duplication check does not accept timeout overrides')
    project, sources, _, tool = arguments(args[1:])
    if not sources or tool:
        raise ValueError('Require source files; tool overrides are not supported')
    return project, sources


def dispatch(args):
    project, sources = selected_sources(args)
    evidence = evidence_directory()
    config = {'cwd': str(project), 'sources': sources}
    config['parserVersions'] = {name: version(name) for name in ('tree-sitter', 'tree-sitter-language-pack')}
    (evidence / 'config.json').write_bytes(json.dumps(config).encode())
    entries = collect(project, sources)
    measurements = [{**entry, 'fingerprints': sorted(entry['fingerprints'])} for entry in entries]
    (evidence / 'measurements.json').write_bytes(json.dumps(measurements).encode())
    result = {**calculate(entries), 'sources': sources, 'parserVersions': config['parserVersions']}
    (evidence / 'result.json').write_bytes(json.dumps(result).encode())
    print(json.dumps(result))
    return 1 if result['findings'] else 0


def collect(project, sources):
    entries = []
    seen = set()
    for source in sources:
        path = (project / source).resolve()
        if path.suffix != '.py':
            raise ValueError(f'Unsupported source file: {source}')
        if path in seen:
            continue
        seen.add(path)
        entries.extend(language('python').duplication_entries(path, source))
    return entries


def main(argv=None):
    try:
        return dispatch(sys.argv[1:] if argv is None else argv)
    except (OSError, ValueError, ImportError, KeyError, TypeError, IndexError, RuntimeError) as error:
        print(f'Duplication: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
