#!/usr/bin/env python3
"""Generate a hierarchical HTML photo gallery from a NASA images catalog."""

import argparse
import html
import json
import urllib.parse
from pathlib import Path

_RENDERABLE = {"jpg", "jpeg", "png", "gif", "webp"}
_TIF = {"tif", "tiff"}
_VIDEO = {"mp4", "mov", "avi", "mkv", "m4v"}
_AUDIO = {"mp3", "wav", "m4a", "ogg", "flac"}


def load_metadata(nasa_id_dir: Path) -> dict:
    meta_path = nasa_id_dir / "metadata.json"
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def scan_nasa_id_dir(nasa_id_dir: Path) -> dict:
    meta = load_metadata(nasa_id_dir)

    orig_file = None
    ext = ""
    for entry in sorted(nasa_id_dir.iterdir(), key=lambda e: e.name):
        if entry.is_file() and not entry.name.endswith(".part") and entry.name != "metadata.json":
            orig_file = entry.name
            ext = entry.suffix.lstrip(".").lower()
            break

    title = meta.get("AVAIL:Title", "")
    description = meta.get("AVAIL:Description", "")
    description_508 = meta.get("AVAIL:Description508", "") or title
    date_created = meta.get("AVAIL:DateCreated", "")
    center = meta.get("AVAIL:Center", "")
    keywords = meta.get("AVAIL:Keywords", [])
    if not isinstance(keywords, list):
        keywords = []
    keywords = [str(k) for k in keywords]
    media_type = meta.get("AVAIL:MediaType", "")

    return {
        "nasa_id": nasa_id_dir.name,
        "rel_dir": nasa_id_dir.name,
        "orig_file": orig_file,
        "ext": ext,
        "title": title,
        "description": description,
        "description_508": description_508,
        "date_created": date_created,
        "center": center,
        "keywords": keywords,
        "is_tif": ext in _TIF,
        "is_video": ext in _VIDEO or media_type == "video",
        "is_audio": ext in _AUDIO or media_type == "audio",
    }


def _escape(s: str) -> str:
    return html.escape(s)


def _quote(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def render_page(title: str, body: str, breadcrumb: str = "") -> str:
    t = _escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: sans-serif; background: #111; color: #eee; padding: 1.5rem; }}
nav {{ margin-bottom: 1rem; font-size: 0.9rem; color: #aaa; }}
nav a {{ color: #7af; text-decoration: none; }}
nav a:hover {{ text-decoration: underline; }}
nav span {{ color: #eee; }}
h1 {{ margin-bottom: 1rem; font-size: 1.5rem; }}
ul {{ list-style: none; padding: 0; }}
ul li {{ margin: 0.5rem 0; font-size: 1rem; }}
ul li a {{ color: #7af; text-decoration: none; }}
ul li a:hover {{ text-decoration: underline; }}
.count {{ color: #888; font-size: 0.85rem; margin-left: 0.5rem; }}
.gallery {{ display: flex; flex-wrap: wrap; gap: 1rem; }}
.card {{ width: 320px; background: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 0.75rem; overflow: hidden; }}
.card-media {{ text-align: center; margin-bottom: 0.6rem; min-height: 60px; display: flex; align-items: center; justify-content: center; flex-direction: column; }}
.card-media img {{ max-width: 300px; max-height: 300px; object-fit: contain; display: block; }}
.card-media a {{ color: #7af; font-size: 0.9rem; }}
.card-note {{ color: #888; font-size: 0.85rem; font-style: italic; margin-bottom: 0.3rem; }}
.card h3 {{ font-size: 0.95rem; margin-bottom: 0.3rem; word-break: break-word; }}
.meta {{ font-size: 0.8rem; color: #999; margin-bottom: 0.3rem; }}
.desc {{ font-size: 0.8rem; color: #ccc; margin-bottom: 0.3rem; }}
details summary {{ font-size: 0.8rem; color: #7af; cursor: pointer; margin-bottom: 0.2rem; }}
details p {{ font-size: 0.8rem; color: #ccc; }}
.keywords {{ display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.4rem; }}
.kw {{ background: #2a2a2a; border: 1px solid #444; border-radius: 3px; font-size: 0.7rem; padding: 0.1rem 0.35rem; color: #bbb; }}
</style>
</head>
<body>
{breadcrumb}
<h1>{t}</h1>
{body}
</body>
</html>"""


def render_breadcrumb(parts: list[tuple[str, str]]) -> str:
    if not parts:
        return ""
    items = []
    for i, (label, href) in enumerate(parts):
        if i == len(parts) - 1:
            items.append(f"<span>{_escape(label)}</span>")
        else:
            items.append(f'<a href="{_escape(href)}">{_escape(label)}</a>')
    return "<nav>" + " / ".join(items) + "</nav>"


def render_card(item: dict) -> str:
    nasa_id = item["nasa_id"]
    orig_file = item["orig_file"]
    title = _escape(item["title"] or nasa_id)
    alt = _escape(item["description_508"] or item["title"] or nasa_id)
    date_created = _escape(item["date_created"])
    center = _escape(item["center"])
    description = item["description"]
    keywords = item["keywords"]

    if orig_file is None:
        media_html = '<span class="card-note">Media file not available</span>'
    else:
        href = urllib.parse.quote(item["rel_dir"], safe="/") + "/" + _quote(orig_file)
        if item["ext"] in _RENDERABLE:
            media_html = (
                f'<a href="{href}" target="_blank">'
                f'<img src="{href}" alt="{alt}" loading="lazy">'
                f"</a>"
            )
        elif item["is_tif"]:
            media_html = (
                f'<span class="card-note">TIFF — not browser-renderable</span>'
                f'<a href="{href}" download>Download TIFF</a>'
            )
        elif item["is_video"]:
            media_html = (
                f'<span class="card-note">Video file</span>'
                f'<a href="{href}">View / Download</a>'
            )
        elif item["is_audio"]:
            media_html = (
                f'<span class="card-note">Audio file</span>'
                f'<a href="{href}">Download Audio</a>'
            )
        else:
            media_html = (
                f'<span class="card-note">{_escape(orig_file)}</span>'
                f'<a href="{href}">Download</a>'
            )

    if len(description) > 300:
        short = _escape(description[:300]) + "..."
        full = _escape(description)
        desc_html = (
            f'<p class="desc">{short}</p>'
            f"<details><summary>Read more</summary><p>{full}</p></details>"
        )
    elif description:
        desc_html = f'<p class="desc">{_escape(description)}</p>'
    else:
        desc_html = ""

    kw_html = ""
    if keywords:
        kw_tags = "".join(
            f'<span class="kw">{_escape(k)}</span>' for k in keywords[:10]
        )
        kw_html = f'<div class="keywords">{kw_tags}</div>'

    meta_parts = [p for p in [date_created, center] if p]
    meta_html = f'<p class="meta">{" &middot; ".join(meta_parts)}</p>' if meta_parts else ""

    return (
        f'<div class="card">'
        f'<div class="card-media">{media_html}</div>'
        f"<h3>{title}</h3>"
        f"{meta_html}"
        f"{desc_html}"
        f"{kw_html}"
        f"</div>"
    )


def render_gallery_page(title: str, items: list[dict], breadcrumb: str) -> str:
    count = len(items)
    s = "s" if count != 1 else ""
    count_line = f'<p style="margin-bottom:1rem;color:#999">{count} item{s}</p>'
    cards = "\n".join(render_card(item) for item in items)
    body = f'{count_line}<div class="gallery">{cards}</div>'
    return render_page(title, body, breadcrumb)


def render_index_page(title: str, links: list[tuple[str, str, int]], breadcrumb: str) -> str:
    def li(label: str, href: str, count: int) -> str:
        s = "s" if count != 1 else ""
        return (
            f'<li><a href="{_escape(href)}">{_escape(label)}</a>'
            f'<span class="count">({count} item{s})</span></li>'
        )

    items_html = "".join(li(label, href, count) for label, href, count in links)
    return render_page(title, f"<ul>{items_html}</ul>", breadcrumb)


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_day_gallery(day_dir: Path) -> int:
    year = day_dir.parent.parent.name
    month = day_dir.parent.name
    day = day_dir.name

    items = [
        scan_nasa_id_dir(entry)
        for entry in sorted(day_dir.iterdir(), key=lambda e: e.name)
        if entry.is_dir()
    ]

    breadcrumb = render_breadcrumb([
        ("Catalog", "../../../index.html"),
        (year, "../../index.html"),
        (f"{year}-{month}", "../index.html"),
        (day, ""),
    ])
    _write(day_dir / "index.html", render_gallery_page(day, items, breadcrumb))
    return len(items)


_MONTH_GALLERY_THRESHOLD = 100
_YEAR_GALLERY_THRESHOLD = 100


def _scan_month_items(month_dir: Path) -> list[tuple[Path, list[dict]]]:
    """Return (day_dir, items) pairs with rel_dir set relative to month_dir."""
    result = []
    for day_dir in sorted(month_dir.iterdir(), key=lambda e: e.name):
        if not day_dir.is_dir():
            continue
        items = [
            scan_nasa_id_dir(e)
            for e in sorted(day_dir.iterdir(), key=lambda e: e.name)
            if e.is_dir()
        ]
        for item in items:
            item["rel_dir"] = f"{day_dir.name}/{item['nasa_id']}"
        result.append((day_dir, items))
    return result


def write_month_index(month_dir: Path) -> int:
    year = month_dir.parent.name
    month = month_dir.name

    day_items = _scan_month_items(month_dir)
    all_items = [item for _, items in day_items for item in items]

    breadcrumb = render_breadcrumb([
        ("Catalog", "../../index.html"),
        (year, "../index.html"),
        (month, ""),
    ])

    if len(all_items) < _MONTH_GALLERY_THRESHOLD:
        # Small month — one flat gallery, no day sub-pages needed.
        _write(month_dir / "index.html", render_gallery_page(f"{year} / {month}", all_items, breadcrumb))
    else:
        # Large month — write individual day galleries and an index linking to them.
        links = []
        for day_dir, items in day_items:
            write_day_gallery(day_dir)
            links.append((day_dir.name, f"{day_dir.name}/index.html", len(items)))
        _write(month_dir / "index.html", render_index_page(f"{year} / {month}", links, breadcrumb))

    return len(all_items)


def write_year_index(year_dir: Path) -> int:
    year = year_dir.name

    # Scan all months up front so we can decide which layout to use.
    month_items: list[tuple[Path, list[dict]]] = []
    for month_dir in sorted(year_dir.iterdir(), key=lambda e: e.name):
        if not month_dir.is_dir():
            continue
        items = [item for _, day_items in _scan_month_items(month_dir) for item in day_items]
        for item in items:
            item["rel_dir"] = f"{month_dir.name}/{item['rel_dir']}"
        month_items.append((month_dir, items))

    all_items = [item for _, items in month_items for item in items]

    breadcrumb = render_breadcrumb([
        ("Catalog", "../index.html"),
        (year, ""),
    ])

    if len(all_items) < _YEAR_GALLERY_THRESHOLD:
        # Small year — one flat gallery, no month/day sub-pages needed.
        _write(year_dir / "index.html", render_gallery_page(year, all_items, breadcrumb))
    else:
        # Large year — write individual month indexes and link to them.
        links = []
        for month_dir, items in month_items:
            write_month_index(month_dir)
            links.append((month_dir.name, f"{month_dir.name}/index.html", len(items)))
        _write(year_dir / "index.html", render_index_page(year, links, breadcrumb))

    return len(all_items)


def write_unknown_gallery(unknown_dir: Path) -> int:
    items = [
        scan_nasa_id_dir(entry)
        for entry in sorted(unknown_dir.iterdir(), key=lambda e: e.name)
        if entry.is_dir()
    ]

    breadcrumb = render_breadcrumb([
        ("Catalog", "../index.html"),
        ("Unknown", ""),
    ])
    _write(unknown_dir / "index.html", render_gallery_page("Unknown Date", items, breadcrumb))
    return len(items)


def write_root_index(catalog: Path, years: list[str], year_counts: dict[str, int], unknown_count: int) -> None:
    links = [(year, f"{year}/index.html", year_counts[year]) for year in years]
    if unknown_count > 0:
        links.append(("Unknown", "unknown/index.html", unknown_count))
    _write(catalog / "index.html", render_index_page("NASA Images Catalog", links, ""))


def generate(catalog: Path) -> int:
    years: list[str] = []
    year_counts: dict[str, int] = {}

    for entry in sorted(catalog.iterdir(), key=lambda e: e.name):
        if not entry.is_dir() or entry.name == "unknown":
            continue
        count = write_year_index(entry)
        years.append(entry.name)
        year_counts[entry.name] = count

    unknown_count = 0
    unknown_dir = catalog / "unknown"
    if unknown_dir.is_dir():
        unknown_count = write_unknown_gallery(unknown_dir)

    write_root_index(catalog, years, year_counts, unknown_count)

    return sum(1 for _ in catalog.rglob("index.html"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HTML gallery from a catalog.")
    parser.add_argument("catalog", type=Path, help="Path to the catalog directory")
    args = parser.parse_args()

    if not args.catalog.is_dir():
        parser.error(f"not a directory: {args.catalog}")

    n = generate(args.catalog)
    print(f"wrote {n} index.html files")


if __name__ == "__main__":
    main()
