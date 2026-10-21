# Attribution and adaptation record

Reference: [Skill-3D](https://github.com/skill-3d/Skill-3D), commit
`e379d643e9889f49cb19dd425ceee9ff00e9adee`.

The new preparation module is an independent implementation of a small schema,
registry and retrieval interface inspired by Skill-3D's organization. We do not
vendor its agent, perception stack, dynamic memory or trained checkpoints.

The seed procedures in `skill3d/core/skill_normalization.py` informed these cards:

| Original skill | Adapted card(s) |
|---|---|
| Spatial Localization & Relation | `reference_frame_reasoning`, `match_objects_and_anchors` |
| Multi-view Verification & Occlusion | `select_informative_evidence`, `resolve_multiview_pose` |
| Object Segmentation & Boundary Analysis | `diagnose_spatial_error` |
| Comprehensive Scene Understanding | `select_informative_evidence`, `match_objects_and_anchors` |

Cards are rewritten for scene operations and are not verbatim original skills.
Each card records its source links and adaptation notes. Remaining cards are
original procedures informed by SpatialAct and SceneActBench task definitions.
Editorial review does not establish measured effectiveness.

Skill-3D is distributed under Apache-2.0; a copy of its license is preserved in
`licenses/Skill-3D-Apache-2.0.txt`. Original authorship and notices remain with the
referenced project. No unpublished evolved library or scene memory is included.
