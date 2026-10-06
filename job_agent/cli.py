"""One entry point; load only the selected workflow's dependencies."""

import argparse
import asyncio
import importlib
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    module: str
    handler: str
    asynchronous: bool = False
    interactive: bool = False


COMMANDS = {
    "target-register": Command("job_agent.sites.registry", "main"),
    "application-prepare": Command("job_agent.sites.application", "main"),
    "source": Command("job_agent.documents.source", "main"),
    "library": Command("job_agent.documents.library", "main"),
    "form-map": Command("job_agent.browser.mapper", "main", True),
    "form-connect": Command("job_agent.browser.connector", "main"),
    "form-fill": Command("job_agent.browser.filler", "main", True),
    "job-search": Command("job_agent.agents.job_hunter", "run_job_hunter", True, True),
    "revise": Command(
        "job_agent.agents.resume_reviser", "run_resume_reviser", True, True
    ),
    "site-package": Command(
        "job_agent.agents.site_resume", "run_site_resume_agent", True, True
    ),
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="job-agent", description="Evidence-backed resume workflows"
    )
    parser.add_argument("command", choices=COMMANDS)
    if not argv or argv[0] in {"-h", "--help"}:
        parser.print_help()
        return
    command = COMMANDS[parser.parse_args(argv[:1]).command]
    remaining = argv[1:]
    if command.interactive:
        argparse.ArgumentParser(
            prog=f"job-agent {argv[0]}",
            description="Interactive workflow; asks for input and model selection.",
        ).parse_args(remaining)
    handler = getattr(importlib.import_module(command.module), command.handler)
    result = handler() if command.interactive else handler(remaining)
    if command.asynchronous:
        asyncio.run(result)
