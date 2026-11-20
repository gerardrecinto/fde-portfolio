# fde-portfolio

A forward deployed engineer portfolio for infrastructure and developer tooling: two featured projects, case studies, interview answers, and one customer visit you can run.

Site: https://gerardrecinto.github.io/fde-portfolio/

## Run the customer demo

Needs Go 1.21 or newer, Python 3.9 or newer, and curl.

```bash
git clone https://github.com/gerardrecinto/fde-portfolio
cd fde-portfolio
bash demo/run.sh
```

The first run builds the Joltrin barrier server from a pinned commit, which took 24 seconds on a GitHub runner and 76 on my laptop. After that it takes seconds. It ends with `ALL 15 CHECKS PASSED`, or exits 1 and names the check that failed. To use a server you already have, set `SOP_MCP_SERVER=/path/to/sop-mcp-server`.

The demo takes a made-up team that wants an AI agent kept away from production drops through scoping, a runbook built from their step names, a dry run on their traces, an enforced deploy, a restart that breaks a run, and recovery.

## What is real and what is simulated

- Real: the server (Joltrin, MIT, built from the commit in `demo/versions.env`), the checks, and every line of output after the customer input.
- Simulated: the team, its requirements and its agent traces in `demo/customer/`. They are not a customer and not data from any system.
- Not claimed: no paying customer, no usage numbers. The demo runs on one machine, not in a cluster. The pinned commit has observe mode, which is not in a tagged Joltrin release yet.

## Layout

```
demo/run.sh            builds the server and runs the visit
demo/fde_demo.py       the visit and its checks
demo/customer/         simulated requirements, runbooks and traces
site/                  the pages
scripts/build_site.py  puts the saved demo output into the demo page
scripts/check_links.py internal links always, external with --external
```

## Credits and licenses

This repo is MIT. Joltrin is MIT licensed and lives in [SharedCode/joltrin](https://github.com/SharedCode/joltrin). I maintain its verification barrier side. The storage engine underneath was written by Gerardo Recinto, and the contributor list in that repo is the full credit. meshdoctor and fde-field-kit are my own MIT projects.
