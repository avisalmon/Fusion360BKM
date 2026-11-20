r"""Write library/index.html: the part library as a page, from every library/<owner>/<part>/part.json.

    python scripts\library_page.py            # write the page
    python scripts\library_page.py --check    # exit 1 if the page is not current (the tests run this)

The page shows each part (photos, what it is, where it lives, its pins, its footprint and symbol as
Fusion drew them, its 3D model, the boards that use it, its files), the owner's deal for borrowing
parts ("take one, give back two"), and what a part in a library is made of, so a reader can start
their own. Everything comes from the library's own files; nothing is typed into the page by hand.
"""

import argparse
import html
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "library"
OUT = LIB / "index.html"
REPO = "https://github.com/avisalmon/Fusion360BKM"
esc = html.escape


def both(he, en):
    return f'<span lang="he">{he}</span><span lang="en">{en}</span>'


def parts():
    out = []
    for pj in sorted(LIB.glob("*/*/part.json"), key=lambda p: p.as_posix()):
        d = json.loads(pj.read_text(encoding="utf-8-sig"))
        d["_dir"] = pj.parent
        d["_owner"] = pj.parent.parent.name
        out.append(d)
    return out


def used_in():
    """Which example boards place each library part: {part_id: [(folder, title)]}."""
    uses = {}
    for brd in sorted(ROOT.glob("examples/*/fusion/*.brd"), key=lambda p: p.as_posix()):
        ex = brd.parent.parent
        readme = ex / "README.md"
        title = ex.name
        if readme.exists():
            first = readme.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
            title = first.split(":")[0]
        for lib in sorted(
            set(re.findall(r'<element [^>]*library="([^"]+)"', brd.read_text(encoding="utf-8")))
        ):
            uses.setdefault(lib, []).append((ex.name, title))
    return uses


def first_sentence(s, most=150):
    """The description's first sentence, or its first words up to `most` characters."""
    s = s or ""
    m = re.match(r"(.+?\.)(\s|$)", s)
    s = m.group(1) if m else s
    return s if len(s) <= most else s[:most].rsplit(" ", 1)[0] + " …"


def t(s):
    """English text from the records, kept in its own direction on the Hebrew page."""
    return f"<bdi>{esc(str(s))}</bdi>"


def rel(p):
    return p.relative_to(LIB).as_posix()


OWNER_MAIL = "avi.salmon@gmail.com"  # published on the owner's word, 2026-11-20


def borrow_link(d):
    subject = f"Take one, give back two: {d['name']}"
    body = (
        f"I would like to borrow: {d['name']} (library/{d['_owner']}/{d['id']}).\n"
        "I will order two and bring them back when they arrive."
    )
    q = urllib.parse.urlencode({"subject": subject, "body": body}, quote_via=urllib.parse.quote)
    return f"mailto:{OWNER_MAIL}?{q}"


def check_line(label_he, label_en, text):
    ok = bool(text)
    mark = "✓" if ok else "·"
    cls = "ok" if ok else "todo"
    tip = esc(text or "not yet")
    return f'<li class="{cls}" title="{tip}"><b>{mark}</b> {both(label_he, label_en)}</li>'


def card(d, uses):
    folder = d["_dir"]
    photos = d.get("photos", {})
    pics = [
        v for k, v in photos.items() if k not in ("symbol", "footprint") and (folder / v).exists()
    ]
    status = d.get("status", {})
    model = d.get("model") or {}
    has_model = bool(model.get("boxes") or model.get("cylinders"))
    cat = d.get("category", "Other")
    words = " ".join(
        [
            d["name"],
            d["id"],
            cat,
            d.get("description", ""),
            " ".join(p[1] for p in d.get("pins", [])),
        ]
    ).lower()
    loc = d.get("location") or "?"
    qty = d.get("quantity")
    where = esc(loc) + (f" · {qty}" if qty is not None else "")
    img = (
        f'<img src="{esc(rel(folder / pics[0]))}" alt="{esc(d["name"])}" loading="lazy">'
        if pics
        else '<div class="noimg">no photo yet</div>'
    )
    used = uses.get(d["id"], [])
    used_html = (
        " ".join(
            f'<a class="chip" href="../examples/{esc(f)}/index.html">{t(name)}</a>'
            for f, name in used
        )
        if used
        else f'<span class="muted">{both("עוד לא על לוח", "not on a board yet")}</span>'
    )
    h = [
        f'<article class="part" data-cat="{esc(cat)}" data-words="{esc(words)}" id="{esc(d["id"])}">',
        f'<div class="pic">{img}</div>',
        '<div class="body">',
        f'<span class="cat">{t(cat)}</span>',
        f"<h3>{t(d['name'])}</h3>",
        f'<p class="desc">{t(first_sentence(d.get("description", "")))}</p>',
        f'<p class="where">{both("איפה", "Where")}: <b><bdi>{where}</bdi></b></p>',
        '<ul class="checks">',
        check_line("סימבול", "symbol", status.get("symbol")),
        check_line("פוטפרינט", "footprint", status.get("footprint")),
        check_line("מודל תלת-מימד", "3D model", status.get("3d_model") if has_model else ""),
        "</ul>",
        f'<p class="used">{both("על הלוחות", "On boards")}: {used_html}</p>',
        '<div class="actions">',
        f'<a class="btn" href="{esc(borrow_link(d))}">{both("אני רוצה אחד", "I want one")}</a>',
        "</div>",
        "<details>",
        f"<summary>{both('כל הפרטים', 'All the details')}</summary>",
        f'<p dir="auto">{esc(d.get("description", ""))}</p>',
    ]
    if len(pics) > 1:
        h.append(
            '<div class="gallery">'
            + "".join(
                f'<img src="{esc(rel(folder / p))}" alt="{esc(d["name"])}" loading="lazy">'
                for p in pics[1:]
            )
            + "</div>"
        )
    drawn = [
        (k, photos[k])
        for k in ("symbol", "footprint")
        if k in photos and (folder / photos[k]).exists()
    ]
    if drawn:
        h.append(
            '<div class="drawn">'
            + "".join(
                f'<figure><img src="{esc(rel(folder / v))}" alt="{k}" loading="lazy">'
                f"<figcaption>{esc(k)}, {both('כפי ש-Fusion ציירה', 'as Fusion drew it')}</figcaption></figure>"
                for k, v in drawn
            )
            + "</div>"
        )
    pins = d.get("pins", [])
    if pins:
        h.append(f'<h4>{both("פינים", "Pins")}</h4><div class="tw"><table dir="ltr">')
        h.append("<tr><th>#</th><th>name</th><th>kind</th><th>note</th></tr>")
        for p in pins:
            n, name, kind, *note = p + [""] * (4 - len(p))
            h.append(
                f"<tr><td>{esc(str(n))}</td><td><b>{esc(name)}</b></td><td>{esc(kind)}</td><td>{esc(note[0])}</td></tr>"
            )
        h.append("</table></div>")
    dims = d.get("dimensions_mm", {})
    if dims:
        h.append(
            f'<h4>{both("מידות, ומאיפה כל אחת", "Dimensions, and where each came from")}</h4><ul class="dims" dir="ltr">'
        )
        for k, v in dims.items():
            val = v.get("value") if isinstance(v, dict) else v
            src = v.get("source", "") if isinstance(v, dict) else ""
            h.append(
                f'<li><b>{esc(k)}</b>: {esc(json.dumps(val))} mm <span class="muted">({esc(src)})</span></li>'
            )
        h.append("</ul>")
    fp = d.get("footprint", {})
    if fp:
        keys = (
            "type",
            "name",
            "per_row",
            "pitch",
            "row_spacing",
            "drill",
            "pad",
            "body",
            "body_diameter",
        )
        bits = ", ".join(f"{k} {fp[k]}" for k in keys if k in fp)
        h.append(f"<h4>{both('פוטפרינט', 'Footprint')}</h4><p><code>{esc(bits)}</code></p>")
        if fp.get("why"):
            h.append(f'<p class="muted" dir="auto">{esc(fp["why"])}</p>')
    if has_model:
        nb, nc = len(model.get("boxes", [])), len(model.get("cylinders", []))
        h.append(
            f"<h4>{both('מודל תלת-מימד', '3D model')}</h4><p>"
            + both(
                f"{nb} תיבות ו-{nc} גלילים, לכל מידה המקור שלה; ממנו נבנים הלוח בתלת-מימד והקופסה.",
                f"{nb} boxes and {nc} cylinders, every size with its source; the board in 3D and the case are built from it.",
            )
            + "</p>"
        )
    links = []
    if d.get("datasheet"):
        links.append(f'<a href="{esc(d["datasheet"])}">datasheet</a>')
    links.append(f'<a href="{esc(rel(folder / "part.json"))}">part.json</a>')
    for lbr in sorted(folder.glob("*.lbr")):
        links.append(f'<a href="{esc(rel(lbr))}">{esc(lbr.name)}</a>')
    h.append(f'<h4>{both("קבצים", "Files")}</h4><p class="files">{" · ".join(links)}</p>')
    if d.get("maker"):
        h.append(f'<p class="muted">{both("יצרן", "Maker")}: {t(d["maker"])}</p>')
    h += ["</details>", "</div>", "</article>"]
    return "\n".join(h)


CSS = """
:root { --bg:#f7f8fb; --panel:#fff; --ink:#17202e; --muted:#556173; --line:#dfe4ec; --accent:#c2410c;
  --accent-ink:#fff; --accent-soft:#fdebe0; --cool:#0a6b8f; --cool-soft:#e2f1f6; --ok:#15803d; --todo:#9aa3b2;
  --shadow:0 1px 2px rgba(16,24,40,.06),0 4px 16px rgba(16,24,40,.06); }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#0e131b; --panel:#161d28;
  --ink:#e9eef5; --muted:#a3afc0; --line:#273142; --accent:#f59e6b; --accent-ink:#2a1206; --accent-soft:#3a2416;
  --cool:#4cc9d9; --cool-soft:#11303a; --ok:#4ade80; --todo:#5b6577; --shadow:none; } }
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--ink); font-family:"Segoe UI","Heebo",Arial,sans-serif; font-size:16px; line-height:1.6; }
.he [lang="en"], .en [lang="he"] { display:none !important; }
a { color:var(--cool); }
.wrap { max-width:1120px; margin:0 auto; padding:0 16px; }
.top { position:sticky; top:0; z-index:10; background:color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter:blur(8px); border-bottom:1px solid var(--line); }
.top .wrap { display:flex; align-items:center; justify-content:space-between; gap:12px; height:56px; }
.brand { font-weight:700; display:flex; align-items:center; gap:10px; color:var(--ink); text-decoration:none; }
.brand-dot { width:22px; height:22px; border-radius:6px; background:var(--accent); }
.lang-switch { display:flex; border:1px solid var(--line); border-radius:999px; overflow:hidden; }
.lang-switch button { border:0; background:transparent; color:var(--muted); font:inherit; font-size:14px; padding:4px 14px; cursor:pointer; min-height:32px; }
.lang-switch button[aria-pressed="true"] { background:var(--accent); color:var(--accent-ink); }
.hero { padding:44px 0 20px; }
.hero h1 { font-size:38px; line-height:1.15; margin-bottom:10px; }
.hero p { font-size:19px; color:var(--muted); max-width:780px; }
.duo { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:16px; margin:22px 0 8px; }
.box { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:18px 20px; box-shadow:var(--shadow); }
.box.deal { background:var(--accent-soft); border-color:transparent; }
.box h2 { font-size:22px; margin-bottom:6px; }
.box ol { margin:8px 0 0; padding-inline-start:22px; }
.box li { margin:4px 0; }
.anatomy { font-family:Consolas,"Cascadia Code",ui-monospace,monospace; font-size:13.5px; background:var(--cool-soft);
  border-radius:10px; padding:10px 12px; margin-top:8px; direction:ltr; text-align:left; white-space:pre; overflow-x:auto; }
.bar { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:26px 0 14px; }
.bar input { flex:1 1 220px; min-height:40px; border:1px solid var(--line); border-radius:999px; padding:6px 16px;
  font:inherit; background:var(--panel); color:var(--ink); }
.chip, .bar button { display:inline-block; border:1px solid var(--line); background:var(--panel); color:var(--ink);
  border-radius:999px; padding:3px 12px; font:inherit; font-size:14px; text-decoration:none; cursor:pointer; }
.bar button[aria-pressed="true"] { background:var(--ink); color:var(--bg); border-color:var(--ink); }
.count { color:var(--muted); font-size:14px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:16px; margin-bottom:40px; align-items:start; }
.part { background:var(--panel); border:1px solid var(--line); border-radius:14px; overflow:hidden; box-shadow:var(--shadow);
  display:flex; flex-direction:column; }
.part[hidden] { display:none; }
.pic { aspect-ratio:4/3; background:#e9edf3; display:grid; place-items:center; overflow:hidden; }
.pic img { width:100%; height:100%; object-fit:cover; }
.noimg { color:var(--muted); }
.part .body { padding:14px 16px 16px; display:flex; flex-direction:column; gap:6px; flex:1; }
.cat { font-size:12px; font-weight:700; letter-spacing:.05em; text-transform:uppercase; color:var(--accent); }
.part h3 { font-size:18px; line-height:1.3; }
.desc { color:var(--muted); font-size:15px; }
.where, .used { font-size:14px; }
.checks { list-style:none; display:flex; flex-wrap:wrap; gap:6px 12px; font-size:14px; }
.checks .ok b { color:var(--ok); } .checks .todo { color:var(--todo); }
.actions { padding-top:6px; }
.btn { display:inline-block; background:var(--accent); color:var(--accent-ink); padding:7px 16px; border-radius:999px;
  text-decoration:none; font-weight:700; font-size:15px; }
details { border-top:1px solid var(--line); margin-top:8px; padding-top:8px; font-size:14.5px; }
summary { cursor:pointer; font-weight:700; color:var(--cool); }
details h4 { margin:12px 0 4px; font-size:15px; }
details p { margin:4px 0; }
.gallery, .drawn { display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:8px; margin:8px 0; }
.gallery img, .drawn img { width:100%; border-radius:8px; border:1px solid var(--line); background:#fff; }
figure figcaption { font-size:12.5px; color:var(--muted); }
.tw { overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:13.5px; }
th, td { padding:4px 8px; border-bottom:1px solid var(--line); text-align:start; vertical-align:top; }
th { background:var(--cool-soft); }
.dims { padding-inline-start:18px; }
.muted { color:var(--muted); }
code { font-family:Consolas,ui-monospace,monospace; font-size:13px; background:var(--cool-soft); padding:1px 5px; border-radius:5px; direction:ltr; unicode-bidi:embed; }
footer { padding:24px 0 40px; color:var(--muted); font-size:14px; border-top:1px solid var(--line); }
@media (max-width:600px) { .hero h1 { font-size:30px; } }
"""

JS = """
(function () {
  var root = document.documentElement, buttons = document.querySelectorAll("[data-set-lang]");
  function setLang(lang, remember) {
    root.classList.remove("he", "en"); root.classList.add(lang);
    root.setAttribute("lang", lang); root.setAttribute("dir", lang === "he" ? "rtl" : "ltr");
    buttons.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-set-lang") === lang ? "true" : "false"); });
    if (remember) { try { localStorage.setItem("fusion-lang", lang); } catch (e) {} }
  }
  var wanted = null;
  try { wanted = localStorage.getItem("fusion-lang"); } catch (e) {}
  setLang(wanted || "he", false);
  buttons.forEach(function (b) { b.addEventListener("click", function () { setLang(b.getAttribute("data-set-lang"), true); }); });

  var q = document.getElementById("q"), cats = document.querySelectorAll("[data-cat-filter]"), cat = "";
  var cards = document.querySelectorAll(".part"), count = document.getElementById("count");
  function apply() {
    var words = (q.value || "").toLowerCase().trim().split(/\\s+/).filter(Boolean), shown = 0;
    cards.forEach(function (c) {
      var ok = (!cat || c.getAttribute("data-cat") === cat) &&
        words.every(function (w) { return c.getAttribute("data-words").indexOf(w) >= 0; });
      c.hidden = !ok; if (ok) shown++;
    });
    count.textContent = shown + " / " + cards.length;
  }
  q.addEventListener("input", apply);
  cats.forEach(function (b) {
    b.addEventListener("click", function () {
      cat = b.getAttribute("data-cat-filter");
      cats.forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      apply();
    });
  });
  apply();
})();
"""


def page():
    ps = parts()
    uses = used_in()
    owners = sorted({p["_owner"] for p in ps})
    cats = sorted({p.get("category", "Other") for p in ps})
    who = ", ".join(o.replace("_", " ").title() for o in owners)
    anatomy = (
        "library/&lt;your_name&gt;/&lt;part&gt;/\n"
        "  part.json     what it is, where it lives, pins, footprint,\n"
        "                every size with its source, status, 3D model\n"
        "  photos/       your photos, upright, no metadata\n"
        "  &lt;part&gt;.lbr    the Fusion library, generated from part.json\n"
        "  fusion/       the symbol and footprint as Fusion drew them"
    )
    h = [
        "<!DOCTYPE html>",
        '<html lang="he" dir="rtl" class="he">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "<title>Part library | Fusion 360 BKM</title>",
        '<meta name="description" content="Real electronic parts from a real shelf, each a full library cell: '
        'photos, pins, footprint, symbol and 3D model, checked in Fusion. Take one, give back two.">',
        f"<style>{CSS}</style>",
        "</head>",
        "<body>",
        '<header class="top"><div class="wrap">',
        '<a class="brand" href="../index.html"><span class="brand-dot"></span><span>Fusion 360 BKM</span></a>',
        '<div class="lang-switch" role="group" aria-label="Language / שפה">',
        '<button type="button" data-set-lang="he" aria-pressed="true">עברית</button>',
        '<button type="button" data-set-lang="en" aria-pressed="false">English</button>',
        "</div></div></header>",
        "<main>",
        '<div class="hero"><div class="wrap">',
        "<h1>"
        + both(
            "ספריית הרכיבים: חלקים אמיתיים מהמדף", "The part library: real parts from a real shelf"
        )
        + "</h1>",
        "<p>"
        + both(
            f"{len(ps)} רכיבים של {esc(who)}. כל אחד הוא תא ספרייה שלם: תמונות, פינים, פוטפרינט וסימבול שנבדקו ב-Fusion, ומודל תלת-מימד. מכאן נבנים הלוחות והקופסאות בדוגמאות.",
            f"{len(ps)} parts of {esc(who)}'s. Each is a full library cell: photos, pins, a footprint and a symbol checked in Fusion, and a 3D model. The example boards and their cases are built from them.",
        )
        + "</p>",
        '<div class="duo">',
        '<div class="box deal">',
        "<h2>" + both("לוקחים אחד, מחזירים שניים", "Take one, give back two") + "</h2>",
        "<p>"
        + both(
            "צריכים רכיב עכשיו? אין צורך לחכות חודש ל-AliExpress. קחו מהמדף שלי, והזמינו שניים שיחזרו אליי כשיגיעו. הרכיבים זולים, והמדף רק גדל.",
            "Need a part now? No need to wait a month for AliExpress. Take it from my shelf, and order two that come back to me when they arrive. The parts are cheap, and the shelf only grows.",
        )
        + "</p>",
        "<ol>",
        "<li>" + both("מוצאים את הרכיב למטה.", "Find the part below.") + "</li>",
        "<li>"
        + both(
            f'לוחצים "אני רוצה אחד" (נפתח מייל לאבי), או כותבים אליו: <a href="mailto:{OWNER_MAIL}"><bdi>{OWNER_MAIL}</bdi></a>.',
            f'Click "I want one" (it opens an email to Avi), or write to <a href="mailto:{OWNER_MAIL}">{OWNER_MAIL}</a>.',
        )
        + "</li>",
        "<li>"
        + both(
            "לוקחים אותו היום, מזמינים שניים, ומביאים אותם כשהם מגיעים.",
            "Take it today, order two, and bring them when they arrive.",
        )
        + "</li>",
        "</ol>",
        "<p>"
        + both(
            "אבי גר בצפון הארץ: אם נוח לכם להגיע ולאסוף, בשמחה. אם לא, קנו את הרכיב ברשת.",
            "Avi lives in the north of Israel: if you can come and pick it up, you are welcome. If not, buy the part online.",
        )
        + "</p></div>",
        '<div class="box">',
        "<h2>" + both("ככה נראית ספרייה", "What a library looks like") + "</h2>",
        "<p>"
        + both(
            'לכל משתמש ספרייה משלו, במאגר שלו. זו של אבי פתוחה לכולם, כדוגמה. בצ\'אט אומרים "הוסף רכיב לספרייה שלי" ומראים לו את הרכיב:',
            'Every user keeps their own library, in their own repository. Avi\'s is public, as an example. In the chat, say "add a part to my library" and show it the part:',
        )
        + "</p>",
        f'<div class="anatomy">{anatomy}</div>',
        f'<p style="margin-top:8px"><a href="README.md">library/README.md</a> · <a href="../examples/12_tiny_arcade/index.html">{both("לוח שנבנה מהספרייה: Tiny Arcade", "A board built from it: Tiny Arcade")}</a></p>',
        "</div></div>",
        '<div class="bar">',
        '<input id="q" type="search" placeholder="search: esp32, button, i2c, gnd ..." aria-label="search">',
        '<button type="button" data-cat-filter="" aria-pressed="true">'
        + both("הכול", "All")
        + "</button>",
    ]
    h += [
        f'<button type="button" data-cat-filter="{esc(c)}" aria-pressed="false">{t(c)}</button>'
        for c in cats
    ]
    h += ['<span class="count" id="count"></span>', "</div>", '<div class="grid">']
    h += [card(p, uses) for p in ps]
    h += [
        "</div>",
        "</div></div>",
        "</main>",
        '<footer><div class="wrap">',
        both(
            "הדף נכתב מקבצי הספרייה עצמם (<code>python scripts\\library_page.py</code>); אף מילה לא מוקלדת בו ביד.",
            "Written from the library's own files (<code>python scripts\\library_page.py</code>); nothing on it is typed by hand.",
        ),
        f' · <a href="{REPO}">{REPO.split("//")[1]}</a>',
        "</div></footer>",
        f"<script>{JS}</script>",
        "</body>",
        "</html>",
    ]
    return "\n".join(h) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--check", action="store_true", help="exit 1 if library/index.html is not current"
    )
    a = ap.parse_args(argv)
    text = page()
    if a.check:
        current = OUT.exists() and OUT.read_text(encoding="utf-8").replace("\r\n", "\n") == text
        print(
            "library/index.html is current"
            if current
            else "library/index.html is stale: run library_page.py"
        )
        return 0 if current else 1
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(text) // 1024} KB, {text.count('<article')} parts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
