"""Seal mutation snapshots and carry forward only unchanged non-actionable outcomes."""
import hashlib
import json
from pathlib import Path

from shared_runner import parse_json, read_json
from shared_mutation import ACTIONABLE, adapter, mutant_status, validate_detail

SCHEMA = 2
SOURCE_SUFFIXES = {'.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.rs', '.swift'}
CONFIG_SUFFIXES = {'.toml', '.json', '.cfg', '.ini', '.yaml', '.yml', '.lock'}
CONFIG_PREFIXES = ('requirements', 'stryker.config', 'muter.conf')
EXCLUDED_PARTS = {'.git', '.venv', 'venv', 'node_modules', 'target', '.build', '__pycache__',
                  'mutants', 'mutants.out', 'reports', '.stryker-tmp'}
TEST_PARTS = {'tests', 'test', '__tests__'}
TEST_PREFIX = 'test_'
TEST_SUFFIXES = ('_test', '.test', '.spec', 'Tests')
# Any of these changing means earlier outcomes were produced under different rules.
INVALIDATING = ('tests', 'engine', 'configuration', 'module')
SNAPSHOT, OUTCOMES = 'snapshot.json', 'outcomes.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(project, module, engine):
    paths = [p for p in sorted(project.rglob('*')) if p.is_file() and not excluded(p.relative_to(project))]
    current = {'schema': SCHEMA, 'files': {}, 'functions': {}, 'tests': {}, 'configuration': {},
               'engine': engine, 'module': digest(Path(module.__file__).read_bytes()), 'moduleSources': {}}
    for path in paths:
        record(current, path.relative_to(project), path.read_bytes())
    return current


def record(current, relative, data):
    kind = category(relative)
    if kind:
        current[kind][relative.as_posix()] = digest(data)
    if kind == 'files':
        current['functions'].update(function_hashes(relative.as_posix(), data))
        if relative.suffix == '.py':
            current['moduleSources'][relative.as_posix()] = python_module_hash(data)


def category(relative):
    if is_test(relative):
        return 'tests'
    if relative.suffix in SOURCE_SUFFIXES:
        return 'files'
    if relative.suffix in CONFIG_SUFFIXES or relative.name.startswith(CONFIG_PREFIXES):
        return 'configuration'
    return None


def excluded(relative):
    return bool(set(relative.parts) & EXCLUDED_PARTS)


def is_test(relative):
    return relative.suffix in SOURCE_SUFFIXES and (
        bool({part.lower() for part in relative.parts[:-1]} & TEST_PARTS)
        or relative.name.startswith(TEST_PREFIX) or relative.stem.endswith(TEST_SUFFIXES))


def function_hashes(file, data):
    import lizard
    text = data.decode()
    lines = text.splitlines()
    return {f'{file}:{f.name}:{f.start_line}': digest(repr(lines[f.start_line - 1:f.end_line]).encode())
            for f in lizard.analyze_file.analyze_source_code(file, text).function_list}


def python_module_hash(data):
    import ast
    tree = ast.parse(data)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            del node.body
    return digest(ast.dump(tree).encode())


def load_previous(directory):
    directory = Path(directory)
    try:
        manifest = read_json(directory / SNAPSHOT)
        encoded = (directory / OUTCOMES).read_bytes()
        seal = manifest.pop('sha256')
        if (seal != digest(canonical(manifest)) or manifest['schema'] != SCHEMA
                or manifest['outcomesSha256'] != digest(encoded)):
            raise ValueError('seal mismatch')
        return manifest, parse_json(encoded.decode())
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise ValueError(f'Damaged previous mutation evidence in {directory}: {error}') from error


def canonical(value):
    return json.dumps(value).encode()


def plan(current, previous, by_function):
    """Return reused outcomes, files and functions to run (None means all), and any fallback."""
    old, outcomes = previous
    fallback = full_run_reason(current, old, outcomes)
    if fallback:
        return [], None, None, fallback
    edited = changed_keys(current['files'], old['files'])
    changed = (edited | actionable(outcomes, 'sourceFile')) & current['files'].keys()
    if by_function and all(item['functionKey'] for item in outcomes):
        return function_plan(current, old, outcomes, changed, edited)
    return reusable(outcomes, 'sourceFile', current['files'], changed), sorted(changed), None, 'full file'


def full_run_reason(current, old, outcomes):
    if old['files'].keys() - current['files'].keys():
        return 'full run: source files were deleted'
    if any(current[key] != old[key] for key in INVALIDATING):
        return 'full run: tests, engine, configuration or language module changed'
    if any(item['sourceFile'] is None for item in outcomes):
        return 'full run: previous outcomes are not bound to source files'
    return None


def function_plan(current, old, outcomes, changed_files, edited_files):
    functions = current['functions']
    edited = changed_keys(functions, old['functions'])
    selected = edited | actionable(outcomes, 'functionKey')
    for file in edited_files:
        in_file = {key for key in functions if key.startswith(file + ':')}
        # A changed file with no edited function was edited outside them, which can affect them all.
        if module_changed(current, old, file):
            selected |= in_file
    selected &= functions.keys()
    return reusable(outcomes, 'functionKey', functions, selected), sorted(changed_files), sorted(selected), None


def module_changed(current, old, file):
    return current['moduleSources'].get(file) != old['moduleSources'].get(file)


def changed_keys(current, old):
    return {key for key, sha in current.items() if old.get(key) != sha}


def actionable(outcomes, field):
    return {item[field] for item in outcomes if item['status'] in ACTIONABLE}


def reusable(outcomes, field, present, selected):
    return [{**item, 'reused': True} for item in outcomes if item[field] in present and item[field] not in selected]


def all_outcomes(report, format, report_path):
    reader = adapter(format)
    return [{**validate_detail(describe()), 'status': mutant_status(reader, status), 'reused': False}
            for status, describe in reader.mutants(report, report_path)]


def source_file(file, current):
    """Engines report project-relative, absolute or bare file names; bind only unambiguous ones."""
    files = current['files']
    if file in files:
        return file
    matches = [key for key in files if Path(key).name == Path(str(file)).name]
    return matches[0] if len(matches) == 1 else None


def function_key(item, file, current):
    # Lizard names a method without its class, so bind on the last name segment and the line.
    key = f"{file}:{str(item.get('function')).rpartition('.')[2]}:{item.get('line')}"
    return key if key in current['functions'] else None


def save(evidence, current, outcomes):
    bound = []
    for item in outcomes:
        file = source_file(item.get('file'), current)
        bound.append({**item, 'sourceFile': file, 'functionKey': function_key(item, file, current)})
    encoded = json.dumps(bound).encode()
    manifest = {**current, 'outcomesSha256': digest(encoded)}
    (evidence / OUTCOMES).write_bytes(encoded)
    (evidence / SNAPSHOT).write_bytes(json.dumps({**manifest, 'sha256': digest(canonical(manifest))}).encode())
