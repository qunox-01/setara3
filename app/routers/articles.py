import os

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.utils.markdown import list_articles, parse_article

router = APIRouter()
templates = Jinja2Templates(directory="templates")

ARTICLES_DIR = "content/articles"


@router.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request):
    articles = list_articles(ARTICLES_DIR)
    return templates.TemplateResponse(
        "blog/index.html",
        {"request": request, "articles": articles},
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_article(request: Request, slug: str):
    article_path = os.path.join(ARTICLES_DIR, f"{slug}.md")
    if not os.path.exists(article_path):
        raise HTTPException(status_code=404, detail="Article not found.")

    article = parse_article(article_path)
    all_articles = list_articles(ARTICLES_DIR)
    related = [a for a in all_articles if a.get("slug") != slug][:3]

    return templates.TemplateResponse(
        "blog/article.html",
        {"request": request, "article": article, "related": related},
    )
