# Graph Report - blackout-privacy  (2026-10-25)

## Corpus Check
- Corpus is ~6,254 words - fits in a single context window. You may not need a graph.

## Summary
- 113 nodes · 181 edges · 9 communities (4 shown, 5 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 23 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Screen Blackout Engine & DWM Affinity
- GUI Interface & User Feedback
- Automated BitBlt Test Verification
- Privacy Core Group 3
- Privacy Core Group 4
- Privacy Core Group 5
- Privacy Core Group 7
- Privacy Core Group 8

## God Nodes (most connected - your core abstractions)
1. `ScreenBlackoutManager` - 18 edges
2. `run_all_empirical_tests()` - 13 edges
3. `run_empirical_verification()` - 11 edges
4. `FeedbackDialog` - 10 edges
5. `BlackoutApp` - 10 edges
6. `TestScreenBlackout` - 6 edges
7. `steps` - 5 edges
8. `with` - 4 edges
9. `init_dpi_awareness()` - 4 edges
10. `get_mem_bytes()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `BlackoutApp` --uses--> `ScreenBlackoutManager`  [INFERRED]
  app.py → blackout_core.py
- `TestScreenBlackout` --uses--> `ScreenBlackoutManager`  [INFERRED]
  test_blackout.py → blackout_core.py
- `run_all_empirical_tests()` --calls--> `ScreenBlackoutManager`  [EXTRACTED]
  test_challenger_stress.py → blackout_core.py
- `run_empirical_verification()` --calls--> `ScreenBlackoutManager`  [EXTRACTED]
  test_empirical_screen_capture.py → blackout_core.py

## Import Cycles
- None detected.

## Communities (9 total, 5 thin omitted)

### Community 0 - "Screen Blackout Engine & DWM Affinity"
Cohesion: 0.12
Nodes (3): ScreenBlackoutManager, sample_screen_pixel(), TestScreenBlackout

### Community 1 - "GUI Interface & User Feedback"
Cohesion: 0.11
Nodes (17): runs-on, steps, jobs, build, name, branches, branches, name (+9 more)

### Community 5 - "Privacy Core Group 5"
Cohesion: 0.40
Nodes (6): get_gui_resources(), get_handle_count(), get_mem_bytes(), POINT, PROCESS_MEMORY_COUNTERS, run_all_empirical_tests()

### Community 7 - "Privacy Core Group 7"
Cohesion: 0.29
Nodes (6): capture_pixel_64bit(), enumerate_monitors(), enum_cb(), MONITORINFOEXW, RECT, run_empirical_verification()

## Knowledge Gaps
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ScreenBlackoutManager` connect `Screen Blackout Engine & DWM Affinity` to `Automated BitBlt Test Verification`, `Privacy Core Group 4`, `Privacy Core Group 5`, `Privacy Core Group 7`, `Privacy Core Group 8`?**
  _High betweenness centrality (0.207) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ScreenBlackoutManager` (e.g. with `BlackoutApp` and `TestScreenBlackout`) actually correct?**
  _`ScreenBlackoutManager` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `Screen Blackout Engine & DWM Affinity` be split into smaller, more focused modules?**
  _Cohesion score 0.12333333333333334 - nodes in this community are weakly interconnected._
- **Why does `FeedbackDialog` connect `Privacy Core Group 3` to `Automated BitBlt Test Verification`, `Privacy Core Group 4`?**
  _High betweenness centrality (0.138) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `run_all_empirical_tests()` (e.g. with `.activate()` and `.deactivate()`) actually correct?**
  _`run_all_empirical_tests()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `GUI Interface & User Feedback` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._
- **Why does `BlackoutApp` connect `Privacy Core Group 4` to `Screen Blackout Engine & DWM Affinity`, `Automated BitBlt Test Verification`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._