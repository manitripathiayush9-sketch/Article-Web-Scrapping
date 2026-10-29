const form = document.getElementById("search-form");
const message = document.getElementById("message");
const results = document.getElementById("results");
const saved = document.getElementById("saved");
const button = document.getElementById("search-button");

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[char]);
}

function showMessage(text, type = "") {
  message.textContent = text;
  message.className = type;
}

function renderResults(articles) {
  results.innerHTML = "";

  if (!articles.length) {
    results.textContent = "No articles could be extracted. Try another search.";
    return;
  }

  for (const article of articles) {
    const card = document.createElement("article");
    card.className = "card";

    card.innerHTML = `
      <small>${escapeHTML(article.section || "News")}
        · ${Number(article.word_count || 0)} words
      </small>
      <h3>${escapeHTML(article.title)}</h3>
      <p>${escapeHTML(article.preview || "")}</p>
      <a href="/download/${encodeURIComponent(article.filename)}">
        Download TXT ↓
      </a>
      <a href="${escapeHTML(article.url)}"
         target="_blank" rel="noopener noreferrer">
        Original article ↗
      </a>
    `;

    results.appendChild(card);
  }
}

async function loadSaved() {
  saved.textContent = "Loading saved articles...";

  try {
    const response = await fetch("/api/articles");
    const data = await response.json();

    saved.innerHTML = "";

    if (!response.ok || !data.articles.length) {
      saved.textContent = "No saved articles yet.";
      return;
    }

    for (const article of data.articles.slice(0, 30)) {
      const row = document.createElement("div");
      row.className = "saved-row";

      row.innerHTML = `
        <div>
          <strong>${escapeHTML(article.title)}</strong>
          <small>${escapeHTML(article.filename)}</small>
        </div>
        <a class="download-link"
           href="/download/${encodeURIComponent(article.filename)}">
          Download
        </a>
      `;

      saved.appendChild(row);
    }
  } catch {
    saved.textContent = "Could not load saved articles.";
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();

  const query = document.getElementById("query").value.trim();
  const section = document.getElementById("section").value;
  const limit = Number(document.getElementById("limit").value);

  if (!query && !section) {
    showMessage("Enter a keyword or choose a section.", "error");
    return;
  }

  button.disabled = true;
  button.textContent = "Searching...";
  showMessage("Fetching and extracting articles...");
  results.textContent = "Please wait...";

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({query, section, limit})
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Search failed.");
    }

    renderResults(data.articles || []);
    document.getElementById("count").textContent =
      `(${data.count})`;

    showMessage(data.message, "success");
    await loadSaved();
  } catch (error) {
    showMessage(error.message, "error");
    results.textContent = "Search unsuccessful.";
  } finally {
    button.disabled = false;
    button.textContent = "Search and extract →";
  }
});

document.getElementById("refresh").addEventListener(
  "click", loadSaved
);

loadSaved();