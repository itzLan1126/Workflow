# Python

Run `python crap.py python PROJECT SOURCE...` and `python mutation.py python PROJECT` from the bundled scripts directory. Mutation checks require a fresh isolated copy.

Install coverage.py, pytest, Lizard, and mutmut 3. Coverage runs with branch measurement and subprocess tracking, combines the data, and writes LCOV. Arguments after `--` replace `-m pytest`, for example `-- -m unittest discover -s tests`.

Mutation uses the project's mutmut configuration and exports a normalized report. Only pytest exit 1 counts as killed. A pre-existing `mutants/` directory causes a run failure to prevent stale evidence. Arguments after `--` replace the mutation command; that command must write the normalized report to the absolute path in `WORKFLOW_REPORT_FILE`.

The CRAP and mutation checks accept `--timeout-ms`, defaulting to 3,600,000. Results use exit 0 for pass, 1 for review needed, and 2 for run failure.

## Duplication check

Manually install `tree-sitter==0.25.2` and `tree-sitter-language-pack==0.9.0` in the interpreter that runs the bundled scripts (Python 3.10+), or install the repository's `requirements-dev.txt` for development. Automatic installation is not implemented yet. The language pack bundles the Python grammar; analysis needs no grammar download.

```sh
python duplication.py python PROJECT SOURCE.py OTHER.py
```

Only explicitly selected `.py` files are analysed. Functions and methods are compared; functions nested inside functions are excluded, while methods of nested classes remain candidates. The fixed duplication standard requires at least 4 lines and 20 normalized nodes and reports similarity >= 0.8. Local names, field names, and literals are normalized; call names, operators, and tree shape remain significant. No config mode, threshold/minimum-size flags, tool overrides or timeout overrides are accepted.

The command prints JSON to stdout and a fresh evidence directory to stderr. `config.json` records project, source scope and parser package versions; `measurements.json` preserves function spans, normalized node counts and sorted subtree fingerprints; `result.json` preserves the JSON result with findings, pairs (score, language, both file/line spans), scope and versions. No findings exits 0, findings exit 1, and missing packages, unreadable or unparseable files, and unsupported source types exit 2. This entry point currently supports Python only.

The analyser is a reduced port of [dryer at 66ff6d2](https://github.com/unclebob/dryer/tree/66ff6d2); [provenance and the upstream 0BSD licence](../dryer-LICENSE.txt) are bundled with the skill.
