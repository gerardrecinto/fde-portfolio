# What the example team asked for (SIMULATED)

This is a made-up team, written to show how I would scope the work. It is not a real
customer and none of the numbers in the demo describe a real system.

The example team runs an AI agent that does Postgres maintenance for their platform group.
From the discovery call:

1. The agent must never drop a production table until a snapshot exists and has been verified.
2. A change must be approved before a drop.
3. The nightly staging restore drill drops a staging table with no snapshot. It must keep working.
4. Rollout must not page anyone. They want to see the effect before anything is blocked.
5. The on-call engineer needs to see what was blocked, and why, without reading agent logs.

Their agent already calls steps with their own names: open_change, approve_change,
snapshot_db, verify_snapshot, drop_table. The runbook uses those names, so their agent
code does not change.
