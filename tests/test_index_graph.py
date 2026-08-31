from __future__ import annotations

from conftest import write_page

from enhanced_second_brain.graph import bridges, clusters, hubs, impact, path
from enhanced_second_brain.index import query, update


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


def test_graph_path_impact_hubs_clusters_bridges(vault) -> None:
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
    result = path(vault, "alpha", "gamma")
    assert result["hops"] == 2
    assert [step["type"] for step in result["steps"]] == ["uses", "informs"]
    assert impact(vault, "gamma", depth=3)["total"] == 2
    assert hubs(vault)[0]["page"] == "concepts/b.md"
    assert clusters(vault)[0]["size"] == 3
    assert bridges(vault)[0]["page"] == "concepts/b.md"
