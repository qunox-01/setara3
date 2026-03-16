import os
import re
from typing import List

import frontmatter
import markdown as md_lib


def _reading_time(text: str) -> int:
    """Estimate reading time in minutes at 200 wpm."""
    words = len(text.split())
    return max(1, round(words / 200))


def _extract_faq(content: str) -> list:
    """Extract Q&A pairs from the ## FAQ section of a markdown article."""
    parts = re.split(r'^## FAQ\s*$', content, flags=re.MULTILINE)
    if len(parts) < 2:
        return []
    faq_text = parts[1]
    # Stop at the next ## section if any
    faq_text = re.split(r'^## ', faq_text, flags=re.MULTILINE)[0]
    items = re.split(r'^### (.+)$', faq_text, flags=re.MULTILINE)
    faqs = []
    for i in range(1, len(items) - 1, 2):
        question = items[i].strip()
        answer = items[i + 1].strip()
        if question and answer:
            faqs.append({"question": question, "answer": answer})
    return faqs


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

    return {
        "metadata": metadata,
        "content_html": content_html,
        "reading_time": _reading_time(post.content),
        "faq_items": _extract_faq(post.content),
    }


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
