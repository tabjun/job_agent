"""Own a temporary tunnel and revocable, bounded remote sessions."""

from http.cookies import SimpleCookie
import os
import re
import secrets
import shutil
import subprocess
import threading
import time


class Sharing:
    def __init__(self, port):
        self.port = port
        self.process = None
        self.url = ""
        self.code = ""
        self.error = ""
        self.sessions = {}
        self.attempts = []
        self.lock = threading.RLock()

    @staticmethod
    def binary():
        path = os.getenv("CLOUDFLARED_PATH") or shutil.which("cloudflared")
        return path if path and os.path.isfile(path) else None

    def status(self, private=False):
        with self.lock:
            running = self.process is not None and self.process.poll() is None
            result = {
                "state": "active"
                if running and self.url
                else "starting"
                if running
                else "stopped",
                "url": self.url if running else "",
                "error": self.error,
            }
            if private:
                result["access_code"] = self.code if running else ""
                result["installed"] = bool(self.binary())
            return result

    def start(self, consent=False):
        if consent is not True:
            raise ValueError(
                "인증한 방문자에게 전체 작업 공간 접근을 허용하는 데 동의하세요."
            )
        with self.lock:
            if self.status()["state"] != "stopped":
                return self.status(True)
            binary = self.binary()
            if not binary:
                raise ValueError(
                    "cloudflared를 먼저 설치하세요. README의 설치 명령을 확인하세요."
                )
            self.code = secrets.token_urlsafe(24)
            self.sessions.clear()
            self.attempts.clear()
            self.url, self.error = "", ""
            self.process = subprocess.Popen(
                [
                    binary,
                    "--no-autoupdate",
                    "tunnel",
                    "--url",
                    f"http://127.0.0.1:{self.port}",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            threading.Thread(
                target=self._watch, args=(self.process,), daemon=True
            ).start()
            return self.status(True)

    def _watch(self, process):
        started = time.monotonic()
        # Drain output continuously; do not persist cloudflared diagnostics or secrets.
        for line in process.stdout:
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com\b", line)
            with self.lock:
                if self.process is not process:
                    break
                if match:
                    self.url = match.group(0)
                if not self.url and time.monotonic() - started > 60:
                    self.error = "공유 주소 생성이 지연되고 있습니다. 네트워크와 cloudflared 설정을 확인하세요."
        with self.lock:
            if self.process is process and process.poll() is not None:
                self.sessions.clear()
                self.error = "터널이 종료되었습니다. 네트워크·cloudflared 설정을 확인하고 다시 생성하세요."

    def stop(self):
        with self.lock:
            process, self.process = self.process, None
            self.url, self.code, self.error = "", "", ""
            self.sessions.clear()
        if process:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        return self.status(True)

    def login(self, code):
        with self.lock:
            now = time.monotonic()
            self.attempts = [stamp for stamp in self.attempts if now - stamp < 60]
            if len(self.attempts) >= 20:
                raise ValueError("잠시 후 다시 시도하세요.")
            self.attempts.append(now)
            if (
                self.status()["state"] != "active"
                or not isinstance(code, str)
                or not secrets.compare_digest(code, self.code)
            ):
                raise ValueError("접근 코드가 올바르지 않습니다.")
            self.sessions = {
                key: expiry for key, expiry in self.sessions.items() if expiry > now
            }
            if len(self.sessions) >= 32:
                self.sessions.pop(next(iter(self.sessions)))
            session = secrets.token_urlsafe(32)
            self.sessions[session] = now + 8 * 3600
            return session

    def authenticated(self, cookie):
        try:
            parsed = SimpleCookie(cookie or "")
            session = parsed.get("__Host-resume_session")
            with self.lock:
                return bool(
                    session
                    and self.sessions.get(session.value, 0) > time.monotonic()
                    and self.status()["state"] == "active"
                )
        except Exception:
            return False
