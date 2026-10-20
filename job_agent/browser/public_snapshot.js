() => {
  const root = document.querySelector("main") || document.body;
  const clone = root.cloneNode(true);
  const originals = [root, ...root.querySelectorAll("*")];
  const copies = [clone, ...clone.querySelectorAll("*")];
  for (let i = originals.length - 1; i > 0; i--) {
    const original = originals[i], copy = copies[i];
    const style = getComputedStyle(original);
    if (["SCRIPT", "STYLE", "NOSCRIPT", "HEADER", "NAV", "FOOTER"].includes(original.tagName)
        || style.display === "none" || style.visibility === "hidden" || original.hidden) copy.remove();
  }
  const schema = [...document.querySelectorAll('script[type="application/ld+json"]')].map(n => n.outerHTML).join("");
  const meta = [...document.querySelectorAll('meta[name="description"]')].map(n => n.outerHTML).join("");
  const escape = value => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const buttons = [...document.querySelectorAll("button,a,[role=button]")].filter(n => {
    const text = (n.innerText || n.getAttribute("aria-label") || "").replace(/\s+/g, "");
    return /^(?:홈페이지|간편|즉시|온라인|바로)?(?:입사)?지원(?:하기|서작성)?$/.test(text)
      && n.getBoundingClientRect().width > 0 && n.getBoundingClientRect().height > 0;
  }).map(n => `<button${n.disabled || n.getAttribute("aria-disabled") === "true" ? " disabled" : ""}>${escape(n.innerText || n.getAttribute("aria-label"))}</button>`).join("");
  return `<!doctype html><html><head>${meta}${schema}</head><body>${clone.outerHTML}${buttons}</body></html>`;
}
