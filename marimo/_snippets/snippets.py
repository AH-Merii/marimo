# Copyright 2024 Marimo. All rights reserved.
from __future__ import annotations

from collections.abc import Awaitable, Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from marimo import _loggers
from marimo._ast.load import load_app
from marimo._config.manager import get_default_config_manager
from marimo._utils.paths import marimo_package_path

LOGGER = _loggers.marimo_logger()


@dataclass
class SnippetSection:
    id: str
    html: Optional[str] = None
    code: Optional[str] = None


@dataclass
class Snippet:
    title: str
    sections: list[SnippetSection]


@dataclass
class Snippets:
    snippets: list[Snippet]


async def read_snippets() -> Snippets:
    snippets: list[Snippet] = []

    for file in read_snippet_filenames_from_config():
        app = load_app(file)
        assert app is not None
        sections: list[SnippetSection] = []
        title = ""

        for cell in app._cell_manager.cells():
            if not cell:
                continue

            code = cell._cell.code
            if should_ignore_code(code):
                continue

            if is_markdown(code):
                if not title and "# " in code:
                    title = get_title_from_code(code)

                ret = cell.run()
                if isinstance(ret, Awaitable):
                    output, _defs = await ret
                else:
                    output, _defs = ret
                sections.append(
                    SnippetSection(html=output.text, id=cell._cell.cell_id)
                )
            else:
                sections.append(
                    SnippetSection(code=code, id=cell._cell.cell_id)
                )

        snippets.append(Snippet(title=title, sections=sections))

    return Snippets(
        snippets=sorted(snippets, key=lambda snippet: snippet.title)
    )


def should_ignore_code(code: str) -> bool:
    return code == "import marimo as mo"


def get_title_from_code(code: str) -> str:
    # We intentionally avoid AST parsing here to avoid the overhead
    if not code:
        return ""
    code = code.strip()
    if not (code.startswith("mo.md") or code.startswith("#")):
        return ""

    start = code.find("#")
    if start == -1:
        return ""

    # Skip the # character
    start += 1

    # Find end of title
    for end_char in ("\n", '"', "'"):
        if (end := code.find(end_char, start)) != -1:
            return code[start:end].strip()

    return code[start:].strip()


def is_markdown(code: str) -> bool:
    return code.strip().startswith("mo.md")


def read_snippet_filenames_from_config() -> Generator[str, Any, None]:
    # Get custom snippets path from config if present
    config = get_default_config_manager(current_path=None).get_config()
    custom_paths = config.get("snippets", {}).get("custom_paths", [])
    include_default_snippets = config.get("snippets", {}).get(
        "include_default_snippets", True
    )
    return read_snippet_filenames(include_default_snippets, custom_paths)


def read_snippet_filenames(
    include_default_snippets: bool, custom_paths: list[str]
) -> Generator[str, Any, None]:
    paths: list[Path] = []
    if include_default_snippets:
        paths.append(marimo_package_path() / "_snippets" / "data")
    if custom_paths:
        paths.extend([Path(p) for p in custom_paths])
    for root_path in paths:
        if not root_path.is_dir():
            # Note: currently no handling of permissions errors, but theoretically
            # this shouldn't be required for `is_dir` or `rglob`
            # Other possible errors:
            # - RecursionError: not possible, since by default symlinks are not followed
            # - FileNotFoundError: not possible, `is_dir` checks if the path exists,
            # but also resolve() is not called with strict=True
            LOGGER.warning(
                "Snippets path %s not a directory - ignoring", root_path
            )
            continue
        for file in root_path.resolve().rglob("*.py"):
            yield str(file)
