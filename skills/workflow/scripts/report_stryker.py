"""Read Stryker reports and UTF-16 source locations."""
import codecs
from functools import partial
from shared_mutation import object_value, array, safe_detail, code_diff, function_at

ACCEPTED_EXIT_CODES = (0,)
STATUSES = {'Killed': 'killed', 'Survived': 'survived', 'NoCoverage': 'noCoverage', 'Timeout': 'timeout', 'CompileError': 'unviable', 'Ignored': 'ignored', 'RuntimeError': 'error', 'Pending': 'error'}

def valid_utf16_column(encoded_byte_length, column):
    return 1 <= column <= encoded_byte_length // 2 + 1


def valid_position(lines, line, column):
    return (1 <= line <= len(lines)
            and valid_utf16_column(len(codecs.utf_16_le_encode(lines[line - 1].rstrip("\r\n"))[0]), column))


def source_offset(source, position):
    lines = source.splitlines(keepends=True)
    line, column = position["line"], position["column"]
    if type(line) is not int or type(column) is not int:
        raise ValueError("Invalid Stryker source position")
    if position == {"line": len(lines) + 1, "column": 1} and source.endswith("\n"):
        return len(source)
    if not valid_position(lines, line, column):
        raise ValueError("Invalid Stryker source position")
    # Stryker columns count UTF-16 code units, including two units for astral characters.
    prefix = codecs.utf_16_le_decode(codecs.utf_16_le_encode(lines[line - 1])[0][:(column - 1) * 2], None, True)[0]
    return sum(map(len, lines[:line - 1])) + len(prefix)


def stryker_detail(file, source, mutant):
    detail = {**mutant}
    location = mutant.get("location")
    if not isinstance(source, str) or not isinstance(location, dict):
        return detail
    start, end = source_offset(source, location["start"]), source_offset(source, location["end"])
    if end < start:
        raise ValueError("Invalid Stryker source range")
    line = location["start"]["line"]
    detail.update({"line": line, **function_at(file, source, line)})
    replacement = mutant.get("replacement")
    if isinstance(replacement, str):
        detail["diff"] = code_diff(source, source[:start] + replacement + source[end:])
    return detail


def describe(file, data, mutant):
    return {**safe_detail(stryker_detail, file, data.get("source"), mutant),
            "id": mutant.get("id"), "file": file}


def mutants(report, report_path):
    for file, data in object_value(report.get("files")).items():
        for mutant in array(object_value(data).get("mutants")):
            yield object_value(mutant).get("status"), partial(describe, file, data, mutant)
