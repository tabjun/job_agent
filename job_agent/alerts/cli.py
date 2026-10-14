"""Run registered job alerts from a scheduler (Task Scheduler/cron) or by hand."""

import argparse
import json


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="job-agent alerts",
        description="Verified-email job alerts kept in result/job_alerts/ on this PC",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="Show registered alerts and next run times")
    run = commands.add_parser("run", help="Search and mail new postings")
    target = run.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--due", action="store_true", help="Only alerts whose time has come"
    )
    target.add_argument("--id", help="Run one alert now")
    run.add_argument(
        "--preview", action="store_true", help="With --id: search only, do not mail"
    )
    args = parser.parse_args(argv)

    from job_agent.alerts.service import JobAlerts
    from job_agent.core.paths import ProjectPaths, load_environment

    paths = ProjectPaths()
    load_environment(paths)
    alerts = JobAlerts(paths)
    if args.command == "list":
        result = alerts.status()
    elif args.due:
        result = [
            {k: v for k, v in row.items() if k != "jobs"} for row in alerts.run_due()
        ]
    else:
        result = alerts.run_now({"id": args.id, "send": not args.preview})
    print(json.dumps(result, ensure_ascii=False, indent=2))
