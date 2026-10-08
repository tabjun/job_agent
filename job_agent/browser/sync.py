"""Review, apply, save and verify a bounded set of existing resume fields."""

import asyncio
import hashlib
import json
import secrets
import threading
from uuid import uuid4
from urllib.parse import urlsplit

from job_agent.browser.connector import candidate_fields
from job_agent.browser.filler import FormFiller
from job_agent.browser.mapper import capture_page
from job_agent.browser.session import BrowserSession
from job_agent.browser.suggestions import propose_mappings
from job_agent.core.storage import ArtifactStore
from job_agent.documents.profile import ResumeProfile
from job_agent.sites.registry import SiteRegistry, default_sites


SAVE_LABELS = {
    "저장",
    "저장하기",
    "이력서저장",
    "이력서 저장",
    "이 부분만 저장",
    "모두 저장",
}


def resume_editor(site, url):
    path = urlsplit(url).path.lower()
    if any(
        token in path
        for token in ["login", "signin", "apply", "manage", "list", "resumemng"]
    ):
        return False
    prefixes = {
        "catch": "/member/resume/",
        "jobkorea": "/user/resume/edit",
        "saramin": "/zf_user/resume/",
        "wanted": "/cv/",
        "incruit": "/resume/resume.asp",
    }
    if site in {"catch", "wanted"}:
        return path.startswith(prefixes[site]) and path != prefixes[site]
    return path.startswith(prefixes[site])


def digest(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


async def save_controls(page):
    rows = await page.locator(
        'button, input[type="button"], input[type="submit"], [role="button"], a'
    ).evaluate_all(
        """els => els.map(el => {
          const parts = []; let node = el;
          while (node && node.localName !== 'html') {
            const siblings = Array.from(node.parentElement?.children || []).filter(x => x.localName === node.localName);
            parts.unshift(node.localName + ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')'); node = node.parentElement;
          }
          return {selector: parts.join(' > '), label: (el.innerText || el.value || '').trim().replace(/\\s+/g, ' '),
                  visible: !!(el.getClientRects().length), disabled: !!el.disabled};
        })"""
    )
    return [
        row
        for row in rows
        if row["label"] in SAVE_LABELS and row["visible"] and not row["disabled"]
    ]


def control_value(target, value):
    if target.get("tag") != "select":
        return value
    options = [o for o in target.get("options", []) if not o.get("disabled")]
    matches = [o for o in options if o.get("value") == value]
    if not matches:
        matches = [o for o in options if o.get("label") == value]
    if len(matches) != 1:
        raise ValueError("선택값이 없거나 중복됩니다. 항목을 직접 확인하세요.")
    return matches[0]["value"]


class ResumeSync:
    def __init__(
        self, paths, profile_reader, *, registry=None, headed=True, editor_check=None
    ):
        self.paths = paths
        self.profile_reader = profile_reader
        self.registry = registry or SiteRegistry()
        self.headed = headed
        self.editor_check = editor_check or resume_editor
        self.contexts, self.sessions, self.previews = {}, {}, {}
        self.playwright = None
        self.store = ArtifactStore(paths.results / "site_sync")

    def _site(self, payload):
        site = payload.get("site")
        if site not in default_sites():
            raise ValueError("지원 사이트를 선택하세요.")
        return site

    async def open(self, payload):
        site = self._site(payload)
        if site not in self.contexts:
            if self.playwright is None:
                from playwright.async_api import async_playwright

                self.playwright = await async_playwright().start()
            session = BrowserSession(
                self.playwright,
                site,
                paths=self.paths,
                registry=self.registry,
                headed=self.headed,
            )
            self.contexts[site] = await session.__aenter__()
            self.sessions[site] = session
            context = self.contexts[site]
            # Unknown website dialogs are never accepted automatically.
            context.on(
                "page", lambda page: page.on("dialog", lambda dialog: dialog.dismiss())
            )
            page = context.pages[0] if context.pages else await context.new_page()
            page.on("dialog", lambda dialog: dialog.dismiss())
            editor_url = self.registry.target(site)["candidate_urls"][0]
            saved_path = self.store.directory / f"{site}-bindings.json"
            if saved_path.exists():
                try:
                    remembered = json.loads(saved_path.read_text(encoding="utf-8")).get(
                        "editor_url"
                    )
                    if (
                        isinstance(remembered, str)
                        and self.registry.matches_url(site, remembered)
                        and self.editor_check(site, remembered)
                    ):
                        editor_url = remembered
                except (ValueError, AttributeError, OSError):
                    pass
            await page.goto(
                editor_url,
                wait_until="domcontentloaded",
                timeout=30000,
            )
        return {
            "site": site,
            "status": "login_and_open_editor",
            "message": "전용 브라우저에서 로그인하고 기존 이력서 편집 화면을 여세요.",
        }

    def _page(self, site):
        context = self.contexts.get(site)
        if context is None:
            raise ValueError("먼저 사이트 브라우저를 여세요.")
        pages = [
            p
            for p in context.pages
            if not p.is_closed() and self.registry.matches_url(site, p.url)
        ]
        if len(pages) != 1:
            raise ValueError("해당 사이트의 편집 탭 하나만 남긴 뒤 다시 확인하세요.")
        return pages[0]

    async def status(self, payload):
        site = self._site(payload)
        if site not in self.contexts:
            return {
                "site": site,
                "status": "not_opened",
                "message": "먼저 전용 사이트 브라우저를 여세요.",
            }
        try:
            page = self._page(site)
        except ValueError:
            return {
                "site": site,
                "status": "choose_editor",
                "message": "인증 팝업을 완료하고 이력서 편집 탭 하나만 남겨 주세요.",
            }
        checks = [
            (
                'input[autocomplete="one-time-code"]:visible, input[name*="otp" i]:visible, input[id*="otp" i]:visible',
                "mfa_required",
                "전용 브라우저에서 문자·앱 등의 2차 인증을 직접 완료하세요. 인증번호를 이 서비스에 입력하지 마세요.",
            ),
            (
                'iframe[src*="captcha" i]:visible, #challenge-running:visible',
                "security_check",
                "사이트의 보안 확인을 직접 완료하세요. 자동 우회하지 않습니다.",
            ),
            (
                'input[type="password"]:visible',
                "login_required",
                "전용 브라우저의 해당 사이트에 직접 로그인하세요. 일반 Chrome의 기존 로그인은 별도입니다.",
            ),
        ]
        for selector, status, message in checks:
            if await page.locator(selector).count():
                return {"site": site, "status": status, "message": message}
        if not self.editor_check(site, page.url):
            return {
                "site": site,
                "status": "open_editor",
                "message": "로그인·2차 인증을 완료한 뒤 기존 이력서의 수정 화면으로 이동하세요. 이력서 목록이나 지원 화면은 사용할 수 없습니다.",
            }
        return {
            "site": site,
            "status": "editor_candidate",
            "message": "편집 화면 후보입니다. 현재 편집 화면 확인으로 입력 항목을 수집·검수하세요. 로그인·저장 완료 판정은 아닙니다.",
        }

    async def capture(self, payload):
        site = self._site(payload)
        state = await self.status(payload)
        if state["status"] != "editor_candidate":
            raise ValueError(state["message"])
        page = self._page(site)
        if (
            not self.editor_check(site, page.url)
            or await page.locator('input[type="password"]:visible').count()
        ):
            raise ValueError(
                "기존 이력서 편집 화면으로 이동하세요. 로그인·목록·지원 화면은 사용할 수 없습니다."
            )
        source = self.profile_reader()
        profile = ResumeProfile(payload.get("profile", source))
        package = profile.package()
        observation = await capture_page(page, site, registry=self.registry)
        fields = [
            f
            for f in candidate_fields(observation)
            if f.get("visible", True)
            and not f.get("disabled")
            and not f.get("read_only")
        ]
        buttons = await save_controls(page)
        nonce = secrets.token_urlsafe(24)
        self.previews[site] = {
            "nonce": nonce,
            "profile_digest": digest(profile.to_dict()),
            "source_digest": digest(source),
            "url": page.url,
            "fields": fields,
            "buttons": buttons,
            "page": page,
        }
        saved_path = self.store.directory / f"{site}-bindings.json"
        saved = (
            json.loads(saved_path.read_text(encoding="utf-8"))
            if saved_path.exists()
            else {}
        )
        mappings = []
        for row in saved.get("mappings", []):
            for index, field in enumerate(fields):
                if (
                    field == row["target"]
                    and row["field_id"] in package["package"]["field_values"]
                ):
                    mappings.append(
                        {"field_id": row["field_id"], "target_index": index}
                    )
        save_index = next(
            (
                i
                for i, button in enumerate(buttons)
                if button == saved.get("save_button")
            ),
            None,
        )
        return {
            "site": site,
            "nonce": nonce,
            "url": page.url,
            "fields": fields,
            "buttons": buttons,
            "profile_fields": [
                {"id": key, "value": value}
                for key, value in package["package"]["field_values"].items()
            ],
            "saved_mappings": mappings,
            "suggested_mappings": propose_mappings(
                package["package"]["field_values"], fields
            ),
            "saved_save_index": save_index,
            "suggested_save_index": 0 if len(buttons) == 1 else None,
            "autosave_available": site == "wanted",
        }

    async def apply(self, payload):
        site = self._site(payload)
        preview = self.previews.get(site)
        if (
            not preview
            or payload.get("nonce") != preview["nonce"]
            or payload.get("consent") is not True
        ):
            raise ValueError("현재 미리보기와 입력·저장 승인이 필요합니다.")
        source = self.profile_reader()
        profile = ResumeProfile(payload.get("profile", source))
        if digest(profile.to_dict()) != preview["profile_digest"]:
            raise ValueError("이력서가 변경되었습니다. 다시 미리보기를 확인하세요.")
        if digest(source) != preview["source_digest"]:
            raise ValueError("공통 원본이 변경되었습니다. 다시 미리보기를 확인하세요.")
        page = self._page(site)
        if page is not preview["page"] or page.url != preview["url"]:
            raise ValueError("편집 화면이 변경되었습니다. 다시 수집하세요.")
        state = await self.status(payload)
        if state["status"] != "editor_candidate":
            raise ValueError(state["message"])
        if (
            not self.editor_check(site, page.url)
            or await page.locator('input[type="password"]:visible').count()
        ):
            raise ValueError("이력서 편집 화면만 입력·저장할 수 있습니다.")
        values = profile.package()["package"]["field_values"]
        selected = payload.get("mappings")
        if not isinstance(selected, list) or not 1 <= len(selected) <= 100:
            raise ValueError("저장할 항목 연결을 선택하세요.")
        actions = []
        seen = set()
        for row in selected:
            if not isinstance(row, dict):
                raise ValueError("잘못된 항목 연결입니다.")
            key, index = row.get("field_id"), row.get("target_index")
            if (
                key not in values
                or type(index) is not int
                or not 0 <= index < len(preview["fields"])
                or index in seen
            ):
                raise ValueError("항목 연결이 잘못되었거나 중복됩니다.")
            seen.add(index)
            actions.append(
                {
                    "path": key,
                    "value": control_value(preview["fields"][index], values[key]),
                    "target": preview["fields"][index],
                }
            )
        current_fields = candidate_fields(
            await capture_page(page, site, registry=self.registry)
        )
        if any(action["target"] not in current_fields for action in actions):
            raise ValueError("입력 항목이 변경되었습니다. 다시 수집하세요.")
        save_index = payload.get("save_index")
        autosave = payload.get("autosave") is True
        button = None
        if autosave:
            if site != "wanted" or save_index is not None:
                raise ValueError("자동저장은 원티드에서만 선택할 수 있습니다.")
        else:
            if type(save_index) is not int or not 0 <= save_index < len(
                preview["buttons"]
            ):
                raise ValueError("확인된 저장 버튼을 선택하세요.")
            button = preview["buttons"][save_index]
            if button not in await save_controls(page):
                raise ValueError("저장 버튼이 바뀌었습니다. 다시 수집하세요.")
        allowed = lambda url: self.registry.matches_url(site, url)
        filler = FormFiller(page, actions, allowed_url=allowed)
        await filler.preflight()
        backup = []
        for action in actions:
            locator = await filler._resolve_target(action["target"])
            backup.append(
                {
                    "field_id": action["path"],
                    "target": action["target"],
                    "before": await locator.evaluate(
                        "el => el.isContentEditable ? el.innerText : el.value"
                    ),
                    "after": action["value"],
                }
            )
        record_id = uuid4().hex
        record = {
            "id": record_id,
            "site": site,
            "status": "started",
            "backup": backup,
            "changed_fields": [a["path"] for a in actions],
        }
        self.store.write_json(f"{record_id}.json", record)
        # Consume the review token before mutation; an uncertain save is not retried.
        del self.previews[site]
        try:
            await filler.apply()
            if button:
                if page.url != preview["url"] or button not in await save_controls(
                    page
                ):
                    raise ValueError("저장 화면이 변경되었습니다.")
                await page.locator(button["selector"]).click(timeout=10000)
            await asyncio.sleep(2)
            if not allowed(page.url):
                raise ValueError("저장 후 허용 사이트를 벗어났습니다.")
            await page.goto(
                preview["url"], wait_until="domcontentloaded", timeout=30000
            )
            for action in actions:
                locator = await filler._resolve_target(action["target"])
                await locator.wait_for(state="visible", timeout=10000)
                current = await locator.evaluate(
                    "el => el.isContentEditable ? el.innerText : el.value"
                )
                if current.replace("\r\n", "\n") != action["value"].replace(
                    "\r\n", "\n"
                ):
                    raise ValueError("새로고침 후 저장값을 확인하지 못했습니다.")
            record["status"] = "saved_verified"
            self.store.write_json(
                f"{site}-bindings.json",
                {
                    "editor_url": preview["url"],
                    "mappings": [
                        {"field_id": a["path"], "target": a["target"]} for a in actions
                    ],
                    "save_button": button,
                },
            )
        except Exception:
            record["status"] = "save_unverified"
        self.store.write_json(f"{record_id}.json", record)
        return {
            "site": site,
            "id": record_id,
            "status": record["status"],
            "changed_fields": record["changed_fields"],
            "message": "선택 항목 저장 및 재접속 확인 완료"
            if record["status"] == "saved_verified"
            else "일부 입력·저장이 발생했을 수 있습니다. 브라우저에서 확인하세요. 자동 재시도하지 않습니다.",
        }

    async def close(self):
        for session in self.sessions.values():
            await session.__aexit__(None, None, None)
        if self.playwright:
            await self.playwright.stop()

    async def close_site(self, payload):
        site = self._site(payload)
        session = self.sessions.pop(site, None)
        if session:
            await session.__aexit__(None, None, None)
        self.contexts.pop(site, None)
        self.previews.pop(site, None)
        return {"site": site, "status": "closed"}


class SyncWorker:
    """Keep Playwright contexts on one event loop across HTTP requests."""

    def __init__(self, engine):
        self.engine = engine
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def call(self, operation, payload):
        future = asyncio.run_coroutine_threadsafe(
            getattr(self.engine, operation)(payload), self.loop
        )
        return future.result()

    def close(self):
        asyncio.run_coroutine_threadsafe(self.engine.close(), self.loop).result(
            timeout=30
        )
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)
        self.loop.close()
