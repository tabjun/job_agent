"""Site configuration shared without importing browser or LLM dependencies."""

import argparse
from copy import deepcopy
import json
import re
from urllib.parse import urlparse

from job_agent.core.paths import ProjectPaths
from job_agent.core.storage import ArtifactStore


SITE_TARGETS = {
    "saramin": {
        "name": "Saramin",
        "aliases": ["saramin", "사람인"],
        "candidate_urls": ["https://www.saramin.co.kr/zf_user/resume/resume-manage"],
    },
    "wanted": {
        "name": "Wanted",
        "aliases": ["wanted", "원티드"],
        "candidate_urls": ["https://www.wanted.co.kr/cv/list"],
    },
    "jobplanet": {
        "name": "JobPlanet",
        "aliases": ["jobplanet", "잡플래닛"],
        "candidate_urls": [
            "https://www.jobplanet.co.kr/user-session/sign-in",
            "https://www.jobplanet.co.kr/profile/resume",
            "https://www.jobplanet.co.kr/users/resume",
        ],
    },
    "catch": {
        "name": "Catch",
        "aliases": ["catch", "캐치"],
        "candidate_urls": ["https://www.catch.co.kr/Member/ResumeList"],
    },
    "jobkorea": {
        "name": "JobKorea",
        "aliases": ["jobkorea", "잡코리아"],
        "candidate_urls": ["https://www.jobkorea.co.kr/User/ResumeMng"],
    },
    "incruit": {
        "name": "Incruit",
        "aliases": ["incruit", "인크루트"],
        "candidate_urls": ["https://www.incruit.com/"],
    },
    "linkedin": {
        "name": "LinkedIn",
        "aliases": ["linkedin", "링크드인"],
        "candidate_urls": [
            "https://www.linkedin.com/in/",
            "https://www.linkedin.com/feed/",
            "https://www.linkedin.com/profile/edit/forms/position/new/",
        ],
    },
}


def default_sites():
    return ["catch", "jobkorea", "saramin", "wanted", "incruit"]


def normalize_site(site):
    needle = site.strip().lower()
    for key, target in SITE_TARGETS.items():
        if needle == key or needle in [alias.lower() for alias in target["aliases"]]:
            return key
    raise ValueError(f"Unknown site: {site}. Known: {', '.join(SITE_TARGETS)}")


def site_matches_url(site, url):
    host = (urlparse(url).hostname or "").lower()
    domain = (
        urlparse(SITE_TARGETS[site]["candidate_urls"][0]).hostname or ""
    ).removeprefix("www.")
    return host == domain or host.endswith("." + domain)


def web_origin(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Target must be an HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("Credentials must not appear in target URLs")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return parsed.scheme, parsed.hostname.lower(), port


class SiteRegistry:
    """Own one optional company target without changing built-in global targets."""

    def __init__(self, custom=None):
        self._custom = deepcopy(custom)
        if custom is not None:
            key = custom.get("key", "")
            if not re.fullmatch(r"company-[a-z0-9][a-z0-9_-]{0,60}", key):
                raise ValueError(
                    "Custom key must start with company- and use a safe slug"
                )
            if not isinstance(custom.get("name"), str) or not custom["name"].strip():
                raise ValueError("Company name is required")
            urls = custom.get("candidate_urls")
            if not isinstance(urls, list) or len(urls) != 1:
                raise ValueError("Exactly one start URL is required")
            self._origins = {
                web_origin(url) for url in custom.get("allowed_origins", [])
            }
            if web_origin(urls[0]) not in self._origins:
                raise ValueError("Start URL must be explicitly allowed")

    @classmethod
    def from_file(cls, path):
        if not path:
            return cls()
        return cls(json.loads(ProjectPaths().resolve(path).read_text(encoding="utf-8")))

    def normalize(self, site):
        if self._custom and site.strip().lower() == self._custom["key"]:
            return self._custom["key"]
        return normalize_site(site)

    @property
    def custom_key(self):
        return self._custom["key"] if self._custom else None

    def target(self, site):
        key = self.normalize(site)
        return deepcopy(self._custom if self.is_custom(key) else SITE_TARGETS[key])

    def is_custom(self, site):
        return bool(self._custom and site == self._custom["key"])

    def matches_url(self, site, url):
        key = self.normalize(site)
        if not self.is_custom(key):
            return site_matches_url(key, url)
        try:
            return web_origin(url) in self._origins
        except ValueError:
            return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="Register a company application URL")
    parser.add_argument("--key", required=True, help="company-example")
    parser.add_argument("--name", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--allow-origin", action="append", default=[])
    parser.add_argument("--output-dir", default="result/company_targets")
    args = parser.parse_args(argv)
    custom = {
        "key": args.key,
        "name": args.name,
        "candidate_urls": [args.url],
        "allowed_origins": [args.url, *args.allow_origin],
    }
    registry = SiteRegistry(custom)
    store = ArtifactStore(ProjectPaths().resolve(args.output_dir))
    path = store.write_json(f"{args.key}.json", registry.target(args.key))
    print(f"Company target saved: {path}")
