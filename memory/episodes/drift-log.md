# Drift Log

| date | task | symptom | cause | fix | reusable_rule |
| --- | --- | --- | --- | --- | --- |
| 2026-05-08 | Phase 8 audit | Some answer-type interfaces did not read canonical files first. | Preflight rule was implemented unevenly. | Added canonical preflight for `/ask` and Agent endpoints. | Answer-type work must call canonical preflight before retrieval or generation. |
| 2026-05-08 | Phase 8.7 real task test | Workflow candidate paths did not match current SK filenames. | Hard-coded candidate paths drifted from repository names. | Fallback search found alternate files. | Candidate path misses should be logged and converted to routing or SOP fixes. |
