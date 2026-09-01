from __future__ import annotations

from conftest import write_page

from enhanced_second_brain.index import query, update
from enhanced_second_brain.pages import iter_page_paths
from enhanced_second_brain.utility import backlinks


def test_fts_lifecycle_and_unicode(settings, vault) -> None:
    first = write_page(
        vault,
        "concepts/cafe.md",
        title="Café field guide",
        description="Étude côtière",
        body="# Café\n\nObservation à l'estuaire.",
    )
    stats = update(settings)
    assert stats["added"] == 1
    assert query(settings, "cafe estuaire", track=False)[0].path == "concepts/cafe.md"
    first.write_text(
        first.read_text(encoding="utf-8").replace("estuaire", "lagune"),
        encoding="utf-8",
    )
    assert update(settings)["changed"] == 1
    assert query(settings, "lagune", track=False)[0].path == "concepts/cafe.md"
    first.rename(vault / "concepts" / "coast.md")
    transition = update(settings)
    assert transition["added"] == 1 and transition["removed"] == 1
    (vault / "concepts" / "coast.md").unlink()
    assert update(settings)["removed"] == 1


def test_backlinks_protect_linked_pages_without_another_engine(vault) -> None:
    write_page(
        vault,
        "concepts/a.md",
        title="Alpha",
        description="Alpha",
        body="# Alpha",
        relationships=[{"type": "uses", "target": "[[concepts/b]]"}],
    )
    write_page(
        vault,
        "concepts/b.md",
        title="Beta",
        description="Beta",
        body="# Beta",
        relationships=[{"type": "informs", "target": "[[concepts/c]]"}],
    )
    write_page(
        vault, "concepts/c.md", title="Gamma", description="Gamma", body="# Gamma"
    )
    incoming = backlinks(vault)
    assert incoming["concepts/a.md"] == 0
    assert incoming["concepts/b.md"] == 1
    assert incoming["concepts/c.md"] == 1


def test_page_walk_prunes_operational_directories(vault) -> None:
    write_page(
        vault, "concepts/visible.md", title="Visible", description="Visible", body="# Visible"
    )
    hidden = vault / ".git" / "objects" / "hidden.md"
    hidden.parent.mkdir(parents=True)
    hidden.write_text("# Hidden", encoding="utf-8")
    archived = vault / "_archives" / "old.md"
    archived.parent.mkdir(parents=True)
    archived.write_text("# Archived", encoding="utf-8")
    assert [path.relative_to(vault).as_posix() for path in iter_page_paths(vault)] == [
        "concepts/visible.md"
    ]
