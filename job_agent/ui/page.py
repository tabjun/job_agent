"""Filter operator-only choices before a remote page reaches the browser."""

from html.parser import HTMLParser


class RemotePage(HTMLParser):
    def __init__(self, providers, web_search):
        super().__init__(convert_charrefs=False)
        self.providers = providers
        self.web_search = web_search
        self.parts = []
        self.select = None
        self.label = None
        self.skip_option = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "select":
            self.select = attributes.get("id")
        if tag == "label":
            self.label = attributes.get("id")
        if tag == "option":
            value = attributes.get("value")
            self.skip_option = (
                self.select == "provider" and value not in self.providers
            ) or (self.select == "source" and value == "web" and not self.web_search)
        if not self.skip_option:
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if not self.skip_option:
            self.parts.append(f"</{tag}>")
        if tag == "option":
            self.skip_option = False
        elif tag == "select":
            self.select = None
        elif tag == "label":
            self.label = None

    def handle_data(self, data):
        if self.skip_option:
            return
        if self.label == "ai-consent-label" and data.strip():
            data = "입력 자료의 AI 전송에 동의"
        elif self.label == "search-consent-label" and data.strip():
            data = "검색어 전송에 동의"
        self.parts.append(data)

    def handle_decl(self, decl):
        self.parts.append(f"<!{decl}>")

    def handle_entityref(self, name):
        if not self.skip_option:
            self.parts.append(f"&{name};")

    def handle_charref(self, name):
        if not self.skip_option:
            self.parts.append(f"&#{name};")


def remote_page(source, providers, web_search=False):
    parser = RemotePage(providers, web_search)
    parser.feed(source)
    parser.close()
    return "".join(parser.parts).encode("utf-8")
