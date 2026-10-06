"""Own a site's persistent context and guarantee its cleanup."""

from pathlib import Path

from job_agent.core.paths import ProjectPaths
from job_agent.sites.registry import SiteRegistry


CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_local_browser():
    return next((path for path in CHROME_CANDIDATES if Path(path).is_file()), None)


class BrowserSession:
    def __init__(
        self,
        playwright,
        site,
        *,
        headed=True,
        browser_path=None,
        paths=None,
        registry=None,
    ):
        self._playwright = playwright
        self.site = (registry or SiteRegistry()).normalize(site)
        self.paths = paths or ProjectPaths()
        self._headed = headed
        self._browser_path = browser_path
        self._context = None

    async def __aenter__(self):
        if self._context is not None:
            raise RuntimeError("Browser session is already open")
        options = {
            "headless": not self._headed,
            "locale": "ko-KR",
            "viewport": {"width": 1440, "height": 1100},
        }
        executable = self._browser_path or find_local_browser()
        if executable:
            options["executable_path"] = executable
        self._context = await self._playwright.chromium.launch_persistent_context(
            str(self.paths.browser_profile(self.site)), **options
        )
        return self._context

    async def __aexit__(self, exc_type, exc, traceback):
        if self._context is not None:
            await self._context.close()
            self._context = None
