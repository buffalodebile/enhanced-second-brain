from __future__ import annotations

from collections import Counter
from itertools import pairwise
from pathlib import Path, PurePosixPath
from typing import Any

import networkx as nx

from .pages import iter_page_paths, page_links, parse_markdown, resolve_link


def build(vault: Path) -> nx.DiGraph:
    pages = [parse_markdown(path, vault) for path in iter_page_paths(vault)]
    known: dict[str, str] = {}
    for page in pages:
        rel = page.relative_path
        stem = PurePosixPath(rel).with_suffix("").as_posix().lower()
        known[stem] = rel
        known[PurePosixPath(stem).name] = rel
        known[str(page.metadata.get("title") or "").lower()] = rel
    graph = nx.DiGraph()
    for page in pages:
        graph.add_node(
            page.relative_path, title=str(page.metadata.get("title") or page.path.stem)
        )
    for page in pages:
        typed: dict[str, str] = {}
        for relationship in page.metadata.get("relationships") or []:
            if isinstance(relationship, dict):
                target = (
                    str(relationship.get("target") or "")
                    .replace("[[", "")
                    .replace("]]", "")
                )
                typed[target] = str(relationship.get("type") or "related_to")
        for raw in page_links(page):
            target = resolve_link(page, raw, known)
            if target and target != page.relative_path:
                graph.add_edge(
                    page.relative_path, target, type=typed.get(raw, "related_to")
                )
    return graph


def resolve_node(graph: nx.Graph, raw: str) -> str:
    normalized = raw.replace("\\", "/").lower().removesuffix(".md")
    exact: list[str] = []
    for node, data in graph.nodes(data=True):
        stem = PurePosixPath(node).with_suffix("").as_posix().lower()
        if normalized in {
            stem,
            PurePosixPath(stem).name,
            str(data.get("title", "")).lower(),
        }:
            exact.append(node)
    if len(exact) == 1:
        return exact[0]
    if not exact:
        raise ValueError(f"Unknown page: {raw}")
    raise ValueError(f"Ambiguous page: {raw} -> {', '.join(exact)}")


def path(vault: Path, source: str, target: str) -> dict[str, Any]:
    graph = build(vault)
    source_node, target_node = resolve_node(graph, source), resolve_node(graph, target)
    undirected = graph.to_undirected()
    nodes = nx.shortest_path(undirected, source_node, target_node)
    steps = []
    for left, right in pairwise(nodes):
        if graph.has_edge(left, right):
            steps.append(
                {
                    "from": left,
                    "to": right,
                    "type": graph[left][right].get("type", "related_to"),
                    "reverse": False,
                }
            )
        else:
            steps.append(
                {
                    "from": left,
                    "to": right,
                    "type": graph[right][left].get("type", "related_to"),
                    "reverse": True,
                }
            )
    return {"nodes": nodes, "hops": len(nodes) - 1, "steps": steps}


def impact(vault: Path, node: str, *, depth: int = 3) -> dict[str, Any]:
    graph = build(vault)
    target = resolve_node(graph, node)
    reverse = graph.reverse(copy=False)
    lengths = nx.single_source_shortest_path_length(reverse, target, cutoff=depth)
    grouped: dict[int, list[str]] = {}
    for page, hops in lengths.items():
        if hops:
            grouped.setdefault(hops, []).append(page)
    return {
        "page": target,
        "depth": depth,
        "dependents": {str(k): sorted(v) for k, v in grouped.items()},
        "total": len(lengths) - 1,
    }


def hubs(vault: Path, *, limit: int = 10) -> list[dict[str, Any]]:
    graph = build(vault)
    rows = [
        {
            "page": node,
            "degree": graph.degree(node),
            "incoming": graph.in_degree(node),
            "outgoing": graph.out_degree(node),
        }
        for node in graph.nodes
    ]
    return sorted(rows, key=lambda row: (-row["degree"], row["page"]))[:limit]


def clusters(vault: Path) -> list[dict[str, Any]]:
    graph = build(vault).to_undirected()
    communities = (
        nx.community.greedy_modularity_communities(graph)
        if graph.number_of_edges()
        else [frozenset([n]) for n in graph.nodes]
    )
    result = []
    for i, community in enumerate(
        sorted(communities, key=lambda group: (-len(group), min(group))), 1
    ):
        subgraph = graph.subgraph(community)
        result.append(
            {
                "cluster": i,
                "size": len(community),
                "density": nx.density(subgraph),
                "pages": sorted(community),
            }
        )
    return result


def bridges(vault: Path, *, limit: int = 10) -> list[dict[str, Any]]:
    graph = build(vault).to_undirected()
    if not graph.number_of_nodes():
        return []
    centrality = nx.betweenness_centrality(graph)
    return [
        {"page": page, "betweenness": score}
        for page, score in sorted(
            centrality.items(), key=lambda item: (-item[1], item[0])
        )[:limit]
    ]


def backlinks(vault: Path) -> Counter[str]:
    graph = build(vault)
    return Counter({node: graph.in_degree(node) for node in graph.nodes})
