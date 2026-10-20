"""Read public search cards without cookies, scripts, login or internal APIs.

Only supported server-rendered layouts are parsed. Missing/blocked layouts
return no cards so the caller can report and use its index fallback.
"""

import re
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlsplit

import httpx

from job_agent.core.job_match import experience
from job_agent.core.postings import APPLY_LABEL, canonical_url


class Node:
    def __init__(self, tag="root", attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def text(self):
        return " ".join(
            (child.text() if isinstance(child, Node) else child)
            for child in self.children
        ).strip()

    def joined(self):
        """Text as displayed; highlight spans must not split words."""
        return " ".join(
            "".join(
                (child.joined() if isinstance(child, Node) else child)
                for child in self.children
            ).split()
        )

    def nodes(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.nodes()

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()


class Cards(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.current = Node()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self.current = node

    def handle_endtag(self, tag):
        node = self.current
        while node.parent:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data):
        if self.current.tag not in {"script", "style"}:
            self.current.children.append(data)


def _apply_button(nodes):
    return any(
        n.tag in {"a", "button"}
        and re.fullmatch(APPLY_LABEL, " ".join(n.text().split()))
        and "disabled" not in n.attrs
        and n.attrs.get("aria-disabled") != "true"
        for n in nodes
    )


def _card_experience(nodes):
    """First short leaf text that states a career condition (e.g. 경력1년↑)."""
    for node in nodes:
        label = " ".join(node.text().split())
        if (
            not any(isinstance(c, Node) for c in node.children)
            and len(label) <= 20
            and re.match(r"신입|경력", label)
        ):
            parsed = experience(label)
            if parsed["kind"] != "unknown":
                return parsed
    return experience("")


def parse_cards(site, html):
    parser = Cards()
    parser.feed(html)
    nodes = list(parser.root.nodes())
    rows = []
    if site == "saramin":
        for card in (n for n in nodes if n.has_class("item_recruit")):
            inner = list(card.nodes())
            heading = next((n for n in inner if n.has_class("job_tit")), None)
            employer = next((n for n in inner if n.has_class("corp_name")), None)
            link = (
                next((n for n in heading.nodes() if n.tag == "a"), None)
                if heading
                else None
            )
            if link and employer and "rec_idx=" in link.attrs.get("href", ""):
                href = urljoin("https://www.saramin.co.kr", link.attrs.get("href", ""))
                if urlsplit(href).hostname != "www.saramin.co.kr":
                    continue
                condition = next(
                    (n for n in inner if n.has_class("job_condition")), None
                )
                location = (
                    next(
                        (
                            n.text()
                            for n in condition.children
                            if isinstance(n, Node) and n.tag == "span"
                        ),
                        "",
                    )
                    if condition
                    else ""
                )
                apply = _apply_button(inner)
                rows.append(
                    {
                        "title": link.attrs.get("title") or link.text(),
                        "company_name": employer.text(),
                        "url": href,
                        "content": card.text()[:10000],
                        "retrieval_source": "native_search",
                        "requirements_card": {
                            "job_location": location,
                            "experience": experience(
                                condition.text() if condition else ""
                            ),
                            "job_title": link.attrs.get("title") or link.text(),
                            "application_available": apply,
                        },
                    }
                )
    elif site == "incruit":
        for card in (n for n in nodes if n.tag == "ul" and n.has_class("c_row")):
            inner = list(card.nodes())
            employer = next(
                (n for n in inner if n.tag == "a" and n.has_class("cpname")), None
            )
            link = next(
                (
                    n
                    for n in inner
                    if n.tag == "a"
                    and re.search(
                        r"/jobdb_info/jobpost\.asp\?job=\d+", n.attrs.get("href", "")
                    )
                ),
                None,
            )
            if link and employer:
                href = urljoin("https://job.incruit.com", link.attrs["href"])
                if urlsplit(href).hostname != "job.incruit.com":
                    continue
                title = link.joined()
                # cl_md lists location, career, education and type as spans.
                facts = next(
                    (n for n in inner if n.has_class("cl_md")), None
                )
                spans = (
                    [n for n in facts.children if isinstance(n, Node)]
                    if facts
                    else []
                )
                rows.append(
                    {
                        "title": title,
                        "company_name": employer.text(),
                        "url": href,
                        "content": card.text()[:10000],
                        "retrieval_source": "native_search",
                        "requirements_card": {
                            "job_location": spans[0].text() if spans else "",
                            "experience": _card_experience(spans),
                            "job_title": title,
                            "application_available": _apply_button(inner),
                        },
                    }
                )
    elif site == "jobkorea":
        grouped = {}
        for node in nodes:
            if (
                node.tag == "a"
                and urlsplit(
                    urljoin("https://www.jobkorea.co.kr", node.attrs.get("href", ""))
                ).hostname
                != "www.jobkorea.co.kr"
            ):
                continue
            match = (
                re.search(
                    r"/Recruit/GI_Read/(\d+)", node.attrs.get("href", ""), re.IGNORECASE
                )
                if node.tag == "a"
                else None
            )
            if match and node.text():
                grouped.setdefault(match[1], []).append(node)
        for identity, links in grouped.items():
            labels = list(dict.fromkeys(link.text() for link in links))
            if len(labels) < 2:
                continue
            card = links[0].parent
            while card.parent and not any(n is links[-1] for n in card.nodes()):
                card = card.parent
            inner = list(card.nodes())
            # The location chip is the one with the place emoji icon.
            place = next(
                (
                    n
                    for n in inner
                    if n.attrs.get("data-sentry-component") == "GrayChip"
                    and any("place" in c.attrs.get("class", "") for c in n.nodes())
                ),
                None,
            )
            rows.append(
                {
                    "title": labels[0],
                    "company_name": labels[-1],
                    "url": f"https://www.jobkorea.co.kr/Recruit/GI_Read/{identity}",
                    "content": card.text()[:10000],
                    "retrieval_source": "native_search",
                    "requirements_card": {
                        "job_location": " ".join(place.text().split()) if place else "",
                        "experience": _card_experience(inner),
                        "job_title": labels[0],
                        "application_available": _apply_button(inner),
                    },
                }
            )
    return rows


def native_search(query, domain):
    site = {
        "jobkorea.co.kr": "jobkorea",
        "saramin.co.kr": "saramin",
        "incruit.com": "incruit",
    }.get(domain)
    if not site:
        return []
    keyword = re.sub(r"\s+채용$", "", query).strip()
    # Location is checked on the returned card; do not AND every region in the search box.
    keyword = re.sub(r"\s+(?:서울|경기|판교)(?=\s|$)", "", keyword).strip()
    keyword = keyword.replace("분석가", "분석")
    base, parameter, page_parameter = {
        "jobkorea": ("https://www.jobkorea.co.kr/Search/", "stext", "Page_No"),
        "saramin": (
            "https://www.saramin.co.kr/zf_user/search",
            "searchword",
            "recruitPage",
        ),
        "incruit": ("https://search.incruit.com/list/search.asp", "kw", "startno"),
    }[site]
    rows, seen = [], set()
    # Site search boxes take one phrase; 'A OR B' would be searched literally.
    alternatives = [
        part.strip()
        for part in re.split(r"\s+OR\s+", keyword, flags=re.IGNORECASE)
        if part.strip()
    ]
    with httpx.Client(timeout=12, follow_redirects=False, trust_env=False) as client:
        for word in alternatives:
            for page in range(1, 4):
                params = {parameter: word, page_parameter: page}
                if site == "incruit":
                    params["col"] = "job"
                    params[page_parameter] = (page - 1) * 30
                encoded = urlencode(
                    params,
                    encoding="euc-kr" if site == "incruit" else "utf-8",
                    errors="replace",
                )
                client.cookies.clear()
                with client.stream("GET", base + "?" + encoded) as response:
                    if response.status_code != 200:
                        break
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 3_000_000:
                            return rows
                        chunks.append(chunk)
                    html = b"".join(chunks).decode(
                        "euc-kr" if site == "incruit" else "utf-8", errors="replace"
                    )
                cards = parse_cards(site, html)
                fresh = [r for r in cards if canonical_url(r["url"]) not in seen]
                if not fresh:
                    break
                for row in fresh:
                    row["retrieval_page"] = page
                    seen.add(canonical_url(row["url"]))
                    rows.append(row)
    groups = [
        re.findall(r"[가-힣A-Za-z0-9]+", part.casefold())
        for part in re.split(r"\s+OR\s+", keyword, flags=re.IGNORECASE)
    ]

    def relevant(row):
        body = re.sub(r"\s+", "", (row["title"] + " " + row["content"]).casefold())
        return any(
            group and all(token.replace("분석가", "분석") in body for token in group)
            for group in groups
        )

    return [row for row in rows if relevant(row)][:100]
