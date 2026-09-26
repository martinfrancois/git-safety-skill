# Contributing

Issues and pull requests are welcome, especially new situations where an agent does something to a
repository that its user would not have approved.

- For a change to the skill's wording, run the live suite on both agents as described in
  [`AGENTS.md`](AGENTS.md) and include both summaries in the pull request.
- For a new situation, include its safe and unsafe scripted agents and a few runs with
  `--condition none`, which show whether agents get it wrong without the skill.
- Keep the self-test green: `python3 -m unittest discover -s evals/tests`.
