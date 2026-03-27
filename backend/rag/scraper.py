"""
scraper.py — Crawls https://linear.app/docs and extracts page content.

Returns a list of dicts: { "url": str, "title": str, "content": str }

URL discovery uses a hardcoded list sourced from linear.app/sitemap.xml.
The docs index page is JS-rendered (Next.js), so BeautifulSoup cannot
discover links by crawling it directly.
"""

import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://linear.app"
REQUEST_DELAY = 0.5  # seconds between requests

# All /docs pages from linear.app/sitemap.xml (127 URLs as of 2025-03).
# Re-generate with: curl -s https://linear.app/sitemap.xml | grep -o 'linear.app/docs[^<"]*' | sort -u
_KNOWN_DOC_PATHS: list[str] = [
    "/docs/account-preferences",
    "/docs/agents-api-deprecated",
    "/docs/agents-in-linear",
    "/docs/ai-at-linear",
    "/docs/airbyte",
    "/docs/api-and-webhooks",
    "/docs/asks-web-forms",
    "/docs/assigning-issues",
    "/docs/audit-log",
    "/docs/beta-project-planning",
    "/docs/billing-and-plans",
    "/docs/board-layout",
    "/docs/changes-to-linears-pricing-plans",
    "/docs/changes-to-user-roles-when-upgrading-to-enterprise",
    "/docs/code-intelligence",
    "/docs/comment-on-issues",
    "/docs/conceptual-model",
    "/docs/configuring-workflows",
    "/docs/creating-issues",
    "/docs/custom-views",
    "/docs/customer-requests",
    "/docs/cycle-graph",
    "/docs/dashboards",
    "/docs/default-team-pages",
    "/docs/delete-archive-issues",
    "/docs/diffs",
    "/docs/discord",
    "/docs/display-options",
    "/docs/due-dates",
    "/docs/editing-issues",
    "/docs/editor",
    "/docs/estimates",
    "/docs/exporting-data",
    "/docs/favorites",
    "/docs/figma",
    "/docs/filters",
    "/docs/front",
    "/docs/get-the-app",
    "/docs/github",
    "/docs/github-enterprise-cloud-beta",
    "/docs/github-integration",
    "/docs/github-to-linear",
    "/docs/gitlab",
    "/docs/gong",
    "/docs/google-sheets",
    "/docs/gus-integration",
    "/docs/how-to-use-linear",
    "/docs/how-to-use-linear-large-scaling-companies",
    "/docs/how-to-use-linear-small-teams",
    "/docs/how-to-use-linear-startups-mid-size-companies",
    "/docs/import-issues",
    "/docs/inbox",
    "/docs/initiative-and-project-updates",
    "/docs/initiatives",
    "/docs/insights",
    "/docs/integration-directory",
    "/docs/intercom",
    "/docs/invite-members",
    "/docs/issue-documents",
    "/docs/issue-relations",
    "/docs/issue-templates",
    "/docs/jira",
    "/docs/jira-terminology-translated",
    "/docs/jira-to-linear",
    "/docs/joining-your-team-on-linear",
    "/docs/label-views",
    "/docs/labels",
    "/docs/linear-agent",
    "/docs/linear-asks",
    "/docs/linear-for-growth",
    "/docs/linear-for-product-managers",
    "/docs/login-methods",
    "/docs/making-the-most-of-linear",
    "/docs/making-the-most-of-linear-business",
    "/docs/mcp",
    "/docs/members-roles",
    "/docs/microsoft-teams",
    "/docs/my-issues",
    "/docs/notifications",
    "/docs/notion",
    "/docs/ops-and-marketing",
    "/docs/parent-and-sub-issues",
    "/docs/peek",
    "/docs/priority",
    "/docs/private-issue-sharing",
    "/docs/private-teams",
    "/docs/profile",
    "/docs/project-dependencies",
    "/docs/project-documents",
    "/docs/project-graph",
    "/docs/project-labels",
    "/docs/project-milestones",
    "/docs/project-notifications",
    "/docs/project-overview",
    "/docs/project-priority",
    "/docs/project-status",
    "/docs/project-templates",
    "/docs/projects",
    "/docs/pull-request-reviews",
    "/docs/pulse",
    "/docs/releases",
    "/docs/report-performance-issues",
    "/docs/salesforce",
    "/docs/saml-and-access-control",
    "/docs/scim",
    "/docs/search",
    "/docs/security",
    "/docs/security-and-access",
    "/docs/select-issues",
    "/docs/sentry",
    "/docs/sla",
    "/docs/slack",
    "/docs/start-guide",
    "/docs/sub-initiatives",
    "/docs/sub-teams",
    "/docs/team-issue-limit",
    "/docs/team-owner",
    "/docs/teams",
    "/docs/third-party-application-approvals",
    "/docs/timeline",
    "/docs/triage",
    "/docs/triage-intelligence",
    "/docs/triage-manage-unplanned-work",
    "/docs/update-cycles",
    "/docs/use-cycles",
    "/docs/user-views",
    "/docs/view-demos",
    "/docs/workspace-owner",
    "/docs/workspaces",
    "/docs/zapier",
    "/docs/zendesk",
]


def _get_soup(url: str, session: requests.Session) -> BeautifulSoup | None:
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    try:
        response = session.get(url, timeout=15)
    except requests.RequestException as e:
        print(f"  Request error for {url}: {e}")
        return None

    if response.status_code != 200:
        print(f"  Skipping {url} (status {response.status_code})")
        return None

    return BeautifulSoup(response.text, "html.parser")


def _discover_doc_urls() -> list[str]:
    """
    Return the full list of Linear docs URLs.

    The docs site is JS-rendered (Next.js), so link-crawling the index page
    only finds ~12 server-side-rendered links.  Instead we use a hardcoded
    list sourced directly from linear.app/sitemap.xml (127 URLs).
    """
    return [BASE_URL + path for path in _KNOWN_DOC_PATHS]


def _extract_content(soup: BeautifulSoup) -> tuple[str, str]:
    """
    Extract the page title and main body text from a BeautifulSoup object.
    Strips nav, header, footer, and sidebar elements before extracting text.

    Returns (title, content) as plain strings.
    """
    # Remove noisy structural elements
    for tag in soup.find_all(["nav", "header", "footer", "aside"]):
        tag.decompose()

    # Title: prefer <title> tag, fall back to first <h1>
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)

    # Content: prefer <main> or <article>, fall back to <body>
    content_root = soup.find("main") or soup.find("article") or soup.body
    if content_root is None:
        return title, ""

    # Join paragraphs with newlines to preserve structure
    text = content_root.get_text(separator="\n", strip=True)
    return title, text


def scrape_docs(limit: int | None = None) -> list[dict]:
    """
    Scrape all Linear docs pages.

    Args:
        limit: If set, scrape at most this many pages (useful for testing).

    Returns:
        List of dicts with keys: "url", "title", "content".
    """
    session = requests.Session()
    session.headers["User-Agent"] = (
        "DeflectAI-RAG-Scraper/1.0 (educational ingestion bot)"
    )

    print("Discovering doc URLs from sitemap...")
    doc_urls = _discover_doc_urls()

    if limit is not None:
        doc_urls = doc_urls[:limit]

    total = len(doc_urls)
    print(f"Found {total} doc URLs to scrape.\n")

    results: list[dict] = []

    for i, url in enumerate(doc_urls, start=1):
        print(f"Scraping ({i}/{total}): {url}")
        time.sleep(REQUEST_DELAY)

        soup = _get_soup(url, session)
        if soup is None:
            continue

        title, content = _extract_content(soup)

        if not content.strip():
            print(f"  Skipping {url} (no extractable content)")
            continue

        results.append({"url": url, "title": title, "content": content})

    print(f"\nScraping complete. {len(results)} pages collected.")
    return results
