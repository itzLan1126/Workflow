"""Iterative syntax normalization and extraction mechanics (dryer 66ff6d2, 0BSD)."""
from collections import namedtuple

from shared_runner import read_utf8
from shared_duplication import fingerprint_tree

# Node-type names a language module supplies; the walker itself stays language-independent.
Syntax = namedtuple('Syntax', 'identifiers literals calls attributes paths')

# Punctuation is ignored; named syntax and operator spellings preserve structure.
OPERATORS = {'+', '-', '*', '/', '%', '**', '==', '!=', '<', '>', '<=', '>=', '===', '!==',
             '&&', '||', '&', '|', '^', '<<', '>>', '>>>', '+=', '-=', '*=', '/=', '%=',
             '&=', '|=', '^=', '<<=', '>>=', '>>>=', '!', '~', '++', '--', '??', '?.', '=', '=>', '?'}
COMMENTS = {'comment', 'line_comment', 'block_comment', 'doc_comment'}
SYMBOL, LITERAL = ':symbol', ':literal'


def inside(node, types):
    parent = node.parent
    while parent is not None:
        if parent.type in types:
            return True
        parent = parent.parent
    return False


def normalize(root, syntax):
    # Two passes, like the Python normalizer: deep trees cannot overflow the stack.
    cache, pending, stack = {}, [], [(root, False)]
    while stack:
        node, head = stack.pop()
        value = leaf(node, head, syntax)
        if value is None:
            children = jobs(node, head, syntax)
            pending.append((node, head, children))
            stack.extend(children)
        else:
            cache[(node.id, head)] = value
    for node, head, children in reversed(pending):
        cache[(node.id, head)] = [':' + node.type, *(cache[(c.id, h)] for c, h in children)]
    return cache[(root.id, False)]


def leaf(node, head, syntax):
    if node.type in syntax.identifiers:
        return [SYMBOL, node.text.decode()] if head else SYMBOL
    if node.type in syntax.literals:
        return LITERAL
    if node.type in OPERATORS:
        return [SYMBOL, node.type]
    return None


def jobs(node, head, syntax):
    children = [c for c in node.children if keep_child(c)]
    return [(child, child_head(node, child, children, head, syntax)) for child in children]


def child_head(node, child, children, head, syntax):
    """Whether a child names the thing being called, so its spelling is kept."""
    if node.type in syntax.calls:
        return child == (node.child_by_field_name('function') or node.child_by_field_name('constructor'))
    if node.type in syntax.attributes:
        return head and child == children[-1]
    return head and node.type in syntax.paths


def keep_child(child):
    return child.type not in COMMENTS and (child.is_named or child.type in OPERATORS)


def entries(path, file, grammar, language, candidate, syntax):
    from tree_sitter_language_pack import get_parser
    tree = get_parser(grammar).parse(read_utf8(path).encode())
    if tree.root_node.has_error:
        raise ValueError(f'Unparseable {language} source: {path}')
    result, stack = [], [tree.root_node]
    while stack:
        node = stack.pop()
        stack.extend(reversed(node.children))
        if candidate(node):
            count, fingerprints = fingerprint_tree(normalize(node, syntax))
            result.append({'language': language, 'file': file, 'startLine': node.start_point.row + 1,
                           'endLine': node.end_point.row + bool(node.end_point.column),
                           'nodes': count, 'fingerprints': fingerprints})
    return result
