# Teacher-only spatial skills

This library adapts Skill-3D's static/dynamic organization for the scene-operation
SDAR experiment. Student observations and tools are shared with the teacher;
these additional procedural cards are teacher-only context.

- `manifests/static-v1.json` lists ten editorially reviewed seed cards. Their
  behavioral status is **untested**: they are available only in explicit
  validation mode until supported by paired execution evidence.
- `manifests/dynamic-v0.json` is an explicitly empty catalog. Loading an empty
  or unmatched library does not insert fallback skills.
- JSON cards are canonical. Exported Markdown is generated, not a second source
  of truth. Library digests include normalized cards, ordering and capabilities.
- Static describes a fixed seed version; it does not imply applicability to all
  task families. Dynamic cards require training-episode provenance.

`profiles.json` defines **logical capabilities**, not callable tools. A later
benchmark adapter must map its actual public interface to these capabilities;
the preparation package grants no extra observations, transforms or oracle.
SpatialAct feedback may be provided automatically rather than through an
inspection call. SceneActBench inspection exposes current editable geometry,
not hidden target transforms.

Tool schemas, mandatory units, coordinate conventions and action restrictions
must remain available to both branches. Cards add conditional procedures.
Do not put ground-truth scene-specific answers in them or derive them from
official benchmark test episodes. Freeze versions within RL collection/update
intervals. No automatic skill mutation is implemented here.

See [the preparation guide](../../docs/skills/preparation.md) for CLI examples,
prompt boundaries and the required behavioral validation protocol.
