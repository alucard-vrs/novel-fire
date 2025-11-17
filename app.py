from flask import (
    Flask,
    render_template,
    abort,
    request,
    redirect,
    url_for,
    flash,
    Response,
)
import requests
from bs4 import BeautifulSoup
from cachetools import TTLCache
import json
import os
import re
from urllib.parse import urlparse, urljoin
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://example.com").rstrip("/")

# --- Load novel list ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
novels_path = os.path.join(BASE_DIR, "novels.json")
static_media_dir = os.path.join(BASE_DIR, "static", "media")
os.makedirs(static_media_dir, exist_ok=True)

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

try:
    with open(novels_path, "r") as f:
        novels = json.load(f)
except FileNotFoundError:
    novels = [
        {
            "title": "Paragon Of Sin",
            "slug": "paragon-of-sin",
            "cover": "/static/media/paragon.jpg",
            "author": "Kevinascending",
            "total_chapters": 100,  # Set total chapters here
            "source_url": "https://freewebnovel.com/novel/paragon-of-sin",
            "summary": "The greatest sinner of them all fights the Heavenly Dao itself to grasp destiny.",
            "tags": [],
        }
    ]

# --- Cache (for chapters, 1 day) ---
cache = TTLCache(maxsize=200, ttl=86400)


def absolute_url(path: str) -> str:
    if not path:
        return SITE_BASE_URL
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urljoin(SITE_BASE_URL + "/", path.lstrip("/"))


@app.context_processor
def inject_globals():
    return {
        "site_base_url": SITE_BASE_URL,
        "absolute_url": absolute_url,
    }


def save_novels():
    with open(novels_path, "w") as f:
        json.dump(novels, f, indent=2)


def find_novel(slug):
    return next((n for n in novels if n["slug"] == slug), None)


def normalize_slug_fragment(raw_value):
    value = (raw_value or "").strip()
    if not value:
        raise ValueError("Please provide the novel name, slug, or URL.")

    if value.startswith("http"):
        parsed = urlparse(value)
        value = parsed.path or ""

    value = value.strip("/")
    if value.startswith("novel/"):
        value = value.split("/", 1)[1]

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    if not value:
        raise ValueError("Could not figure out the novel slug from the provided input.")
    return value


def fetch_novel_metadata(slug_fragment):
    slug_path = f"novel/{slug_fragment}"
    url = f"https://freewebnovel.com/{slug_path}"

    response = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    def get_meta(name):
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        return tag.get("content").strip() if tag and tag.get("content") else None

    title = get_meta("og:novel:novel_name")
    if not title:
        title_tag = soup.select_one(".m-desc h1.tit")
        title = title_tag.get_text(strip=True) if title_tag else slug_fragment.replace("-", " ").title()

    author = get_meta("og:novel:author") or "Unknown"
    cover_url = get_meta("og:image")
    summary_tag = soup.select_one(".m-desc .txt .inner") or soup.select_one(".m-desc .txt")
    summary_html = summary_tag.decode_contents().strip() if summary_tag else ""

    latest_chapter_url = get_meta("og:novel:lastest_chapter_url")
    total_chapters = None
    if latest_chapter_url:
        match = re.search(r"chapter-(\d+)", latest_chapter_url)
        if match:
            total_chapters = int(match.group(1))

    genres = []
    for item in soup.select(".item"):
        icon = item.find("span", class_=re.compile("glyphicon"))
        if not icon:
            continue
        classes = " ".join(icon.get("class", []))
        if "glyphicon-th-list" in classes:
            right = item.find("div", class_="right")
            if right:
                genres = [a.get_text(strip=True) for a in right.select("a") if a.get_text(strip=True)]
            break

    return {
        "title": title,
        "author": author,
        "cover_url": urljoin(url, cover_url) if cover_url else None,
        "summary": summary_html,
        "total_chapters": total_chapters,
        "source_url": url,
        "genres": genres,
    }


def ensure_cover_image(cover_url, slug_fragment):
    if not cover_url:
        return "/static/media/paragon.jpg"

    filename = f"{slug_fragment}.jpg"
    local_path = os.path.join(static_media_dir, filename)
    public_path = f"/static/media/{filename}"

    try:
        resp = requests.get(cover_url, headers=REQUEST_HEADERS, timeout=15, stream=True)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    except Exception as exc:
        print(f"⚠️ Failed to download cover: {exc}")
        return cover_url

    return public_path


def fetch_chapter_preview(slug, chapter_number=1):
    cache_key = f"preview_{slug}_{chapter_number}"
    if cache_key in cache:
        return cache[cache_key]

    url = f"https://freewebnovel.com/novel/{slug}/chapter-{chapter_number}"
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
        response.raise_for_status()
    except Exception as exc:
        print(f"⚠️ Failed to fetch preview for {slug}: {exc}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    title_tag = soup.select_one("h1")
    content_tag = soup.select_one(".chapter-content") or soup.select_one(".txt") or soup.select_one(".content")
    if not title_tag or not content_tag:
        return None

    paragraphs = [p.get_text(" ", strip=True) for p in content_tag.find_all("p")]
    snippet = " ".join(filter(None, paragraphs))
    if len(snippet) > 260:
        snippet = snippet[:260].rsplit(" ", 1)[0] + "…"

    data = {
        "title": title_tag.get_text(strip=True),
        "snippet": snippet,
        "chapter_number": chapter_number,
    }
    cache[cache_key] = data
    return data


@app.after_request
def add_caching_headers(response):
    if response.direct_passthrough:
        return response
    if response.mimetype in {"text/html", "application/xml", "application/json"}:
        response.headers.setdefault("Cache-Control", "public, max-age=300")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response

# --- Homepage ---
@app.route("/")
def homepage():
    return render_template("index.html", novels=novels)


@app.route("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {absolute_url('/sitemap.xml')}",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    urls = [
        {
            "loc": absolute_url(url_for("homepage")),
            "lastmod": datetime.utcnow().date().isoformat(),
        }
    ]

    for novel in novels:
        urls.append(
            {
                "loc": absolute_url(url_for("novel_page", slug=novel["slug"])),
                "lastmod": datetime.utcnow().date().isoformat(),
            }
        )

    xml = render_template("sitemap.xml", urls=urls)
    return Response(xml, mimetype="application/xml")


@app.route("/add-novel", methods=["POST"])
def add_novel():
    user_value = request.form.get("novel_name", "")
    try:
        slug_fragment = normalize_slug_fragment(user_value)
        metadata = fetch_novel_metadata(slug_fragment)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("homepage"))
    except Exception as exc:
        flash(f"Could not fetch the novel: {exc}", "error")
        return redirect(url_for("homepage"))

    cover_path = ensure_cover_image(metadata.get("cover_url"), slug_fragment)
    novel_payload = {
        "title": metadata.get("title"),
        "slug": slug_fragment,
        "cover": cover_path,
        "author": metadata.get("author") or "Unknown",
        "source_url": metadata.get("source_url"),
        "total_chapters": metadata.get("total_chapters") or 100,
        "summary": metadata.get("summary", ""),
        "tags": metadata.get("genres") or [],
    }

    existing = find_novel(slug_fragment)
    if existing:
        existing.update(novel_payload)
        message = f"Updated '{novel_payload['title']}'"
    else:
        novels.append(novel_payload)
        message = f"Added '{novel_payload['title']}'"

    save_novels()
    flash(f"{message}. Ready to read!", "success")
    return redirect(url_for("novel_page", slug=slug_fragment))


# --- Novel page with grouped chapters ---
@app.route("/novel/<path:slug>")
def novel_page(slug):
    novel = find_novel(slug)
    if not novel:
        abort(404)

    total_chapters = novel.get("total_chapters", 100)
    group_size = 10

    grouped_chapters = [
        {"start": i, "end": min(i + group_size - 1, total_chapters)}
        for i in range(1, total_chapters + 1, group_size)
    ]

    preview_data = None
    if grouped_chapters:
        preview_data = fetch_chapter_preview(slug, grouped_chapters[0]["start"])

    return render_template(
        "novel.html",
        novel=novel,
        grouped_chapters=grouped_chapters,
        preview=preview_data,
    )


# --- Dynamic grouped chapter page ---
@app.route("/novel/<path:slug>/group/<int:start_chap>")
def read_group(slug, start_chap):
    novel = find_novel(slug)
    if not novel:
        abort(404)

    total_chapters = novel.get("total_chapters", 100)
    group_size = 10
    end_chap = min(start_chap + group_size - 1, total_chapters)

    chapters_content = []

    for chapter_number in range(start_chap, end_chap + 1):
        cache_key = f"{slug}_{chapter_number}"
        if cache_key in cache:
            title, content = cache[cache_key]
        else:
            url = f"https://freewebnovel.com/novel/{slug}/chapter-{chapter_number}"
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                r = requests.get(url, headers=headers, timeout=10)
                r.raise_for_status()
            except Exception as e:
                print(f"⚠️ Failed to fetch chapter {chapter_number}: {e}")
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            title_tag = soup.select_one("h1")
            content_tag = soup.select_one(".chapter-content") or soup.select_one(".txt") or soup.select_one(".content")
            if not title_tag or not content_tag:
                continue

            title = title_tag.get_text(strip=True)
            content = content_tag.decode_contents()
            cache[cache_key] = (title, content)

        chapters_content.append({"title": title, "content": content})

    prev_group = start_chap - group_size if start_chap - group_size > 0 else None
    next_group = start_chap + group_size if start_chap + group_size <= total_chapters else None

    return render_template(
        "group_chapter.html",
        novel=novel,
        chapters=chapters_content,
        prev_group=prev_group,
        next_group=next_group,
        start_chap=start_chap,
        end_chap=end_chap,
        group_size=group_size,
    )


# --- Test route ---
@app.route("/test-chapter")
def test_chapter():
    return "✅ Chapter route is reachable!"


if __name__ == "__main__":
    print("🚀 Flask app running at http://127.0.0.1:5000/")
    app.run(debug=True)
