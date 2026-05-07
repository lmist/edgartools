#!/usr/bin/env python3
"""Generate docs/llms.txt from the MkDocs navigation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CONFIG = ROOT / "mkdocs.yml"
OUTPUT = DOCS / "llms.txt"


class MkDocsConfigLoader(yaml.SafeLoader):
    """Parse mkdocs.yml without importing MkDocs Material extension objects."""


def python_name(loader: MkDocsConfigLoader, tag_suffix: str, node: yaml.Node) -> str:
    return tag_suffix


MkDocsConfigLoader.add_multi_constructor("tag:yaml.org,2002:python/name:", python_name)


def flatten_nav(items: list[Any], section: str | None = None) -> list[tuple[str, str, str]]:
    pages: list[tuple[str, str, str]] = []
    for item in items:
        if isinstance(item, dict):
            for title, value in item.items():
                if isinstance(value, str):
                    pages.append((section or "Documentation", title, value))
                elif isinstance(value, list):
                    pages.extend(flatten_nav(value, title))
        elif isinstance(item, str):
            pages.append((section or "Documentation", item, item))
    return pages


def plain_text(markdown: str) -> str:
    markdown = re.sub(r"```.*?```", "", markdown, flags=re.S)
    markdown = re.sub(r"`([^`]*)`", r"\1", markdown)
    markdown = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", markdown)
    markdown = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", markdown)
    markdown = re.sub(r"<[^>]+>", "", markdown)
    markdown = re.sub(r"[*_>#-]+", " ", markdown)
    return " ".join(markdown.split())


def page_summary(path: str) -> str:
    source = DOCS / path
    if not source.exists() or source.suffix.lower() != ".md":
        return ""

    text = source.read_text(encoding="utf-8", errors="ignore")
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    for block in blocks:
        if block.startswith("---") or block.startswith("#"):
            continue
        summary = plain_text(block)
        if len(summary) >= 40:
            return summary[:220].rstrip() + ("..." if len(summary) > 220 else "")
    return ""


def public_url(site_url: str, path: str) -> str:
    if path == "index.md":
        return site_url
    if path.endswith(".md"):
        path = path[:-3] + "/"
    return site_url.rstrip("/") + "/" + path


def main() -> None:
    config = yaml.load(CONFIG.read_text(encoding="utf-8"), Loader=MkDocsConfigLoader)
    site_url = config.get("site_url", "https://lmist.github.io/edgartools/")
    site_name = config.get("site_name", "EdgarTools Documentation")
    description = config.get("site_description", "")
    pages = flatten_nav(config.get("nav", []))

    lines = [
        f"# {site_name}",
        "",
        f"> {description}",
        "",
        "This file maps the public EdgarTools documentation for language models and other automated readers.",
        "",
    ]

    current_section: str | None = None
    seen: set[str] = set()
    for section, title, path in pages:
        if path in seen:
            continue
        seen.add(path)
        if current_section != section:
            current_section = section
            lines.extend(["", f"## {section}", ""])
        summary = page_summary(path)
        suffix = f": {summary}" if summary else ""
        lines.append(f"- [{title}]({public_url(site_url, path)}){suffix}")

    OUTPUT.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(seen)} links")


if __name__ == "__main__":
    main()
