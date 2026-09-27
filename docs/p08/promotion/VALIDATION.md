# Golden promotion integrity checks

The contract suite exercises forty generated positive/negative controls. They
check evidence structure and source identities, never visual similarity. The
standalone tests and Unity preflight use separate MSBuild intermediate/output
directories so their net10.0 and netstandard2.1 restores can coexist.

Actual Unity 6000.5.7f1 checks in this continuation:

1. The unchanged imported Apex R4 prefab instance passed ValidateCaptureInstance.
2. Setting one renderer's forceRenderingOff flag caused the same check to reject
   the instance. The instance was then restored and destroyed.
3. Asking the pack binding layer to validate Apex R4 in bike slot05 without an
   accepted manifest failed with `Golden prefab has no active accepted binding`.
4. The real Apex R5 native camera capture completed, and its PNG decoded through
   ValidateEvidenceImage. The temporary capture scene was removed and Race was
   restored as the sole active scene. This checks the capture mechanism; the
   studio camera/lighting are not the locked concept's calibrated view.

No production manifest or accepted review was created. Current candidates remain
unaccepted, production masks remain1/1/1, and no full content build was attempted.
Rest-pose captures do not cover animation/contact/deformation acceptance.

The R5 import and capture artifacts belong to the separate seam-repair patch.
The current recorder binds its fresh-instance-lod0 policy, actual camera state,
source descriptor/import/prefab/concept hashes and image bytes. Reviewers still
have to inspect each required matching view and document every visual dimension;
software cannot establish that a reviewer's declaration is true.
