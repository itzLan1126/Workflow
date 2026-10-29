#!/usr/bin/env python3
"""Check explicitly selected sources against the fixed duplication standard."""
from importlib.metadata import version
import json
import sys

from shared_duplication import calculate
from shared_tools import options, python_tools
from shared_languages import LANGUAGES, arguments, evidence_directory, language

USAGE = 'Usage: duplication.py LANGUAGE PROJECT SOURCE_FILE...'
EXTENSIONS = {'python': {'.py'}, 'js': {'.js', '.jsx', '.mjs', '.cjs'},
              'ts': {'.ts', '.tsx'}, 'rust': {'.rs'}, 'swift': {'.swift'}}


def selected_sources(args):
    if not args or args[0] not in LANGUAGES:
        raise ValueError(USAGE)
    if '--timeout-ms' in args:
        raise ValueError('Duplication check does not accept timeout overrides')
    project, sources, _, tool = arguments(args[1:])
    if not sources or tool:
        raise ValueError('Require source files; tool overrides are not supported')
    return project, sources


def dispatch(args):
    args, install = options(args)
    project, sources = selected_sources(args)
    with python_tools(['tree-sitter', 'tree-sitter-language-pack'], project, install) as tools:
        return prepared_result(args[0], project, sources, tools)


def prepared_result(name, project, sources, tools):
    evidence = evidence_directory()
    config = {'cwd': str(project), 'sources': sources, 'tools': tools}
    config['parserVersions'] = {name: version(name) for name in ('tree-sitter', 'tree-sitter-language-pack')}
    (evidence / 'config.json').write_bytes(json.dumps(config).encode())
    if name == 'swift':
        result = {'findings': 0, 'pairs': [], 'sources': sources, 'unverified': 'language not supported'}
        (evidence / 'result.json').write_bytes(json.dumps(result).encode())
        print(json.dumps(result))
        return 1
    entries = collect(project, sources, name)
    measurements = [{**entry, 'fingerprints': sorted(entry['fingerprints'])} for entry in entries]
    (evidence / 'measurements.json').write_bytes(json.dumps(measurements).encode())
    result = {**calculate(entries), 'sources': sources, 'parserVersions': config['parserVersions']}
    (evidence / 'result.json').write_bytes(json.dumps(result).encode())
    print(json.dumps(result))
    return 1 if result['findings'] else 0


def collect(project, sources, name):
    entries = []
    seen = set()
    for source in sources:
        path = (project / source).resolve()
        if path.suffix not in EXTENSIONS[name]:
            raise ValueError(f'Unsupported source file: {source}')
        if path in seen:
            continue
        seen.add(path)
        entries.extend(language(name).duplication_entries(path, source))
    return entries


def main(argv=None):
    try:
        return dispatch(sys.argv[1:] if argv is None else argv)
    except (OSError, ValueError, ImportError, KeyError, TypeError, IndexError, RuntimeError) as error:
        print(f'Duplication: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
