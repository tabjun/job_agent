"""Short-lived anonymous workspaces, never the operator's private files."""

from http.cookies import CookieError, SimpleCookie
import secrets
import threading
import time
from job_agent.ui.service import WorkspaceService


class VisitorWorkspaces:
    cookie_name = "__Host-resume_visitor"

    def __init__(self, ttl=3600, limit=32):
        self.ttl, self.limit = ttl, limit
        self.sessions = {}
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.reaper = threading.Thread(target=self._reap, daemon=True)
        self.reaper.start()

    def _reap(self):
        while not self.stop.wait(60):
            with self.lock:
                self._expire()

    def _expire(self):
        now = time.monotonic()
        for key, (expires, service) in list(self.sessions.items()):
            if expires <= now:
                service.close()
                del self.sessions[key]

    def get(self, cookie):
        try:
            parsed = SimpleCookie(cookie or "")
            token = parsed.get(self.cookie_name)
            with self.lock:
                self._expire()
                entry = self.sessions.get(token.value) if token else None
                return entry[1] if entry else None
        except (CookieError, KeyError, ValueError):
            return None

    def create(self):
        with self.lock:
            self._expire()
            if len(self.sessions) >= self.limit:
                raise ValueError("체험 접속이 많습니다. 잠시 후 다시 접속하세요.")
            service = WorkspaceService(ephemeral=True)
            token = secrets.token_urlsafe(32)
            self.sessions[token] = (time.monotonic() + self.ttl, service)
            return (
                service,
                f"{self.cookie_name}={token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age={self.ttl}",
            )

    def close(self):
        self.stop.set()
        self.reaper.join()
        with self.lock:
            for _, service in self.sessions.values():
                service.close()
            self.sessions.clear()
