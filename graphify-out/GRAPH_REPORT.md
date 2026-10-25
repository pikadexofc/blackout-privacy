# Graph Report - blackout-privacy  (2026-10-25)

## Corpus Check
- Corpus is ~11,941 words - fits in a single context window. You may not need a graph.

## Summary
- 87 nodes · 115 edges · 7 communities (2 shown, 5 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Screen Blackout Engine & DWM Affinity
- GUI Interface & User Feedback
- Automated BitBlt Test Verification
- Privacy Core Group 3
- Privacy Core Group 4
- Privacy Core Group 6

## God Nodes (most connected - your core abstractions)
1. `ScreenBlackoutManager` - 14 edges
2. `BlackoutApp` - 11 edges
3. `FeedbackDialog` - 6 edges
4. `TestScreenBlackout` - 6 edges
5. `steps` - 5 edges
6. `with` - 4 edges
7. `build` - 3 edges
8. `worker()` - 3 edges
9. `_ensure_class_registered()` - 3 edges
10. `sample_screen_pixel()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `BlackoutApp` --uses--> `ScreenBlackoutManager`  [INFERRED]
  app.py → blackout_core.py
- `TestScreenBlackout` --uses--> `ScreenBlackoutManager`  [INFERRED]
  test_blackout.py → blackout_core.py

## Import Cycles
- None detected.

## Communities (7 total, 5 thin omitted)

### Community 0 - "Screen Blackout Engine & DWM Affinity"
Cohesion: 0.15
Nodes (3): ScreenBlackoutManager, sample_screen_pixel(), TestScreenBlackout

### Community 1 - "GUI Interface & User Feedback"
Cohesion: 0.11
Nodes (17): runs-on, steps, jobs, build, name, branches, branches, name (+9 more)

## Knowledge Gaps
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ScreenBlackoutManager` connect `Screen Blackout Engine & DWM Affinity` to `Automated BitBlt Test Verification`, `Privacy Core Group 3`, `Privacy Core Group 4`?**
  _High betweenness centrality (0.211) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ScreenBlackoutManager` (e.g. with `BlackoutApp` and `TestScreenBlackout`) actually correct?**
  _`ScreenBlackoutManager` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `Screen Blackout Engine & DWM Affinity` be split into smaller, more focused modules?**
  _Cohesion score 0.14761904761904762 - nodes in this community are weakly interconnected._
- **Why does `BlackoutApp` connect `Privacy Core Group 4` to `Screen Blackout Engine & DWM Affinity`, `Privacy Core Group 3`, `Privacy Core Group 6`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Should `GUI Interface & User Feedback` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._
- **Why does `FeedbackDialog` connect `Privacy Core Group 6` to `Privacy Core Group 3`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._