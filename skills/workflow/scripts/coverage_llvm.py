"""Read llvm-cov export JSON as line and region coverage."""
from itertools import groupby
from pathlib import Path
from shared_runner import read_json


def count(value):
    if type(value) is not int or value < 0:
        raise ValueError('Invalid LLVM coverage count')
    return value


def segment_values(segment):
    if not isinstance(segment, list) or len(segment) < 6:
        raise ValueError('Invalid LLVM coverage segment')
    line, column, hits, has_count, entry, gap = segment[:6]
    if count(line) < 1:
        raise ValueError('Invalid LLVM coverage line')
    if any(type(flag) is not bool for flag in (has_count, entry, gap)):
        raise ValueError('Invalid LLVM coverage segment flag')
    return line, count(hits), has_count, entry, gap


def extend_lines(hits, previous, line, length):
    if previous is None:
        return
    first, previous_count, has_count, entry, gap = previous
    if has_count:
        for covered_line in range(first + 1, min(line, length + 1)):
            hits[covered_line] = previous_count


def mapped_line(segments, previous):
    if any(all((has_count, entry)) for line, hits, has_count, entry, gap in segments):
        return True
    if previous is None or not previous[2]:
        return False
    return segments[0][2] or not segments[0][3]


def execution_count(segments, previous):
    # LLVM maximizes region entries and the wrapped count, not count restorations.
    counts = [hits for line, hits, has_count, entry, gap in segments if has_count and entry and not gap]
    return max([previous[1] if previous else 0, *counts])


def line_hits(segments, length):
    hits, previous = {}, None
    for line, group in groupby(map(segment_values, segments), key=lambda value: value[0]):
        values = list(group)
        extend_lines(hits, previous, line, length)
        if line <= length and mapped_line(values, previous):
            hits[line] = execution_count(values, previous)
        previous = values[-1]
    return hits


def read_files(data, texts, files):
    for file in data['files']:
        source = Path(file['filename']).resolve()
        if source in texts:
            if source in files:
                raise ValueError('Duplicate exact-path LLVM coverage')
            files[source] = {'lines': line_hits(file['segments'], len(texts[source].splitlines())),
                             'branches': {}, 'branchKind': 'region'}


def region_source(function, region):
    start, column, end, end_column, hits, file_id, expanded_id, kind = region[:8]
    if type(file_id) is not int or file_id not in range(len(function['filenames'])):
        raise ValueError('Invalid LLVM region file index')
    if not 1 <= count(start) <= count(end):
        raise ValueError('Invalid LLVM region range')
    return Path(function['filenames'][file_id]).resolve()


def add_regions(function, files, texts):
    for index, region in enumerate(function['regions']):
        start, column, end, end_column, hits, file_id, expanded_id, kind = region[:8]
        source = region_source(function, region)
        if source in files and kind == 0:
            if end > len(texts[source].splitlines()):
                raise ValueError('Invalid LLVM region outside source')
            files[source]['branches'][(start, function['name'], index)] = count(hits)


def read(path, source_text_by_path):
    report = read_json(path)
    if not isinstance(report, dict) or report.get('type') != 'llvm.coverage.json.export':
        raise ValueError('Require llvm-cov export JSON')
    files = {}
    for data in report['data']:
        read_files(data, source_text_by_path, files)
        for function in data['functions']:
            add_regions(function, files, source_text_by_path)
    if not source_text_by_path.keys() <= files.keys():
        raise ValueError('Missing exact-path LLVM coverage')
    return files
