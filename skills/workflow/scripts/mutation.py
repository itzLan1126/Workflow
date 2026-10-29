#!/usr/bin/env python3
"""Execute a mutation engine and classify its fresh report conservatively."""

import json
import sys
from pathlib import Path
import shutil
from shared_languages import LANGUAGES, language, arguments, evidence_directory, split_tool
from shared_tools import options, python_tools, native_tools
from shared_overlay import isolated
import shared_incremental as incremental
from shared_mutation import STATUSES, ACTIONABLE, assessed_count, exit_code

from shared_runner import read_json, is_valid_config, run_report
from shared_mutation import adapter, assess, render_report, summarize, object_value


def execute_config(path, config, codes):
    if not is_valid_config(config):
        raise ValueError("Require cwd, report, nonempty command argv and positive timeoutMs (max 2147483647)")
    return run_report(path, codes, config=config)


def run_mutation(config_path):
    # Config mode keeps its original last-value-wins handling of duplicate keys.
    config = object_value(read_json(config_path, object_pairs_hook=None))
    format = config.get("format")
    reader = adapter(format)
    run = execute_config(config_path, config, reader.ACCEPTED_EXIT_CODES)
    result = assess(run["report"], format, run["reportPath"])
    if run["exitCode"] != 0 and result["exitCode"] == 0:
        raise ValueError(f"Tool exited {run['exitCode']} without reported findings")
    return {**result, "toolExitCode": run["exitCode"], "reportPath": str(run["reportPath"])}


def language_result(name, args):
    args, install = options(args)
    wrapper, tool = split_tool(args)
    previous = previous_option(wrapper)
    overlay = '--overlay' in wrapper
    if overlay:
        wrapper.remove('--overlay')
    project, sources, timeout, tool = arguments([*wrapper, '--', *tool])
    # Snapshots hash functions with Lizard, so every language needs it alongside its engine.
    names = ['lizard', 'mutmut'] if name == 'python' and not tool else ['lizard']
    with python_tools(names, project, install) as tools, isolated(project, overlay) as copy, \
            native_tools(language(name), 'mutation', copy, install, tool) as native:
        return prepared_result(name, copy, sources, timeout, tool, tools + native, previous)


def prepared_result(name, project, sources, timeout, tool, tools, previous):
    if sources:
        raise ValueError('Mutation check accepts one project path')
    spec = language(name).MUTATION
    evidence = evidence_directory()
    report = Path(spec.report(project, evidence))
    config = {'cwd': str(project), 'report': str(report), 'format': spec.format,
              'command': spec.command(project, evidence, tool), 'timeoutMs': timeout, 'tools': tools}
    identity = [{**record, 'location': stable_location(record['location'], project)} for record in tools]
    engine = {'format': spec.format, 'command': tool or [spec.format], 'tools': identity}
    current = incremental.snapshot(project, language(name), engine)
    return execute_incremental(name, evidence, report, config, current, previous, tool)


def stable_location(location, project):
    path = Path(location)
    if path.is_absolute() and path.is_relative_to(project):
        return path.relative_to(project).as_posix()
    return location


def incremental_plan(name, current, previous, tool):
    if previous is None:
        return [], None, None, None
    plan = incremental.plan(current, previous, name == 'python')
    if plan[1] and tool:
        # A replaced command has no selection protocol; rerun it rather than drop outcomes.
        return [], None, None, 'full run: replaced command cannot be scoped'
    return plan


def execute_incremental(name, evidence, report, config, current, previous, tool):
    reused, files, functions, fallback = incremental_plan(name, current, previous, tool)
    if files:
        config['command'] = language(name).incremental_command(config['command'], files, functions)
    config['selectedFiles'] = files
    path = evidence / 'config.json'
    path.write_bytes(json.dumps(config).encode())
    result, outcomes = run_selected(path, config['format'], report, files, reused)
    incremental.save(evidence, current, outcomes)
    result.update(reusedCount=sum(item['reused'] for item in outcomes), outcomes=outcomes)
    if previous is not None:
        result['incrementalScope'] = {'files': files, 'functions': functions, 'fallback': fallback}
    preserve_report(report, evidence, result)
    (evidence / 'result.json').write_bytes(json.dumps(result).encode())
    return result


def preserve_report(report, evidence, result):
    if not report.resolve().is_relative_to(evidence.resolve()):
        shutil.copy2(report, evidence / report.name)
        result['reportPath'] = str(evidence / report.name)


def run_selected(path, format, report, selected, reused):
    if selected == [] and reused:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_bytes(json.dumps({'baselinePassed': True, 'mutants': reused}).encode())
        return combined_result(reused, format, report), reused
    result = run_mutation(path)
    outcomes = incremental.all_outcomes(read_json(report), format, report)
    if selected is not None:
        outcomes = merge_outcomes(outcomes, reused)
        result = {**result, **combined_result(outcomes, format, report)}
    return result, outcomes


def mutant_identity(item):
    return item.get('file'), item.get('id')


def merge_outcomes(fresh, reused):
    # A freshly executed mutant replaces its earlier outcome instead of being counted twice.
    seen = set(map(mutant_identity, fresh))
    return [*fresh, *(item for item in reused if mutant_identity(item) not in seen)]


def previous_option(wrapper):
    if '--previous-evidence' not in wrapper:
        return None
    index = wrapper.index('--previous-evidence')
    if index + 1 >= len(wrapper):
        raise ValueError('Require --previous-evidence DIRECTORY')
    previous = incremental.load_previous(wrapper[index + 1])
    del wrapper[index:index + 2]
    return previous


def combined_result(outcomes, format, report):
    counts = dict.fromkeys(STATUSES, 0)
    for item in outcomes:
        counts[item['status']] += 1
    assessed = assessed_count(counts)
    return {'format': format, 'counts': counts, 'assessed': assessed,
            'exitCode': exit_code(counts, assessed), 'toolExitCode': 0, 'reportPath': str(report),
            'mutants': [item for item in outcomes if item['status'] in ACTIONABLE]}


def dispatch(args):
    if args and args[0] in LANGUAGES:
        return language_result(args[0], args[1:])
    if len(args) == 1:
        return run_mutation(args[0])
    raise ValueError('Usage: python mutation.py [--json] CONFIG.json')


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        args = list(args)
        boundary = args.index('--') if '--' in args else len(args)
        as_json = '--json' in args[:boundary]
        if as_json:
            args.remove('--json')
        result = dispatch(args)
        print(json.dumps(result) if as_json else render_report(result))
        return result["exitCode"]
    except (OSError, ValueError, ImportError, KeyError, TypeError) as error:
        print(f"mutation: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
