"""Structural subtree fingerprints and Jaccard gating, ported from dryer 66ff6d2 (0BSD).

See references/dryer-LICENSE.txt for provenance and licence.
"""
import json
from itertools import combinations

MIN_LINES = 4
MIN_NODES = 20
THRESHOLD = 0.8


def fingerprint_tree(tree):
    """Count every normalized node and collect every subtree, including atoms."""
    fingerprints = set()
    printed = {}
    count = 0
    nodes = [tree]
    for node in nodes:
        if isinstance(node, list):
            nodes.extend(node)
    for node in reversed(nodes):
        value = print_node(node, printed)
        printed[id(node)] = value
        fingerprints.add(value)
        count += 1
    return count, fingerprints


def print_node(node, printed):
    if isinstance(node, list):
        return '[' + ' '.join(printed[id(child)] for child in node) + ']'
    return json.dumps(node)


def eligible(entry):
    return (entry['endLine'] - entry['startLine'] + 1 >= MIN_LINES
            and entry['nodes'] >= MIN_NODES)


def same_source(left, right):
    # Extraction visits each file once in source order, so left starts before right.
    return left['file'] == right['file'] and left['endLine'] >= right['endLine']


def pair(left, right):
    if left['language'] != right['language'] or same_source(left, right):
        return None
    union = left['fingerprints'] | right['fingerprints']
    score = len(left['fingerprints'] & right['fingerprints']) / len(union)
    if score < THRESHOLD:
        return None
    return {'language': left['language'], 'score': score,
            'left': span(left), 'right': span(right)}


def span(entry):
    return {key: entry[key] for key in ('file', 'startLine', 'endLine')}


def calculate(entries):
    candidates = filter(eligible, entries)
    pairs = [finding for left, right in combinations(candidates, 2)
             if (finding := pair(left, right)) is not None]
    return {'findings': len(pairs), 'pairs': pairs}
