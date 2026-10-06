"""Fill individually reviewed fields; saving and submission remain manual."""

import argparse
import asyncio
from copy import deepcopy

from job_agent.browser.connector import flatten_package_values, load_json
from job_agent.browser.session import BrowserSession
from job_agent.sites.registry import SiteRegistry


def approved_actions(package, plan):
    values = {row["path"]: row["value"] for row in flatten_package_values(package)}
    actions = []
    for item in plan.get("mappings", []):
        if item.get("approved") is not True:
            continue
        match = item.get("best_match")
        path = item.get("package_path")
        if not match or not match.get("selector") or path not in values:
            raise ValueError(f"Approved field has no selector or package value: {path}")
        actions.append({"path": path, "value": values[path], "target": match})
    if not actions:
        raise ValueError('Mark reviewed mappings with "approved": true first')
    return actions


class FormFiller:
    """Own a reviewed action snapshot and validate live controls before mutation."""

    def __init__(self, page, actions, *, allowed_url=None):
        self._page = page
        self._actions = deepcopy(actions)
        self._allowed_url = allowed_url

    async def _resolve_target(self, target):
        if self._allowed_url is not None and not self._allowed_url(self._page.url):
            raise ValueError("Page moved outside the allowed origins")
        frame = self._page.main_frame
        for index in target.get("frame_path", []):
            if (
                not isinstance(index, int)
                or index < 0
                or index >= len(frame.child_frames)
            ):
                raise ValueError("Frame structure changed; capture the form again")
            frame = frame.child_frames[index]
        if target.get("frame_path") and frame.url != target.get("frame_url"):
            raise ValueError("Frame URL changed or missing; capture the form again")
        if (
            self._allowed_url is not None
            and frame.url not in {"about:blank", "about:srcdoc"}
            and not self._allowed_url(frame.url)
        ):
            raise ValueError("Frame is outside the allowed origins")
        scope = frame
        for host in target.get("shadow_hosts", []):
            scope = scope.locator(host)
            if await scope.count() != 1:
                raise ValueError("Shadow host is not unique")
        locator = scope.locator(target["selector"])
        if await locator.count() != 1:
            raise ValueError("Selector is missing or ambiguous")
        return locator

    async def _validate_action(self, action):
        locator = await self._resolve_target(action["target"])
        if not await locator.is_visible() or not await locator.is_enabled():
            raise ValueError("Field is hidden or disabled")
        state = await locator.evaluate(
            """(el, value) => ({
          tag: el.localName, type: el.type || '', editable: el.isContentEditable,
          readonly: !!el.readOnly || el.getAttribute('aria-readonly') === 'true',
          max: el.getAttribute('maxlength'), length: value.length,
          select_valid: el.localName !== 'select' || Array.from(el.options).some(o => o.value === value && !o.disabled)
        })""",
            action["value"],
        )
        if state["readonly"] or state["type"] in {
            "password",
            "hidden",
            "file",
            "checkbox",
            "radio",
            "submit",
            "button",
            "reset",
        }:
            raise ValueError("Field cannot be filled by this runner")
        if (
            state["tag"] not in {"input", "textarea", "select"}
            and not state["editable"]
        ):
            raise ValueError("Custom controls require a site-specific adapter")
        if (
            state["max"] is not None
            and int(state["max"]) >= 0
            and state["length"] > int(state["max"])
        ):
            raise ValueError("Value exceeds live maxlength")
        if not state["select_valid"]:
            raise ValueError("Value is not an enabled select option")
        return locator, state

    async def preflight(self):
        seen = []
        try:
            for action in self._actions:
                locator, _ = await self._validate_action(action)
                element = await locator.element_handle()
                seen.append(element)
                for previous in seen[:-1]:
                    if await element.evaluate(
                        "(el, previous) => el === previous", previous
                    ):
                        raise ValueError("Multiple values resolve to the same field")
        finally:
            # Handles detect selectors that alias the same DOM node.
            for element in seen:
                await element.dispose()

    async def apply(self):
        await self.preflight()
        for action in self._actions:
            locator, state = await self._validate_action(action)
            if state["tag"] == "select":
                await locator.select_option(action["value"])
            else:
                await locator.fill(action["value"])
            # Some resume editors commit controlled inputs only on blur (and autosave).
            await locator.press("Tab")
            current = await locator.evaluate(
                "el => el.isContentEditable ? el.innerText : el.value"
            )
            if current.replace("\r\n", "\n") != action["value"].replace("\r\n", "\n"):
                raise RuntimeError(f"Input verification failed: {action['path']}")


async def main(argv=None):
    parser = argparse.ArgumentParser(
        description="검수된 이력서 필드 입력 (기본: 검증만)"
    )
    parser.add_argument("--site", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--browser-path")
    parser.add_argument("--target", help="Registered company target JSON")
    args = parser.parse_args(argv)
    registry = SiteRegistry.from_file(args.target)
    site = registry.normalize(args.site)
    plan = load_json(args.mapping)
    package = load_json(args.package)
    if plan.get("package_site") and registry.normalize(plan["package_site"]) != site:
        raise ValueError("Package site differs from selected site")
    if package.get("site") and registry.normalize(package["site"]) != site:
        raise ValueError("Package site differs from selected site")
    url = plan.get("form_url", "")
    if not registry.matches_url(site, url):
        raise ValueError("Mapping URL differs from selected site")
    actions = approved_actions(package, plan)
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        async with BrowserSession(
            p, site, browser_path=args.browser_path, registry=registry
        ) as context:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.to_thread(
                input, "로그인 후 해당 편집 화면/섹션을 열고 Enter: "
            )
            pages = [
                tab for tab in context.pages if tab.url == url and not tab.is_closed()
            ]
            if len(pages) != 1:
                raise ValueError("Expected exactly one tab at the captured form URL")
            page = pages[0]
            filler = FormFiller(
                page, actions, allowed_url=lambda url: registry.matches_url(site, url)
            )
            await filler.preflight()
            for action in actions:
                print(f"검증: {action['path']} ({len(action['value'])} chars)")
            if args.apply:
                print(
                    "입력 내용은 사이트에 전송되며 자동 저장될 수 있습니다. 저장/지원 버튼은 누르지 않습니다."
                )
                confirm = await asyncio.to_thread(
                    input, f"{site} {len(actions)}개 필드 입력: APPLY 입력 시 실행: "
                )
                if confirm == "APPLY":
                    if page.url != url:
                        raise ValueError(
                            "Page changed after review; capture the form again"
                        )
                    await filler.apply()
                    print("입력값 검증 완료. 화면에서 최종 검수하세요.")
                    await asyncio.to_thread(
                        input,
                        "검수 및 필요한 수동 저장이 끝나면 Enter로 브라우저 종료: ",
                    )
            else:
                print("검증만 완료. 실제 입력에는 --apply가 필요합니다.")


if __name__ == "__main__":
    asyncio.run(main())
