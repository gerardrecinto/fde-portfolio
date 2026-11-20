"""One customer visit, end to end, against the real Joltrin barrier server.

Labels: [SIMULATED] is made-up customer input. [MEASURED] is output from the real
server or a number counted from its decision log and metrics.
Exits 1 if any check fails.
"""
import json, os, secrets, signal, socket, subprocess, sys, tempfile, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = sys.argv[1]
CUST = os.path.join(HERE, "customer")
checks = []


def say(s=""):
    print(s, flush=True)


def head(s):
    say(f"\n== {s}")


def check(ok, what):
    checks.append(ok)
    say(f"  {'PASS' if ok else 'FAIL'}  {what}")
    if not ok:
        say(f"\n{checks.count(False)} check(s) failed")
        sys.exit(1)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Barrier:
    """The real sop-mcp-server in HTTP mode, as one team would run it."""

    def __init__(self, runbook, mode, token, logfile):
        self.port, self.mport = free_port(), free_port()
        env = dict(os.environ, SOP_RUNBOOKS=os.path.join(CUST, runbook), SOP_MCP_TOKEN=token,
                   SOP_DECISION_LOG=logfile, SOP_METRICS_ADDR=f"127.0.0.1:{self.mport}")
        env.pop("SOP_MODE", None)
        if mode == "observe":
            env["SOP_MODE"] = "observe"
        self.token, self.log = token, logfile
        self.proc = subprocess.Popen([BIN, "http", "--addr", f"127.0.0.1:{self.port}"], env=env,
                                     stdout=subprocess.DEVNULL, stderr=open(logfile + ".err", "w"))
        for _ in range(100):
            try:
                if urllib.request.urlopen(f"http://127.0.0.1:{self.port}/healthz", timeout=1).status == 200:
                    return
            except OSError:
                time.sleep(0.1)
        self.stop()
        raise SystemExit("server did not become healthy")

    def stop(self):
        self.proc.send_signal(signal.SIGTERM)
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def rpc(self, method, params, token="default"):
        tok = self.token if token == "default" else token
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if tok:
            h["Authorization"] = f"Bearer {tok}"
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/mcp", body, h)
        return json.loads(urllib.request.urlopen(req, timeout=10).read())

    def step(self, workflow, trace, step):
        r = self.rpc("tools/call", {"name": "execute_step",
                                    "arguments": {"workflow": workflow, "trace_id": trace, "step": step}})
        return r["result"]["structuredContent"]

    def metrics(self):
        return urllib.request.urlopen(f"http://127.0.0.1:{self.mport}/metrics").read().decode()

    def decisions(self):
        with open(self.log) as f:
            return [json.loads(l) for l in f if l.strip()]


def replay(b, traces, route):
    """Send each trace's steps to the barrier. route(kind) picks the workflow name."""
    ran = would = 0
    flagged = []
    for t in traces:
        for s in t["steps"]:
            r = b.step(route(t["kind"]), t["trace"], s)
            ran += 1
            wb = r.get("would_have_blocked")
            if wb:
                would += 1
                flagged.append((t["trace"], s, wb["missing_state"]))
    return ran, would, flagged


def run(*args):
    p = subprocess.run([BIN, *args], capture_output=True, text=True, cwd=CUST)
    return p.returncode, (p.stdout + p.stderr).strip()


def main():
    tmp = tempfile.mkdtemp(prefix="fde-demo-")
    traces = json.load(open(os.path.join(CUST, "traces.json")))["traces"]
    tok = secrets.token_hex(16)
    rc, ver = run("version")
    say(f"[MEASURED] server: {ver}")

    head("1. Discovery [SIMULATED customer, see demo/customer/requirements.md]")
    say(open(os.path.join(CUST, "requirements.md")).read().split("\n\n", 2)[2].strip())

    head("2. Integration: load the customer's step names into a runbook [MEASURED]")
    rc, out = run("check", "runbook-typo.json")
    say("  first draft, one state name misspelled (snapshot_verifed):")
    say("    " + out.replace("\n", "\n    "))
    check(rc != 0 and "snapshot_verified" in out, "the server refuses a runbook where a step can never run")
    rc, out = run("check", "runbook-v1.json")
    say("  fixed draft:")
    say("    " + out.replace("\n", "\n    "))
    check(rc == 0, "runbook-v1.json loads")

    head("3. Observe mode: replay a week of agent traces, block nothing [MEASURED on SIMULATED traces]")
    b = Barrier("runbook-v1.json", "observe", tok, os.path.join(tmp, "observe.jsonl"))
    ran, would, flagged = replay(b, traces, lambda kind: "db-maintenance")
    say(f"  {len(traces)} traces, {ran} steps sent, {would} would have been blocked:")
    for tr, st, ms in flagged:
        say(f"    {tr}  {st}  missing {ms}")
    drills = [f for f in flagged if f[0].startswith("drill")]
    check(would == 6 and len(drills) == 3, "6 would-be blocks: 3 real (prod-09, prod-10, prod-11) and 3 false positives from the staging drill")
    check(all(d["outcome"] in ("allowed", "observed") for d in b.decisions()), "observe mode blocked nothing")
    b.stop()

    head("4. Fix the false positive without touching the customer's agent logic [MEASURED]")
    say("  Staging drill agent now sends workflow=staging-drill (one config line on their side). runbook-v2.json defines it.")
    rc, out = run("check", "runbook-v2.json")
    check(rc == 0, "runbook-v2.json loads")
    b = Barrier("runbook-v2.json", "observe", tok, os.path.join(tmp, "observe2.jsonl"))
    ran, would, flagged = replay(b, traces, lambda kind: "staging-drill" if kind == "staging" else "db-maintenance")
    say(f"  {ran} steps sent, {would} would have been blocked:")
    for tr, st, ms in flagged:
        say(f"    {tr}  {st}  missing {ms}")
    check(would == 3 and not any(f[0].startswith("drill") for f in flagged), "3 would-be blocks left, all real, no staging false positives")
    b.stop()

    head("5. Deploy in enforce mode, with a token, metrics and a decision log [MEASURED]")
    b = Barrier("runbook-v2.json", "enforce", tok, os.path.join(tmp, "enforce.jsonl"))
    say(f"  healthz: 200   metrics: 127.0.0.1:<port>/metrics   decision log: {os.path.basename(b.log)}")
    try:
        b.rpc("tools/list", {}, token="wrong-token")
        denied = False
    except urllib.error.HTTPError as e:
        denied = e.code == 401
    check(denied, "a call with the wrong token gets 401")
    r = b.step("db-maintenance", "run-1", "drop_table")
    say("  agent tries drop_table first:")
    bl = r.get("blocked", {})
    say("    " + json.dumps({"executed": r.get("executed"), **{k: bl.get(k) for k in ("missing_state", "established_by_steps", "next")}}))
    check(r.get("executed") is False and bl.get("missing_state") == "snapshot_verified" and bl.get("next") == "run_established_by_steps", "drop_table is blocked and the reason names the missing state and what to run first")
    for s in ("open_change", "approve_change", "snapshot_db", "verify_snapshot", "drop_table"):
        r = b.step("db-maintenance", "run-1", s)
        say(f"    {s:16} executed={r.get('executed')}")
    check(r.get("executed") is True, "after the steps the hints named, drop_table runs")

    head("6. Verify success from outside the agent [MEASURED]")
    d = b.decisions()
    outcomes = {}
    for x in d:
        outcomes[x["outcome"]] = outcomes.get(x["outcome"], 0) + 1
    say(f"  decision log: {outcomes}")
    m = [l for l in b.metrics().splitlines() if l.startswith("joltrin_steps_total")]
    for l in m:
        say("  " + l)
    check(outcomes.get("blocked") == 1 and outcomes.get("allowed") == 5, "log shows 1 blocked and 5 allowed")
    check(any('outcome="blocked"' in l and l.endswith(" 1") for l in m), "the metrics counter agrees with the log")

    head("7. Failure: the barrier restarts in the middle of a run [MEASURED]")
    for s in ("open_change", "approve_change", "snapshot_db", "verify_snapshot"):
        b.step("db-maintenance", "run-2", s)
    say("  run-2 has recorded four steps. The server restarts, which is what a pod restart does too: trace state is in memory.")
    b.stop()
    b = Barrier("runbook-v2.json", "enforce", tok, os.path.join(tmp, "enforce-after-restart.jsonl"))
    r = b.step("db-maintenance", "run-2", "drop_table")
    say("    drop_table  -> " + json.dumps({"executed": r.get("executed"), "missing_state": r.get("blocked", {}).get("missing_state")}))
    check(r.get("executed") is False, "after the restart the drop is blocked, the barrier forgot the trace and got stricter, never looser")

    head("8. Recovery: replay what the hints name, then roll back to observe if needed [MEASURED]")
    for s in ("open_change", "approve_change", "snapshot_db", "verify_snapshot", "drop_table"):
        r = b.step("db-maintenance", "run-2", s)
    check(r.get("executed") is True, "the agent re-established its state and the drop ran")
    say("  Rollback of enforcement itself: restart with SOP_MODE=observe, which stops blocking and keeps logging.")
    b.stop()
    b = Barrier("runbook-v2.json", "observe", tok, os.path.join(tmp, "rollback.jsonl"))
    r = b.step("db-maintenance", "run-3", "drop_table")
    check(r.get("executed") is True and "would_have_blocked" in r, "in observe mode the same drop runs and is logged as would-have-blocked")
    check(b.decisions()[-1]["outcome"] == "observed", "the decision log records it as observed, so the rollback is visible")
    b.stop()

    say(f"\nALL {len(checks)} CHECKS PASSED")


main()
