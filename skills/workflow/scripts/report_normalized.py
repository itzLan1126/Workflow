"""Read normalized mutation reports."""
from functools import partial
from shared_mutation import object_value, array, safe_detail, code_diff, function_at

from shared_mutation import STATUSES as NORMALIZED_STATUSES
ACCEPTED_EXIT_CODES = (0,)
STATUSES = {status: status for status in NORMALIZED_STATUSES}

def mutants(report, report_path):
    if report.get("baselinePassed") is not True:
        raise ValueError("Normalized report must confirm baselinePassed: true")
    for mutant in array(report.get("mutants")):
        yield object_value(mutant).get("status"), lambda mutant=mutant: mutant
