from pathlib import Path
import re

p = Path("app/dashboard/routes.py")
code = p.read_text(encoding="utf-8")

if "/knowledge-graph" in code:
    print("Knowledge graph route already present — skipping")
else:
    # Find insertion point — right after teaching_dashboard route
    marker = "return templates.TemplateResponse(request, \"teaching_dashboard.html\", ctx)"
    idx = code.find(marker)
    if idx == -1:
        print("teaching_dashboard route not found — bailing")
    else:
        # Find end of function
        end_idx = code.find("\n\n\n", idx)
        if end_idx == -1:
            end_idx = code.find("\n\n@router", idx)

        NEW_ROUTE = '''


# --- Knowledge Graph (Phase 1B) --------------------------------------------


@router.get("/knowledge-graph", response_class=HTMLResponse)
async def knowledge_graph(request: Request, user: User = Depends(require_user)):
    """Visual network of library entries showing connections via embedding similarity."""
    import json as _json
    import math

    from app.tools import memory_tool

    # Fetch all active entries with content
    entries = fetch_all("""
        SELECT id, purpose, service_line, content, applied_count, kind
          FROM knowledge_library
         WHERE is_active = 1
         ORDER BY id
    """)
    entries = [dict(e) for e in entries]

    # Compute embeddings for each entry (truncated content)
    # For efficiency, batch embed; but simplest: one call each (we have <100 entries)
    embeddings = {}
    for e in entries:
        try:
            vec = memory_tool.embed((e["content"] or "")[:500])
            if vec:
                embeddings[e["id"]] = vec
        except Exception:
            continue

    # Compute similarity matrix — edge if cosine similarity > 0.6
    def cosine(a, b):
        dot = sum(x*y for x, y in zip(a, b))
        na = math.sqrt(sum(x*x for x in a))
        nb = math.sqrt(sum(x*x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    edges = []
    ids = list(embeddings.keys())
    for i, aid in enumerate(ids):
        for bid in ids[i+1:]:
            sim = cosine(embeddings[aid], embeddings[bid])
            if sim > 0.6:
                edges.append({"from": aid, "to": bid, "weight": round(sim, 3)})

    # Compute node positions using simple force-directed layout
    # Place nodes in a circle initially, then iterate
    import random
    random.seed(42)
    n = len(entries)
    positions = {}
    if n > 0:
        for i, e in enumerate(entries):
            angle = 2 * math.pi * i / n
            positions[e["id"]] = {"x": 400 + 280 * math.cos(angle), "y": 300 + 250 * math.sin(angle)}

    # Simple spring layout — 100 iterations
    edge_set = {(e["from"], e["to"]): e["weight"] for e in edges}
    for _ in range(100):
        forces = {eid: {"fx": 0.0, "fy": 0.0} for eid in positions}

        # Repulsive force between all pairs
        node_ids = list(positions.keys())
        for i, a in enumerate(node_ids):
            for b in node_ids[i+1:]:
                dx = positions[a]["x"] - positions[b]["x"]
                dy = positions[a]["y"] - positions[b]["y"]
                dist = max(10, math.sqrt(dx*dx + dy*dy))
                # Repulsion ~ 1/dist^2, scaled
                rep = 4000 / (dist * dist)
                forces[a]["fx"] += rep * dx / dist
                forces[a]["fy"] += rep * dy / dist
                forces[b]["fx"] -= rep * dx / dist
                forces[b]["fy"] -= rep * dy / dist

        # Attractive force along edges
        for edge in edges:
            a, b = edge["from"], edge["to"]
            if a not in positions or b not in positions:
                continue
            dx = positions[a]["x"] - positions[b]["x"]
            dy = positions[a]["y"] - positions[b]["y"]
            dist = max(10, math.sqrt(dx*dx + dy*dy))
            # Attraction ~ dist * weight
            att = 0.02 * dist * edge["weight"]
            forces[a]["fx"] -= att * dx / dist
            forces[a]["fy"] -= att * dy / dist
            forces[b]["fx"] += att * dx / dist
            forces[b]["fy"] += att * dy / dist

        # Apply forces (damped)
        for eid in positions:
            positions[eid]["x"] += forces[eid]["fx"] * 0.1
            positions[eid]["y"] += forces[eid]["fy"] * 0.1
            # Keep within viewport
            positions[eid]["x"] = max(50, min(750, positions[eid]["x"]))
            positions[eid]["y"] = max(50, min(550, positions[eid]["y"]))

    # Prepare nodes for template
    purpose_colors = {
        "voice_example": "#8B5CF6",       # purple
        "classifier_example": "#06B6D4",  # cyan
        "document_type": "#F59E0B",       # amber
        "question_template": "#6366F1",   # indigo
        "workflow_rule": "#F97316",       # orange
        "firm_fact": "#10B981",           # emerald
        "firm_policy": "#3B82F6",         # blue
        "reference_material": "#64748B",  # slate
    }

    nodes = []
    for e in entries:
        pos = positions.get(e["id"], {"x": 400, "y": 300})
        size = 8 + min(12, e["applied_count"] * 2)  # 8-20 px based on usage
        nodes.append({
            "id": e["id"],
            "x": round(pos["x"], 1),
            "y": round(pos["y"], 1),
            "purpose": e["purpose"],
            "service_line": e["service_line"],
            "content_preview": (e["content"] or "")[:120],
            "applied_count": e["applied_count"],
            "color": purpose_colors.get(e["purpose"], "#64748B"),
            "size": size,
        })

    # Stats for the header
    stats = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "isolated": len([n for n in nodes if not any(n["id"] in (e["from"], e["to"]) for e in edges)]),
        "densest_purpose": None,
    }
    # Which purpose has most edges
    purpose_edge_count = {}
    node_by_id = {n["id"]: n for n in nodes}
    for edge in edges:
        a = node_by_id.get(edge["from"])
        b = node_by_id.get(edge["to"])
        if a and b and a["purpose"] == b["purpose"]:
            purpose_edge_count[a["purpose"]] = purpose_edge_count.get(a["purpose"], 0) + 1
    if purpose_edge_count:
        stats["densest_purpose"] = max(purpose_edge_count.items(), key=lambda x: x[1])[0]

    ctx = _common_context(request, user)
    ctx.update({
        "nodes": nodes,
        "edges": edges,
        "stats": stats,
        "purpose_colors": purpose_colors,
        "active_tab": "train",
    })
    return templates.TemplateResponse(request, "knowledge_graph.html", ctx)


'''

        code = code[:end_idx] + NEW_ROUTE + code[end_idx:]
        p.write_text(code, encoding="utf-8")
        print(f"Added /knowledge-graph route. File size: {len(code)}")

# Verify import
import sys
for mod in list(sys.modules):
    if "app.dashboard" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.dashboard import routes as _r
    print("Routes import clean")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
