"""Read llvm-cov export JSON as line and region coverage."""
from pathlib import Path
from shared_runner import read_json


def line_hits(segments, length):
    hits = {}
    previous = None
    for segment in segments:
        if not isinstance(segment, list) or len(segment) < 6:
            raise ValueError('Invalid LLVM coverage segment')
        line, column, count, has_count, entry, gap = segment[:6]
        if type(line) is not int or type(count) is not int or line < 1 or count < 0:
            raise ValueError('Invalid LLVM coverage counts')
        if previous is not None:
            first, previous_count, active = previous
            if active:
                for covered_line in range(first, min(line, length + 1)):
                    hits[covered_line] = max(hits.get(covered_line, 0), previous_count)
        if has_count and not gap and line <= length:
            hits[line] = max(hits.get(line, 0), count)
        previous = line, count, has_count and not gap
    return hits


def read(path, source_text_by_path):
    report = read_json(path)
    if report.get('type') != 'llvm.coverage.json.export':
        raise ValueError('Require llvm-cov export JSON')
    files = {}
    for data in report['data']:
        for file in data['files']:
            source = Path(file['filename']).resolve()
            if source in source_text_by_path:
                files[source] = {'lines': line_hits(file['segments'], len(source_text_by_path[source].splitlines())),
                                 'branches': {}, 'branchKind': 'region'}
        for function in data['functions']:
            for index, region in enumerate(function['regions']):
                start, column, end, end_column, count, file_id, expanded_id, kind = region[:8]
                source = Path(function['filenames'][file_id]).resolve()
                if source in files and kind == 0:
                    if type(count) is not int or count < 0:
                        raise ValueError('Invalid LLVM region count')
                    files[source]['branches'][(start, function['name'], index)] = count
    if any(source not in files for source in source_text_by_path):
        raise ValueError('Missing exact-path LLVM coverage')
    return files
