"""Read llvm-cov export JSON as line and region coverage."""
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
    return line, count(hits), has_count and not gap


def extend_lines(hits, previous, line, length):
    if previous is None:
        return
    first, previous_count, active = previous
    if active:
        for covered_line in range(first, min(line, length + 1)):
            hits[covered_line] = max(hits.get(covered_line, 0), previous_count)


def line_hits(segments, length):
    hits, previous = {}, None
    for segment in segments:
        line, hits_count, active = segment_values(segment)
        extend_lines(hits, previous, line, length)
        if active and line <= length:
            hits[line] = max(hits.get(line, 0), hits_count)
        previous = line, hits_count, active
    return hits


def read_files(data, texts):
    files = {}
    for file in data['files']:
        source = Path(file['filename']).resolve()
        if source in texts:
            files[source] = {'lines': line_hits(file['segments'], len(texts[source].splitlines())),
                             'branches': {}, 'branchKind': 'region'}
    return files


def add_regions(function, files):
    for index, region in enumerate(function['regions']):
        start, column, end, end_column, hits, file_id, expanded_id, kind = region[:8]
        source = Path(function['filenames'][file_id]).resolve()
        if source in files and kind == 0:
            files[source]['branches'][(start, function['name'], index)] = count(hits)


def read(path, source_text_by_path):
    report = read_json(path)
    if report.get('type') != 'llvm.coverage.json.export':
        raise ValueError('Require llvm-cov export JSON')
    files = {}
    for data in report['data']:
        files.update(read_files(data, source_text_by_path))
        for function in data['functions']:
            add_regions(function, files)
    if not source_text_by_path.keys() <= files.keys():
        raise ValueError('Missing exact-path LLVM coverage')
    return files
