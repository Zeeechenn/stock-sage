# Deep Research

First inspect project readiness:

```bash
python3 -m backend.agent.cli health --pretty
python3 -m backend.agent.cli actions --pretty
```

Dry-run the deep research action before asking for confirmation:

```bash
python3 -m backend.agent.cli action research.deep.run --payload-json '{"topic":"{{topic}}","symbols":[]}' --pretty
```

After explicit confirmation, execute with `--confirm`. Summarize the report
path, sources, key thesis, risks and follow-up validation questions.
