"""Read public search cards without cookies, scripts, login or internal APIs.

Only supported server-rendered layouts are parsed. Missing/blocked layouts
return no cards so the caller can report and use its index fallback.
"""

import re
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlsplit

import httpx


class Node:
    def __init__(self, tag="root", attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def text(self):
        return " ".join(
            (child.text() if isinstance(child, Node) else child)
            for child in self.children
        ).strip()

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
                rows.append(
                    {
                        "title": link.attrs.get("title") or link.text(),
                        "company_name": employer.text(),
                        "url": href,
                        "content": card.text()[:10000],
                        "retrieval_source": "native_search",
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
            rows.append(
                {
                    "title": labels[0],
                    "company_name": labels[-1],
                    "url": f"https://www.jobkorea.co.kr/Recruit/GI_Read/{identity}",
                    "content": card.text()[:10000],
                    "retrieval_source": "native_search",
                }
            )
    return rows


def native_search(query, domain):
    site = {"jobkorea.co.kr": "jobkorea", "saramin.co.kr": "saramin"}.get(domain)
    if not site:
        return []
    keyword = re.sub(r"\s+채용$", "", query).strip()
    # Location is checked on the returned card; do not AND every region in the search box.
    keyword = re.sub(r"\s+(?:서울|경기|판교)(?=\s|$)", "", keyword).strip()
    keyword = keyword.replace("분석가", "분석")
    base, parameter = (
        ("https://www.jobkorea.co.kr/Search/", "stext")
        if site == "jobkorea"
        else ("https://www.saramin.co.kr/zf_user/search", "searchword")
    )
    with (
        httpx.Client(timeout=12, follow_redirects=False, trust_env=False) as client,
        client.stream("GET", base + "?" + urlencode({parameter: keyword})) as response,
    ):
        if response.status_code != 200:
            return []
        chunks, size = [], 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > 3_000_000:
                return []
            chunks.append(chunk)
    rows = parse_cards(site, b"".join(chunks).decode("utf-8", errors="replace"))
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

    return [row for row in rows if relevant(row)][:60]
