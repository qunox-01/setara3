import os
from typing import List

import frontmatter
import markdown as md_lib


def parse_article(path: str) -> dict:
    """Parse a markdown file with YAML frontmatter. Returns metadata + rendered HTML."""
    with open(path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)

    content_html = md_lib.markdown(
        post.content,
        extensions=["extra", "codehilite", "toc"],
    )

    metadata = dict(post.metadata)
    # Ensure slug is set
    if "slug" not in metadata:
        metadata["slug"] = os.path.splitext(os.path.basename(path))[0]

    return {"metadata": metadata, "content_html": content_html}


def list_articles(directory: str) -> List[dict]:
    """List all markdown articles from a directory, sorted by date descending."""
    if not os.path.exists(directory):
        return []

    articles = []
    for filename in os.listdir(directory):
        if not filename.endswith(".md"):
            continue
        path = os.path.join(directory, filename)
        try:
            article = parse_article(path)
            articles.append(article["metadata"])
        except Exception:
            continue

    # Sort by date if available, newest first
    articles.sort(key=lambda a: str(a.get("date", "1970-01-01")), reverse=True)
    return articles
