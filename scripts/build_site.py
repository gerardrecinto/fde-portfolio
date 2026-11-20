"""Build _site/ from site/. Puts the saved demo output into demo.html.

Usage: python3 scripts/build_site.py demo/output.txt
Fails if a placeholder is left behind.
"""
import html, pathlib, shutil, sys

root = pathlib.Path(__file__).resolve().parent.parent
src, out = root / "site", root / "_site"
demo_out = pathlib.Path(sys.argv[1]).read_text() if len(sys.argv) > 1 else ""
if out.exists():
    shutil.rmtree(out)
shutil.copytree(src, out)

pages = [("index.html", "Home"), ("demo.html", "Customer demo"), ("case-studies.html", "Case studies"), ("interview.html", "Interview Q&A")]

def nav(active):
    items = "".join(
        f'<a href="{h}"{" aria-current=\"page\"" if h == active else ""}>{t}</a>' for h, t in pages)
    return ('<a class="skip" href="#main">Skip to content</a><header class="top"><div class="wrap">'
            f'<a class="brand" href="index.html">Gerard Recinto</a><nav aria-label="Main">{items}</nav></div></header>')

foot = ('<footer><div class="wrap"><p>Code and docs are public. Source for this site: '
        '<a href="https://github.com/gerardrecinto/fde-portfolio">gerardrecinto/fde-portfolio</a> (MIT). '
        'Joltrin is MIT licensed and lives in <a href="https://github.com/SharedCode/joltrin">SharedCode/joltrin</a>; '
        'its contributor credits are in that repo.</p></div></footer>')

for name, _ in pages:
    p = out / name
    t = p.read_text()
    t = t.replace("<!--NAV-->", nav(name)).replace("<!--FOOT-->", foot)
    t = t.replace("{{DEMO_OUTPUT}}", html.escape(demo_out))
    if "{{" in t and name != "demo.html" or "<!--NAV-->" in t:
        sys.exit(f"{name}: placeholder left behind")
    p.write_text(t)
(out / ".nojekyll").write_text("")
print(f"built {len(pages)} pages into {out}")
