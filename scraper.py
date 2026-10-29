from dotenv import load_dotenv
load_dotenv()
import os
import re
import csv
import io
import json
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


API_URL = "https://content.guardianapis.com/search"


class ArticleScraper:
    def __init__(self, output_dir="Saved_Articles"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.api_key = os.getenv("GUARDIAN_API_KEY", "").strip()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ArticleWebScrapingStudentProject/1.0"
        })

    def discover(self, query="", section="", limit=5):
        if not self.api_key:
            raise ValueError(
                "GUARDIAN_API_KEY is missing. Set your Guardian API key."
            )

        params = {
            "api-key": self.api_key,
            "page-size": limit,
            "order-by": "newest",
            "show-fields": "headline,trailText,bodyText,byline"
        }

        if query:
            params["q"] = query
        if section:
            params["section"] = section

        response = self.session.get(
            API_URL, params=params, timeout=20
        )
        response.raise_for_status()

        payload = response.json()
        if payload.get("response", {}).get("status") != "ok":
            raise RuntimeError("Guardian API returned an error.")

        return payload.get("response", {}).get("results", [])

    def extract(self, url, fallback_title):
        response = self.session.get(url, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        title_node = soup.select_one(
            "article h1, main h1, h1"
        )
        title = (
            title_node.get_text(" ", strip=True)
            if title_node else fallback_title
        )

        body = soup.select_one(
            '[data-gu-name="body"], '
            ".article-body-commercial-selector, article"
        )

        if body:
            paragraphs = [
                p.get_text(" ", strip=True)
                for p in body.find_all("p")
            ]
        else:
            paragraphs = [
                p.get_text(" ", strip=True)
                for p in soup.select("main p")
            ]

        paragraphs = [
            p for p in paragraphs if p and len(p) > 25
        ]
        return title, "\n\n".join(paragraphs)

    @staticmethod
    def slug(text):
        result = re.sub(
            r"[^a-zA-Z0-9]+", "_", text.lower()
        ).strip("_")
        return (result or "article")[:60]

    def search_and_save(self, query="", section="", limit=5):
        items = self.discover(query, section, limit)
        saved = []

        for item in items:
            url = item.get("webUrl")
            fields = item.get("fields") or {}

            if not url:
                continue

            fallback_title = (
                fields.get("headline")
                or item.get("webTitle")
                or "Untitled article"
            )

            try:
                title, body = self.extract(url, fallback_title)
            except requests.RequestException:
                title, body = fallback_title, ""

            # API text is a fallback if page HTML changes.
            if not body:
                body = (
                    fields.get("bodyText")
                    or fields.get("trailText")
                    or ""
                ).strip()

            if not body:
                continue

            timestamp = datetime.now(timezone.utc).strftime(
                "%Y%m%d_%H%M%S_%f"
            )
            filename = (
                f"{timestamp}_{self.slug(title)}.txt"
            )
            filepath = os.path.join(
                self.output_dir, filename
            )

            published = item.get("webPublicationDate", "")
            section_name = item.get("sectionName", "")

            with open(filepath, "w", encoding="utf-8") as file:
                file.write(title + "\n")
                file.write("=" * min(len(title), 90) + "\n\n")
                file.write(f"Source: The Guardian\n")
                file.write(f"URL: {url}\n")
                file.write(f"Published: {published}\n\n")
                file.write(body.strip() + "\n")

            saved.append({
                "title": title,
                "url": url,
                "published": published,
                "section": section_name,
                "filename": filename,
                "word_count": len(body.split()),
                "preview": body[:400]
            })

        return saved

    def list_saved_articles(self):
        results = []

        for filename in sorted(
            os.listdir(self.output_dir), reverse=True
        ):
            if not filename.endswith(".txt"):
                continue

            path = os.path.join(self.output_dir, filename)

            try:
                with open(path, encoding="utf-8") as file:
                    content = file.read()
            except OSError:
                continue

            results.append({
                "title": content.splitlines()[0]
                if content else filename,
                "filename": filename,
                "word_count": len(content.split())
            })

        return results

    def export_saved(self, kind):
        rows = []

        for filename in sorted(
            os.listdir(self.output_dir), reverse=True
        ):
            if not filename.endswith(".txt"):
                continue

            path = os.path.join(self.output_dir, filename)

            try:
                with open(path, encoding="utf-8") as file:
                    content = file.read()
            except OSError:
                continue

            lines = content.splitlines()
            title = lines[0] if lines else filename

            url_match = re.search(
                r"^URL:\s*(.+)$", content, re.MULTILINE
            )
            date_match = re.search(
                r"^Published:\s*(.*)$", content, re.MULTILINE
            )

            rows.append({
                "title": title,
                "filename": filename,
                "url": url_match.group(1) if url_match else "",
                "published": date_match.group(1) if date_match else "",
                "content": content
            })

        if kind == "json":
            return (
                json.dumps(rows, ensure_ascii=False, indent=2),
                "application/json; charset=utf-8",
                "json"
            )

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "title", "filename", "url", "published", "content"
            ]
        )
        writer.writeheader()
        writer.writerows(rows)

        return (
            output.getvalue(),
            "text/csv; charset=utf-8",
            "csv"
        )