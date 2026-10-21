# Prepare the teacher-only scene-operation skill library

Run from the repository root. Python 3.9+ is sufficient; the lightweight package
uses only the standard library. On Rorqual it is tested with the available Python
3.12 interpreter. No ML environment activation is required for these checks.

## Status and architecture

The ten seed cards in `skills/spatial/static/` are editorially reviewed and
**behaviorally untested**. The dynamic catalog is empty. The package borrows
Skill-3D's record/registry/retrieval/lifecycle separation with attribution in
`skills/spatial/ATTRIBUTION.md`. It does not require the unpublished Skill-3D
memory or checkpoint. The normalized JSON files are the source of truth.

Static/dynamic is a provenance and lifecycle distinction. Static seeds may be
task-specific. Dynamic skills must carry training-episode provenance; they are
not generated or selected by this milestone.

The default `training` selection admits only reviewed, supported static cards.
Consequently it returns no cards from the initial untested library. Use explicit
`--purpose validation` to preview reviewed untested cards and evaluate their
utility. A status flag and stderr warning identify such previews. No missing
file, unmatched query or empty catalog silently inserts generic seed skills.

## Commands

```bash
python3 -m spatial_skills.cli lint --manifest skills/spatial/manifests/static-v1.json
python3 -m spatial_skills.cli lint --manifest skills/spatial/manifests/dynamic-v0.json
python3 -m spatial_skills.cli list --manifest skills/spatial/manifests/static-v1.json
python3 -m unittest discover -s test/spatial_skills -p 'test_*.py' -v
```

The static lint result reports 10 cards, 10 untested cards and a SHA-256 digest;
the dynamic result reports zero cards. The digest covers normalized ordered
cards, profile capabilities, kind and library version, not absolute file paths.

Inspect a synthetic repair case. Expected selected ID in validation mode:
`repair_without_regression`.

```bash
python3 -m spatial_skills.cli select \
  --manifest skills/spatial/manifests/static-v1.json \
  --context test/spatial_skills/fixtures/repair.json --purpose validation
python3 -m spatial_skills.cli render \
  --manifest skills/spatial/manifests/static-v1.json \
  --context test/spatial_skills/fixtures/repair.json --purpose validation
```

For Layout use `test/spatial_skills/fixtures/layout.json`; expected ID:
`render_compare_refine`. These fixtures exercise retrieval mechanics, not actual
benchmark performance. They contain authored public descriptions, not private
target labels. The renderer prints only procedural fields, not validation or
provenance metadata. Cards exceeding 2,000 rendered characters or a complete
teacher block exceeding 4,000 characters are rejected without truncation.

Portable normalized snapshot export:

```bash
python3 -m spatial_skills.cli export \
  --manifest skills/spatial/manifests/static-v1.json --output /tmp/spatial-static-v1.json
python3 -m spatial_skills.cli lint --manifest /tmp/spatial-static-v1.json
```

An existing output is refused unless `--overwrite` is explicit. Reloading the
export verifies its digest; changing cards or capabilities without recomputing
the digest is rejected. Exporting is the only CLI operation that writes files.

## Retrieval and teacher/student boundary

`RetrievalContext` accepts exactly task family, task text, public-history text,
and available logical capabilities. It cannot ingest a separate ground-truth,
reward or future-observation field. Callers remain responsible for ensuring the
public text itself is not derived from hidden labels. Image understanding and
adapter-to-capability mappings are future integration work.

Retrieval filters family, available capabilities, review/validation status and
kind, then counts distinct matching trigger phrases with word boundaries.
Repeated phrases do not increase their score. Ties use stable IDs. A literal
`*` is an explicitly authored task-wide trigger; none is implicit. At most one
static card is returned, with scores and exclusion reasons for audit.

```python
from pathlib import Path
from spatial_skills import RetrievalContext, load_registry
from spatial_skills.retrieval import select_skills
from spatial_skills.prompts import build_teacher_view, render_skill_block

registry = load_registry(Path("skills/spatial/manifests/static-v1.json"))
context = RetrievalContext(
    "spatialact_repair", "Repair the scene.",
    "The previous edit introduced a new violation.",
    ("observe_scene", "edit_pose"),
)
selection = select_skills(registry, context, purpose="validation")
block = render_skill_block([registry.get(i) for i in selection.selected_ids])
student_messages = [{"role": "user", "content": "Ordinary task and observation."}]
teacher_messages = build_teacher_view(student_messages, block)
```

`build_teacher_view` deep-copies messages, adding the block to the first system
message (or inserting one). Text content and multimodal system-content arrays
are supported; unsupported shapes fail explicitly. Student messages and all
user/tool/image histories are preserved. Empty selections yield an independent,
unchanged teacher copy. This package does not automatically call the builder
from the SPAgent scheduler: the integration must wire it to the teacher only.

Keep tool schemas, mandatory units, coordinate conventions and action
restrictions in shared prompts. Keep skills absent from student training and
inference. Do not use Skill-3D's `skills` prompt mode for the student: that path
can insert static fallback skills even with memory updating disabled.

## Behavioral validation protocol (required before training support)

1. **Freeze the comparison.** Record a model checkpoint/revision, tool and
   renderer versions, action budget, library digest, card ID/version and paired
   initial scene seeds. Use independent skill-development scenes. Official
   benchmark test cases and the separate model-development set stay excluded.
2. **Predeclare a decision rule.** Choose a minimum useful outcome improvement
   or a task-specific noninferiority margin when reducing cost. Specify sample
   count, confidence-interval method, stopping rule and regression limits before
   viewing results. Do not infer usefulness from a nonsignificant difference.
3. **Run matched episodes.** Compare the identical policy with and without one
   card, using the same public information, permitted tools and initial state.
   Match sampling seeds where practical, repeat to address stochasticity, and
   count all tool/renderer interactions. Start with a small screening set and
   expand uncertain comparisons under the declared rule.
4. **Measure native outcomes.** For repair, record repair/scene success, newly
   introduced violations and invalid edits. For Layout, record native ADD-S,
   completeness and invalid transforms. Also record renders, interactions,
   tokens and elapsed time. Do not replace geometric outcome with apparent
   reasoning quality or an author's confidence in the card.
5. **Retain evidence.** Store episode IDs, paired conditions, raw outcomes,
   infrastructure failures, confidence intervals, card hashes and protocol in a
   tracked evaluation artifact. An infrastructure failure is not automatically
   evidence against a skill; disclose exclusion rules and failure rates.
6. **Promote explicitly.** A useful card becomes `supported` only after review of
   the measured evidence. Record the evaluation-artifact reference in its
   `source_refs`, bump its version and the library version, and commit the
   change. Static cards may legitimately have empty episode provenance when
   authored; their support evidence must still be retained externally. Reject
   harmful cards; keep uncertain cards untested. Freeze the chosen version for
   each subsequent RL interval.

No behavioral study has been run in this milestone. Small paired tests screen
teacher utility; they do not prove generalization. Keep a sealed audit set to
detect overfitting from repeated candidate testing. Future dynamic skills
require successful-workflow or failure-diagnosis provenance and independently
verified corrections before promotion; failed traces alone do not establish a
valid remedy.

## Next integration gate

Implement the real environment adapters and an ordinary skill-free student
rollout before wiring teacher context into ms-swift. Check image/history
identity across scoring branches, original action-token alignment, teacher/gate
gradient detachment and equivalence to ordinary GRPO when distillation is zero.
These trainer-level requirements are not established by message-copy tests.

Actual model/simulator experiments must use the project's tracked compute
workflow. Lightweight preparation checks can run on the Rorqual login node; no
GPU or experiment job is launched by this package.
