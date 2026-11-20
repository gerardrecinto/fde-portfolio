"""Check every link in the built site. Internal links and anchors always; external links with --external.
Exits 1 on any broken link."""
import html.parser, pathlib, sys, urllib.request, urllib.error, concurrent.futures as cf

site = pathlib.Path(__file__).resolve().parent.parent / "_site"
external = "--external" in sys.argv


class P(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, a):
        a = dict(a)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])


pages = {}
for f in site.glob("*.html"):
    p = P()
    p.feed(f.read_text())
    pages[f.name] = p
bad, ext = [], set()
for name, p in pages.items():
    for h in p.links:
        if h.startswith("http"):
            ext.add(h)
            continue
        path, _, frag = h.partition("#")
        target = path or name
        if target not in pages:
            bad.append(f"{name}: {h} (no such page)")
        elif frag and frag not in pages[target].ids:
            bad.append(f"{name}: {h} (no such anchor)")


def get(u):
    for method in ("HEAD", "GET"):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, method=method, headers={"User-Agent": "link-check"}), timeout=20)
            return u, r.status
        except urllib.error.HTTPError as e:
            if method == "GET":
                return u, e.code
        except Exception as e:
            if method == "GET":
                return u, str(e)


if external:
    with cf.ThreadPoolExecutor(8) as ex:
        for u, s in ex.map(get, sorted(ext)):
            if s != 200:
                bad.append(f"external {u}: {s}")
print(f"{sum(len(p.links) for p in pages.values())} links, {len(ext)} external{' (checked)' if external else ' (not checked)'}")
print("\n".join(bad) or "no broken links")
sys.exit(1 if bad else 0)
