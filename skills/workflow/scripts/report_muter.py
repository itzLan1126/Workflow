"""Read Muter mutation reports."""
from functools import partial
from shared_mutation import object_value, array, safe_detail, code_diff, function_at

ACCEPTED_EXIT_CODES = (0,)
STATUSES = {'failed': 'killed', 'passed': 'survived', 'noCoverage': 'noCoverage', 'timeout': 'timeout', 'buildError': 'unviable', 'runtimeError': 'error'}

def muter_detail(mutant):
    point = mutant.get("mutationPoint") or {}
    line = point.get("position", {}).get("line")
    detail = {"id": point.get("mutationOperatorId"), "line": line}
    snapshot = mutant.get("mutationSnapshot") or {}
    before, after = snapshot.get("before"), snapshot.get("after")
    if isinstance(before, str) and isinstance(after, str) and line:
        detail.update(diff=code_diff(before, after), diffOffset=line - 1,
                      detailGap="Muter provides a code snippet; function name is unavailable")
    return detail


def describe(file, mutant):
    return {**safe_detail(muter_detail, mutant), "file": file}


def mutants(report, report_path):
    for file in array(report.get("fileReports")):
        for mutant in array(object_value(file).get("appliedOperators")):
            yield object_value(mutant).get("testSuiteOutcome"), partial(describe, file.get("fileName"), mutant)
