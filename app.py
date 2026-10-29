import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from scraper import ArticleScraper

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "Saved_Articles")
scraper = ArticleScraper(OUTPUT_DIR)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "api_key_configured": bool(os.getenv("GUARDIAN_API_KEY"))
    })


@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json(silent=True) or {}

    query = str(data.get("query", "")).strip()
    section = str(data.get("section", "")).strip()

    try:
        limit = max(1, min(int(data.get("limit", 5)), 10))
    except (TypeError, ValueError):
        limit = 5

    if not query and not section:
        return jsonify({
            "error": "Enter a keyword or select a section."
        }), 400

    try:
        articles = scraper.search_and_save(query, section, limit)
        return jsonify({
            "count": len(articles),
            "articles": articles,
            "message": f"{len(articles)} article(s) processed."
        })
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("Article scraping failed")
        return jsonify({
            "error": "Scraping failed. Check your API key, internet connection and logs."
        }), 502


@app.route("/api/articles")
def articles_list():
    return jsonify({
        "articles": scraper.list_saved_articles()
    })


@app.route("/download/<path:filename>")
def download(filename):
    if (
        os.path.basename(filename) != filename
        or not filename.endswith(".txt")
    ):
        return jsonify({"error": "Invalid filename"}), 400

    return send_from_directory(
        OUTPUT_DIR, filename, as_attachment=True
    )


@app.route("/export/<kind>")
def export(kind):
    if kind not in ("json", "csv"):
        return jsonify({"error": "Use json or csv"}), 400

    content, content_type, extension = scraper.export_saved(kind)

    from flask import Response
    response = Response(content, content_type=content_type)
    response.headers["Content-Disposition"] = (
        f'attachment; filename="saved_articles.{extension}"'
    )
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)