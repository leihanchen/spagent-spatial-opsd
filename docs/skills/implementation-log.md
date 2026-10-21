# Initial skill-preparation implementation record

Plan: `initial-skill-preparation-plan.md` in the project's spatial-opsd artifacts.
Implementation date: 2026-10-20.

## Scope completed

The work is on `skills-preparation` in
`/lustre10/scratch/leihan/spagent-spatial-opsd` on Rorqual, based on SPAgent
`14886f02a53e6a0f6cc6be3065693a1016416928`.

| Plan task | Implementation | Verification |
| --- | --- | --- |
| 1: schema and registry | Strict immutable records, explicit manifests, capability profiles, portable digest | 9 schema/registry tests |
| 2: static seeds | Ten reviewed but untested cards; empty dynamic-v0 catalog; attribution and upstream license | 3 library tests plus editorial review |
| 3: retrieval | Deterministic filtering, phrase scoring, stable ties, exclusion audit | 6 retrieval tests |
| 4: teacher boundary | Bounded rendering and independent teacher message copies | 5 prompt-boundary tests |
| 5: CLI and export | lint/list/select/render/export, synthetic repair/layout examples | 5 CLI tests |
| 6: behavioral validation preparation | Paired-run protocol and explicit evidence/promotion rules | Documentation review; no behavioral study run |

All 28 new contract tests passed on Rorqual with Python 3.12.4 and locally with
Python 3.9. The command was:

```bash
python3 -m unittest discover -s test/spatial_skills -p 'test_*.py' -v
```

Both CLI lint commands passed, and `git diff --check` passed. These checks cover
the new preparation package, not the complete SPAgent model/tool test suite.
No model inference, benchmark episode, GPU job or RL training was launched.

The static library digest is
`0913ac05607404423a492e7a314f137d1096e94c9863076f7479d86342e49e4c`.
The empty dynamic library digest is
`bc73bb37c3eb032d19952a894f3d5674a5c6d7c86e4f0d14239b828f7ea8a58a`.

## Implementation decisions

- Ruling: add narrow `.gitignore` exceptions for skill JSON and synthetic JSON
  fixtures — upstream ignores all `*.json`, which would omit the library from
  commits — if the patterns prove too broad, narrow them before adding data.
- Ruling: include capability profiles in the portable digest — a profile change
  changes eligibility even with identical card text — consumers must regenerate
  snapshots when capabilities change.
- Ruling: keep this module outside the heavy `spagent` package — preparation
  checks must work without model dependencies — future integration uses an
  explicit import rather than implicit scheduler registration.
- Ruling: consolidate the preparation changes into one commit and publish the
  feature branch and PR — explicitly requested by the user — retain the branch
  for review without merging it into main.

## Independent review

A read-only whole-change review found no critical or important issues and
independently ran the 28 passing tests. Two minor malformed-input cases remain:

- `build_teacher_view` accepts a system content list without checking every
  element. A malformed list such as `[None]` is copied and extended rather than
  rejected. Valid multimodal messages are preserved correctly.
- `RetrievalContext` checks task-family membership before its type. A list-valued
  family raises `TypeError` instead of descriptive `ValueError`; the CLI catches
  it and exits nonzero.

These do not change normal retrieval or the teacher/student boundary. They are
deferred robustness work, not evidence of behavioral effectiveness.

## Next boundary

Follow [preparation.md](preparation.md) for commands and the paired behavioral
validation protocol. All ten cards are currently `untested`, so normal training
selection returns no skills. Explicit validation previews are available. Real
environment adapters, skill utility measurements, promotion of useful cards,
and ms-swift teacher-scoring integration remain future work.

## Required CPU CI follow-up

PR #1 also adds `.github/workflows/cpu-tests.yml`. It discovers offline CPU tests
throughout `test/` on Python 3.10 and 3.12, including skill tests, core/render
integration, prompt tests, mocked HTTP clients, and CLI mock adapters. The local
matrix passes with 123 passed and four documented live/weight-dependent skips.
Unexpected skips fail; live sockets are blocked during tests. Collection-gate
tests prove that new passing, failing, and skipped test files are detected.

Two existing Molmo2 tests were updated to the current point-grounding contract:
use a valid image fixture and check point output rather than obsolete QA text.
The VACE CLI mock test supplies the video-path fixture its mock advertises and
checks copying; it does not claim video generation. See `test/README.md` for
explicit exclusions and the required-check policy.
