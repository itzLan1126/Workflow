"""Read cargo-mutants outcomes with a verified baseline."""
from functools import partial
from shared_mutation import object_value, array, safe_detail, code_diff, function_at

ACCEPTED_EXIT_CODES = (0, 2, 3)
STATUSES = {'CaughtMutant': 'killed', 'MissedMutant': 'survived', 'Timeout': 'timeout', 'Unviable': 'unviable'}

def has_test(outcome):
    return any(object_value(phase).get("phase") == "Test"
               for phase in array(outcome.get("phase_results")))


def is_successful_baseline(outcome):
    return outcome.get("summary") == "Success" and has_test(outcome)


def check_cargo_baseline(outcomes):
    baselines = [o for o in outcomes if o.get("scenario") == "Baseline"]
    if not baselines or not all(map(is_successful_baseline, baselines)):
        raise ValueError("cargo-mutants requires a successful baseline test (do not use --check or --baseline skip)")


def cargo_mutant(outcome):
    object_value(object_value(outcome.get("scenario")).get("Mutant"))
    summary = outcome.get("summary")
    if summary in ("CaughtMutant", "MissedMutant") and not has_test(outcome):
        raise ValueError("Missing mutation test phase")
    return summary


def cargo_detail(outcome, report_path):
    mutant = outcome["scenario"]["Mutant"]
    function = mutant.get("function") or {}
    span = function.get("span", mutant.get("span", {}))
    detail = {"function": function.get("function_name"), "line": span.get("start", {}).get("line")}
    diff_path = outcome.get("diff_path")
    if diff_path:
        detail.update(read_cargo_diff(report_path, diff_path))
    return detail


def read_cargo_diff(report_path, diff_path):
    path = (report_path.parent / diff_path).resolve()
    if not path.is_relative_to(report_path.parent.resolve()):
        raise ValueError("Cargo diff path must stay inside the report directory")
    detail = {"evidence": str(path)}
    try:
        detail["diff"] = path.read_text(encoding="utf-8")
    except OSError as error:
        detail["detailGap"] = f"Cannot read diff: {error}"
    return detail


def describe(outcome, report_path):
    mutant = outcome["scenario"]["Mutant"]
    return {"id": mutant.get("name"), "file": mutant.get("file"),
            **safe_detail(cargo_detail, outcome, report_path)}


def mutants(report, report_path):
    outcomes = [object_value(o) for o in array(report.get("outcomes"))]
    check_cargo_baseline(outcomes)
    count = 0
    for outcome in outcomes:
        if outcome.get("scenario") != "Baseline":
            count += 1
            yield cargo_mutant(outcome), partial(describe, outcome, report_path)
    if type(report.get("total_mutants")) is not int or report["total_mutants"] != count:
        raise ValueError("Inconsistent cargo-mutants count")
