# Python

Run `python crap.py python PROJECT SOURCE...` and `python mutation.py python PROJECT` from the bundled scripts directory. Mutation checks require a fresh isolated copy.

Install coverage.py, pytest, Lizard, and mutmut 3. Coverage runs with branch measurement and subprocess tracking, combines the data, and writes LCOV. Arguments after `--` replace `-m pytest`, for example `-- -m unittest discover -s tests`.

Mutation uses the project's mutmut configuration and exports a normalized report. Only pytest exit 1 counts as killed. A pre-existing `mutants/` directory causes a run failure to prevent stale evidence. Arguments after `--` replace the mutation command; that command must write `mutation.json` in the printed evidence directory.

Each check prints the evidence directory to stderr. `--timeout-ms` defaults to 3,600,000. Results use exit 0 for pass, 1 for review needed, and 2 for run failure.
