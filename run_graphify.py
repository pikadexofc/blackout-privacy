import json
from pathlib import Path
from graphify.detect import detect
from graphify.extract import extract
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json, to_html

out_dir = Path("graphify-out")
out_dir.mkdir(exist_ok=True)

res = detect(Path("."))
(out_dir / ".graphify_detect.json").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
print(f"Detected {res['total_files']} files")

code_files = [Path(f) for f in res.get("files", {}).get("code", []) if not str(f).startswith("build") and not str(f).startswith("dist")]
ast_res = extract(code_files, cache_root=Path("."))
(out_dir / ".graphify_extract.json").write_text(json.dumps(ast_res, indent=2, ensure_ascii=False), encoding="utf-8")

G = build_from_json(ast_res, root=".")
communities = cluster(G)
cohesion = score_all(G, communities)
tokens = {"input": 0, "output": 0}
gods = god_nodes(G)
surprises = surprising_connections(G, communities)

labels = {
    0: "Screen Blackout Engine & DWM Affinity",
    1: "GUI Interface & User Feedback",
    2: "Automated BitBlt Test Verification"
}
# Fallback for any other community
for cid in communities:
    if cid not in labels:
        labels[cid] = f"Privacy Core Group {cid}"

questions = suggest_questions(G, communities, labels)

to_json(G, communities, str(out_dir / "graph.json"), community_labels=labels)
report = generate(G, communities, cohesion, labels, gods, surprises, res, tokens, ".", suggested_questions=questions)
(out_dir / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")

try:
    to_html(G, communities, str(out_dir / "graph.html"), community_labels=labels)
except Exception as e:
    print(f"HTML export notice: {e}")

print(f"Graph complete: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(communities)} communities")
