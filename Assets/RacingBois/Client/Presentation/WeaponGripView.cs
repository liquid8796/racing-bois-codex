using RacingBois.Gameplay.Definitions;
using UnityEngine;

namespace RacingBois.Client.Presentation
{
    /// <summary>A visual prop follows the authored palm; only authoritative equipment selects visibility.</summary>
    public sealed class WeaponGripView : MonoBehaviour
    {
        private Transform club, leftPalmBone, rightPalmBone;
        private Quaternion inverseModelBasis;
        private int lastHand = 1;
        private bool skinnedHand;
        private Vector3 leftGripOffset,rightGripOffset;
        private Quaternion leftGripRotation,rightGripRotation;

        public void Initialize(GameObject prefab, Transform rider)
        {
            var model = rider.Find("Model");
            inverseModelBasis = Quaternion.Inverse(model == null ? Quaternion.identity : model.localRotation);
            foreach (var bone in rider.GetComponentsInChildren<Transform>(true))
            {
                if (bone.name == "RB_Rider_L0_Forearm_L") leftPalmBone = bone;
                if (bone.name == "RB_Rider_L0_Forearm_R") rightPalmBone = bone;
                if (bone.name == "RB_P06_Rider_L0_Hand_L") { leftPalmBone = bone; skinnedHand = true; }
                if (bone.name == "RB_P06_Rider_L0_Hand_R") { rightPalmBone = bone; skinnedHand = true; }
            }
            if (prefab == null || leftPalmBone == null || rightPalmBone == null)
                throw new System.InvalidOperationException("Club prefab or authored rider palm joint is missing.");
            if(skinnedHand)
            {
                // Convert semantic bind-pose offsets once; imported bone roll is not the model root basis.
                var offset=rider.TransformVector(new Vector3(0,-.04f,.01f));
                leftGripOffset=leftPalmBone.InverseTransformVector(offset);rightGripOffset=rightPalmBone.InverseTransformVector(offset);
                leftGripRotation=Quaternion.Inverse(leftPalmBone.rotation)*rider.rotation*Quaternion.Euler(90,0,0);
                rightGripRotation=Quaternion.Inverse(rightPalmBone.rotation)*rider.rotation*Quaternion.Euler(90,0,0);
            }
            club = Instantiate(prefab, transform).transform;
            club.name = "EquippedClub";
            foreach (var collider in club.GetComponentsInChildren<Collider>(true)) collider.enabled = false;
            foreach (var part in club.GetComponentsInChildren<Transform>(true)) part.gameObject.isStatic = false;
            club.gameObject.SetActive(false);
        }

        public void ResetPose() { lastHand=1;if(club!=null)club.gameObject.SetActive(false); }
        public void Render(WeaponKind equipped, RiderMode mode, WeaponKind attackWeapon, int attackSide)
        {
            bool visible = equipped == WeaponKind.Club;
            club.gameObject.SetActive(visible);
            if (!visible) return;
            if (mode == RiderMode.Attacking && attackWeapon == WeaponKind.Club && attackSide != 0) lastHand = attackSide;
            var hand = lastHand < 0 ? leftPalmBone : rightPalmBone;
            if(skinnedHand)
            {
                club.SetPositionAndRotation(hand.TransformPoint(lastHand<0?leftGripOffset:rightGripOffset),hand.rotation*(lastHand<0?leftGripRotation:rightGripRotation));return;
            }
            // The authored forearm origin is the elbow; the palm is 28.5cm down its semantic axis.
            var palmOffset = skinnedHand ? new Vector3(0,-.04f,.01f) : new Vector3(lastHand * .01f, -.285f, .02f);
            club.SetPositionAndRotation(hand.TransformPoint(inverseModelBasis * palmOffset),
                hand.rotation * inverseModelBasis * Quaternion.Euler(90, 0, 0));
        }
    }
}
