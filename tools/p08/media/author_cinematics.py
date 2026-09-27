"""Author original real-time scene beats and emit an immutable Unity-free catalog.

Reference filename roles/durations are metadata only. No source video frames,
dialogue, actor identity, animation or camera data are imported.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/p08/media"
CATALOG = ROOT / "Assets/RacingBois/Client/Application/CinematicCatalog.cs"
CHARACTERS = ["Ash", "Juno", "Mako", "Rook", "Sol", "Vale", "Echo", "Kai"]
BIKES = ["Spark 450", "Kestrel", "Rift 250", "Jackal", "Ember", "Apex", "Corvus", "Viper", "Rift 750 N", "Specter", "Nightjar", "Cinder 10", "Rift 750", "Odyssey", "Havoc"]


# Every event vignette has its own dramatic problem, turn and resolution.
# Action tags map onto the existing authored rider animation set or directed
# gestures. Directors may not turn these into one repeated orbit with a caption.
STORIES = {
    "Busted": [
        ("A quiet shoulder", "A missed hand signal ends in an orderly stop.", [("Ride", "That light was meant for us."), ("Brake", "Easy. Shoulder first."), ("Dismount", "Engine off. Hands where I can see them."), ("Converse", "I saw the gap. I missed the sign."), ("Nod", "Read both next time."), ("Walk", "The road will still be here tomorrow.")]),
        ("The borrowed excuse", "A rider blames a helmet radio; their rival declines to play along.", [("Brake", "We are pulling over."), ("Point", "Your friend said the radio was broken."), ("Converse", "Only when it tells me to slow down."), ("Nod", "It was quite clear from my lane."), ("Rest", "That excuse needs a better mechanic."), ("Walk", "We will ride back together.")]),
        ("One last yellow line", "A confident pass is reviewed calmly beside the bikes.", [("Ride", "I thought the line had opened."), ("Brake", "It had not."), ("Point", "Look behind the bend, not just through it."), ("Converse", "You are right. I committed too early."), ("Nod", "Good. Start with that."), ("Remount", "Next pass, a clear view.")]),
        ("The audience leaves", "Spectators drift away while a rider accepts responsibility.", [("Brake", "The show is over."), ("Wave", "Give us a little room, please."), ("Dismount", "I made that everybody's problem."), ("Converse", "Then help make the shoulder safe."), ("Point", "Stand behind the guardrail."), ("Rest", "No applause needed.")]),
        ("No argument with a light", "A patrol check interrupts a private rivalry.", [("Ride", "We can settle this at the next straight."), ("Brake", "You can settle it after this stop."), ("Converse", "Neither of us was watching the mirror."), ("Nod", "Now you both are."), ("Point", "Two bikes. One safe way home."), ("Remount", "Truce until the garage.")]),
        ("A slower return", "The rider takes the consequence and helps clear the lane.", [("Brake", "Pull completely clear of the lane."), ("Walk", "I can move it from here."), ("Converse", "Thank you for keeping the road open."), ("Nod", "I should have done that sooner."), ("Point", "Take the service road back."), ("Ride", "Slow enough to notice it this time.")]),
    ],
    "Start": [
        ("Cold hands, warm engines", "A calm breath precedes the first launch.", [("Rest", "Hands loose."), ("Nod", "Eyes up."), ("LeanLeft", "Find your space."), ("Ride", "Make the first corner count.")]),
        ("A shared nod", "Two rivals acknowledge one another before leaving.", [("Converse", "Same road?"), ("Nod", "Different line."), ("LeanRight", "Leave me room."), ("Ride", "Always.")]),
        ("Wind check", "A crosswind changes the riders' starting positions.", [("Point", "Wind from the ridge."), ("LeanLeft", "Give the outside a little space."), ("Nod", "We have it."), ("Ride", "Go when it opens.")]),
        ("The quiet grid", "A noisy group becomes focused at the signal.", [("Wave", "Last jokes now."), ("Rest", "Then listen."), ("Nod", "There it is."), ("Ride", "Your road starts here.")]),
        ("One clean launch", "A rider avoids repeating an earlier stall.", [("Rest", "No hurry in the wrist."), ("LeanRight", "Feel the bite."), ("Nod", "That is it."), ("Ride", "Clean and gone.")]),
        ("Late light", "The final sunlight sets a warm tone for the race.", [("Point", "Catch that last light."), ("Nod", "Keep the sun out of the mirrors."), ("LeanLeft", "Clear left."), ("Ride", "See you at the far end.")]),
    ],
    "Win": [
        ("Room at the front", "The winner makes room for the rest of the group.", [("Ride", "There is the line."), ("Celebrate", "We made it."), ("Brake", "Keep the finish clear."), ("Wave", "Bring everyone through."), ("Converse", "Good run. Every one of you."), ("Nod", "There is room for all of us here.")]),
        ("A glove across the gap", "Two close competitors reconcile without a speech.", [("Brake", "That last bend was yours."), ("Dismount", "You nearly took it back."), ("OfferHandshake", "Next time?"), ("Nod", "Next time."), ("Celebrate", "Today was enough."), ("Rest", "Let the engines cool.")]),
        ("The line nobody saw", "A clever late line becomes the subject of a friendly debate.", [("Ride", "Where did you find that exit?"), ("Brake", "I stopped staring at your rear wheel."), ("Point", "The opening was right there."), ("Converse", "I was saving that lesson."), ("Celebrate", "Then consider it borrowed."), ("Nod", "Bring it back next race.")]),
        ("The long way pays", "Patience and an outside pass earn a celebration.", [("Ride", "You stayed outside the whole way."), ("Brake", "There was more room to breathe."), ("Dismount", "More road, too."), ("Converse", "Sometimes the long line is the clean one."), ("Celebrate", "I will remember that."), ("OfferHandshake", "Then it was a good race for both of us.")]),
        ("Crew first", "The rider redirects congratulations to the crew.", [("Brake", "Nice work out there."), ("Point", "Ask who fixed the rear brake."), ("Wave", "We only handed you a wrench."), ("Converse", "At exactly the right time."), ("Celebrate", "That counts."), ("Nod", "All right. We will take it.")]),
        ("The small victory", "The winner quietly checks on a rival before celebrating.", [("Brake", "You came in wide. Everything all right?"), ("Converse", "All right. Just out of road."), ("Nod", "There will be another one."), ("OfferHandshake", "And another chance to catch you."), ("Celebrate", "I look forward to it."), ("Rest", "One good finish at a time.")]),
    ],
    "Lose": [
        ("A better question", "The rider replaces an excuse with a useful question.", [("Brake", "I had more speed."), ("Rest", "At the wrong time."), ("Converse", "Where should I have waited?"), ("Point", "Before the road made the choice for you."), ("Nod", "Show me again.")]),
        ("One breath late", "A small hesitation is accepted and understood.", [("Brake", "I saw the gap close."), ("Dismount", "One breath too late."), ("Converse", "Next time, decide before you arrive."), ("Nod", "I know the feeling now."), ("Remount", "That is something to take home.")]),
        ("The patient rival", "A rival offers practical advice instead of gloating.", [("Brake", "You could say something."), ("Converse", "Your outside line was good."), ("Point", "Keep it one second longer."), ("Nod", "That is all?"), ("Rest", "That is plenty.")]),
        ("A mirror lesson", "Watching behind made the rider miss what was ahead.", [("Brake", "I kept checking your headlight."), ("Point", "Mine was not the road."), ("Converse", "Fair point."), ("Nod", "Find the exit first."), ("Remount", "Mirror second.")]),
        ("No shortcut home", "The rider chooses to practice the difficult section.", [("Brake", "Service road back?"), ("Point", "No. The ridge again."), ("Converse", "Even now?"), ("Nod", "Especially now."), ("Ride", "I will follow at an easier pace.")]),
        ("The empty boast", "A boast turns into a shared laugh and a new start.", [("Brake", "I may have promised too much."), ("Converse", "Only by an entire finish line."), ("Rest", "That sounds like me."), ("Nod", "Try a smaller promise."), ("Remount", "One cleaner corner.")]),
        ("A cool engine", "The rider learns to stop pushing a tired machine.", [("Brake", "It felt slower every mile."), ("Point", "Listen to it before you ask for more."), ("Dismount", "You earned a rest, little bike."), ("Nod", "So did you."), ("Rest", "We both needed to hear that.")]),
        ("Not the whole story", "A bad placing does not erase one good decision.", [("Brake", "Nothing went right."), ("Converse", "You gave that stopped car room."), ("Nod", "I would do that again."), ("Point", "Then keep that part."), ("Rest", "We can fix the rest.")]),
        ("The marker", "The rider chooses a concrete place to improve.", [("Brake", "Which corner?"), ("Point", "The one by the bent marker."), ("Converse", "I know it."), ("Nod", "Brake before the shadow next time."), ("Remount", "Before the shadow. Got it.")]),
        ("A finish worth keeping", "A difficult run becomes a foundation for future practice.", [("Ride", "You stayed with it all the way."), ("Brake", "It did not feel like enough."), ("Dismount", "Yesterday you would have turned back."), ("Converse", "Yesterday had an easier hill."), ("Nod", "And today had a steadier rider."), ("Point", "Keep today's line in your head."), ("Rest", "We will build on it.")]),
    ],
    "Wreck": [
        ("Count the important parts", "The rider checks themselves before the machine.", [("Fall", "Easy. Stay still for a moment."), ("Recover", "Hands. Knees. Breath."), ("Rest", "All accounted for."), ("Point", "Then we can look at the bike."), ("Walk", "In that order.")]),
        ("A careful lift", "The group coordinates a safe recovery.", [("Fall", "That is enough road for today."), ("Recover", "Can you stand?"), ("Walk", "Slowly."), ("Point", "One at the bars. One at the rear."), ("Converse", "On three, together."), ("Nod", "There. Nobody has to prove anything."), ("Rest", "Call it a ride home.")]),
        ("The missing hurry", "A rival refuses to rush a stranded rider.", [("Fall", "Go. You will lose the light."), ("Recover", "The light can wait."), ("Rest", "The finish cannot."), ("Converse", "Today it can."), ("Walk", "Come on. Shoulder first.")]),
        ("Listen to the silence", "The stopped engine gives space for an honest assessment.", [("Fall", "I heard it before I felt it."), ("Recover", "Then the next warning is worth hearing."), ("Point", "That wheel is done."), ("Converse", "So is the race."), ("Nod", "Not the rider."), ("Rest", "That is the part we keep.")]),
        ("A clean way out", "The rider prioritizes clearing the road.", [("Fall", "Someone is coming."), ("Recover", "Leave the machine for a moment."), ("Run", "Behind the barrier."), ("Point", "We are clear."), ("Rest", "Now we can plan.")]),
        ("Tomorrow's repair", "A damaged machine becomes a repair plan.", [("Fall", "That will need a long evening."), ("Recover", "Bars, brake, and a little patience."), ("Point", "Start with the brake."), ("Converse", "I will bring the lamp."), ("Nod", "Then we have a plan."), ("Rest", "Tomorrow, a better road.")]),
    ],
    "Level": [
        ("Past the first ridge", "The group sees a larger world after the first milestone.", [("Ride", "The old road looks smaller from here."), ("Brake", "It did its job."), ("Point", "There is a whole district past that ridge."), ("Converse", "And more people who know its corners."), ("Nod", "We will listen before we race."), ("Wave", "Pack light."), ("Ride", "Keep the good habits.")]),
        ("City rhythm", "A new route calls for different judgment.", [("Brake", "More windows. More crossings."), ("Point", "Less room for an old assumption."), ("Converse", "We learn the rhythm first."), ("Nod", "Then find our place in it."), ("Ride", "Welcome to the district.")]),
        ("Above the weather", "Climbing into thin air changes the riders' perspective.", [("Ride", "The air is colder up here."), ("Brake", "And the bends arrive faster."), ("Point", "Watch what the mountain hides."), ("Converse", "I will leave more room."), ("Nod", "For the road and each other."), ("Ride", "There is the next pass.")]),
        ("A line beside the sea", "A coast route brings crosswinds and open views.", [("Brake", "You can see forever."), ("Point", "Except behind that headland."), ("Converse", "I knew you would say that."), ("Nod", "Beautiful roads still need attention."), ("Ride", "Then let us give this one plenty.")]),
        ("Orchard light", "A familiar skill meets a quieter landscape.", [("Ride", "It smells different here."), ("Brake", "Fruit, dust, and somebody's supper."), ("Point", "Leave the farm gates clear."), ("Nod", "We are guests on this road."), ("Ride", "Let us act like it.")]),
        ("Beyond the last stamp", "A complete route card becomes an invitation to return.", [("Brake", "Every box has a mark."), ("Converse", "So what is left?"), ("Point", "All the things between the boxes."), ("Nod", "A quieter morning. A cleaner corner."), ("OfferHandshake", "A few people worth riding with."), ("Ride", "That should keep us busy.")]),
    ],
}

LONG_STORIES = {
    "Intro": ("A road with room", "A newcomer joins a loose crew and chooses a first route.", [
        ("Walk", "The garage opens before the city does."), ("Point", "A worn map covers the workbench."), ("Converse", "You are early."), ("Nod", "I did not want to miss the first ride."),
        ("Rest", "The first ride is mostly listening."), ("Inspect", "A loose mirror is tightened by hand."), ("Converse", "What do I need to know?"), ("Point", "Where you are going. Who is beside you."),
        ("Walk", "The crew rolls the bikes into the light."), ("OfferHandshake", "Names first. Lap times later."), ("Remount", "Ash waits until the last engine catches."), ("Nod", "Leave a little room for surprise."),
        ("Ride", "The city gives way to open ground."), ("LeanLeft", "The first bend asks a simple question."), ("LeanRight", "Nobody answers it quite the same way."), ("Ride", "Racing Bois. Find your own line.")]),
    "Duel": ("Two lines, one road", "A private rivalry develops through three trials, a mistake and a deliberate shared finish.", [
        ("Ride", "You always take the outside."), ("Brake", "You always notice."), ("Converse", "One clean run. No excuses."), ("Nod", "Three bends to the water tower."),
        ("Point", "The first bend rewards patience."), ("Remount", "Then I will try something new."), ("Ride", "They leave the shoulder together."), ("LeanLeft", "Ash waits half a breath longer."),
        ("LeanRight", "Juno finds daylight near the exit."), ("Ride", "Neither has a clear advantage."), ("Brake", "One each?"), ("Converse", "We have not reached the second bend."),
        ("Point", "A patch of gravel lies in the shadow."), ("Nod", "I see it."), ("Ride", "They spread out before the narrow section."), ("LeanRight", "Juno stays wide of the loose surface."),
        ("LeanLeft", "Ash gives up speed to keep a clean line."), ("Ride", "The gap opens, then settles."), ("Brake", "That was the right choice."), ("Converse", "It did not look like the fast choice."),
        ("Nod", "Sometimes those are different."), ("Point", "The tower is past the next crest."), ("Ride", "Both bikes climb toward the last turn."), ("LeanLeft", "Ash moves early and finds the apex."),
        ("LeanRight", "Juno carries a little too much entry speed."), ("Hit", "The rear tire skips at the shoulder."), ("Brake", "Ash hears the engine change."), ("Point", "You all right?"),
        ("Rest", "All right. Give me a moment."), ("Brake", "The finish waits beyond the tower."), ("Converse", "You could have had it."), ("Nod", "I still want a proper answer."),
        ("Remount", "Then another corner."), ("Ride", "They start together without a signal."), ("LeanLeft", "This time both riders leave room."), ("Ride", "The tower passes between their shadows."),
        ("Brake", "Too close to call."), ("OfferHandshake", "That sounds like another ride."), ("Converse", "Next time, you take the outside."), ("Nod", "Next time, you try waiting.")]),
    "Rival": ("Juno's unfinished map", "A rider's reputation gives way to the personal reason they return to the road.", [
        ("Walk", "Juno is still at the garage after the others leave."), ("Inspect", "A route card lies beside a cooling engine."), ("Converse", "You never put that card away."), ("Rest", "There is one section I never got right."),
        ("Point", "Here, where the road doubles back."), ("Nod", "It looks ordinary on paper."), ("Converse", "Most important places do."), ("Remount", "Will you show me?"),
        ("Ride", "They follow the river out of town."), ("LeanRight", "Juno takes the bends without hurry."), ("Point", "The old marker used to be there."), ("Brake", "I learned this road with my brother."),
        ("Rest", "He said the corner would make sense one morning."), ("Converse", "Did it?"), ("Nod", "Not while I was trying to prove him wrong."), ("Walk", "They stand above a quiet stretch of water."),
        ("Point", "The exit is visible from here."), ("Converse", "You cannot see it from the entry."), ("Nod", "You have to remember it."), ("Remount", "One more try, then."),
        ("Ride", "Juno rolls back to the start of the bend."), ("LeanLeft", "The bike settles before the apex."), ("LeanRight", "The remembered exit opens at the right moment."), ("Ride", "No sudden correction. No chase."),
        ("Brake", "That looked different."), ("Rest", "It felt quieter."), ("OfferHandshake", "A good morning for that corner."), ("Nod", "A good morning to bring someone along."),
        ("Point", "The card gains a small, careful mark."), ("Ride", "There are still roads left to learn.")]),
    "FinalWin": ("The road stays open", "Finishing the campaign becomes a shared moment and a return to ordinary riding.", [
        ("Ride", "The final marker slips behind the group."), ("Brake", "Nobody reaches for another lap time."), ("Dismount", "They leave space for the last rider."), ("Wave", "Every engine is accounted for."),
        ("Celebrate", "That is all five routes."), ("Converse", "And enough stories for the winter."), ("OfferHandshake", "Keep a few for the next rider."), ("Point", "The garage light is still on."),
        ("Remount", "Tomorrow, an easy road?"), ("Nod", "Tomorrow, a good one."), ("Ride", "There is no final corner."), ("Rest", "Racing Bois. Thanks for riding with us.")]),
}

SHOWCASE_FOCUS = [
    ("Compact confidence", "Short wheelbase, upright bars, a clean everyday stance."),
    ("Light over the crest", "A high front profile and narrow tail leave a nimble silhouette."),
    ("Small displacement, clear intent", "The light chassis keeps the mechanical layout readable."),
    ("Long shadow", "A low seat and forward fork establish a stretched cruiser profile."),
    ("Warm start", "An exposed frame and simple bodywork put the engine at the center."),
    ("A sharper horizon", "Full fairing and an aerodynamic tail define a fast touring shape."),
    ("Dark wing", "Angular side panels contrast with a compact instrument cluster."),
    ("Coiled energy", "A forward crouch and broad rear section communicate acceleration."),
    ("Pressure reserved", "Distinct intake and exhaust routing make the boosted variant legible."),
    ("Quiet speed", "A smooth outer shell gives way to detailed mechanical surfaces."),
    ("After sundown", "Raised controls and balanced proportions suit long late rides."),
    ("Heat signature", "A sculpted tank anchors an aggressive engine-forward silhouette."),
    ("An honest middleweight", "The unboosted design keeps its frame and breathing path exposed."),
    ("Distance in mind", "A longer seat and relaxed controls put endurance in the profile."),
    ("Built to be noticed", "A compact tail and strong front geometry give a muscular stance."),
]

ACTION_MAP = {"Brake": "Idle", "Dismount": "Run", "Point": "Converse", "Nod": "Converse",
              "Walk": "Run", "Wave": "Celebrate", "OfferHandshake": "Converse", "Rest": "Idle", "Recover": "Remount"}
SHOWCASE_SHOTS = [
    ["SideTrack", "FrontDetail", "EngineDetail", "CockpitDetail", "Wide"],
    ["FrontDetail", "WheelDetail", "TailDetail", "SideTrack", "HighReveal"],
    ["EngineDetail", "LowDetail", "CockpitDetail", "FrontDetail", "Wide"],
    ["WheelDetail", "SideTrack", "RearDetail", "TankDetail", "HighReveal"],
    ["EngineDetail", "TankDetail", "LowDetail", "SideTrack", "Wide"],
    ["FrontDetail", "SideTrack", "CockpitDetail", "TailDetail", "HighReveal"],
    ["HighReveal", "TankDetail", "FrontDetail", "EngineDetail", "Wide"],
    ["LowDetail", "TailDetail", "EngineDetail", "FrontDetail", "SideTrack"],
    ["EngineDetail", "FrontDetail", "RearDetail", "TankDetail", "HighReveal"],
    ["Wide", "FrontDetail", "SideTrack", "CockpitDetail", "TailDetail"],
    ["CockpitDetail", "SideTrack", "WheelDetail", "RearDetail", "HighReveal"],
    ["TankDetail", "LowDetail", "EngineDetail", "SideTrack", "Wide"],
    ["SideTrack", "EngineDetail", "RearDetail", "FrontDetail", "HighReveal"],
    ["CockpitDetail", "TankDetail", "TailDetail", "SideTrack", "Wide"],
    ["LowDetail", "FrontDetail", "TankDetail", "RearDetail", "HighReveal"],
]


def slug(text):
    return "-".join(text.lower().replace(",", "").replace("'", "").split())


def vector(x, y, z):
    return [round(x, 4), round(y, 4), round(z, 4)]


def make_beats(actions, duration, role, variant, bike):
    weights = [1 + min(len(text), 95) / 120 for _, text in actions]
    total = sum(weights)
    cursor = 0.0
    positions = {0: [-1.1, 0, -1.5], 1: [1.1, 0, .6], 2: [.8, 0, -4], 3: [3.3, 0, 1.5]}
    beats = []
    for index, ((action, text), weight) in enumerate(zip(actions, weights)):
        length = round(duration * weight / total, 4) if index < len(actions) - 1 else round(duration - cursor, 4)
        shot = ["Wide", "SideTrack", "FaceClose", "LowDetail", "OverShoulder", "HighReveal"][(index + variant) % 6]
        focus = 1 if role == "Rival" or (index % 3 == 1 and role in ["Duel", "Win", "Lose"]) else (2 if role == "Busted" and index % 2 else 0)
        actor_cues = []
        mask = 1 | (2 if role not in ["Showcase"] else 0) | (4 if role == "Busted" else 0) | (8 if role in ["Win", "Level", "FinalWin", "Intro"] else 0)
        for slot in range(4):
            if not mask & (1 << slot):
                continue
            start = list(positions[slot])
            actor_action = action if slot in [0, focus] else ("Ride" if action in ["Ride", "LeanLeft", "LeanRight"] else "Idle")
            delta = 2.2 if actor_action == "Ride" else (1.1 if actor_action in ["Walk", "Run"] else .2 if actor_action in ["LeanLeft", "LeanRight"] else 0)
            destination = list(start)
            if role == "Showcase":
                destination = start
            else:
                destination[2] += delta
            yaw = 12 if slot == 0 else (-18 if slot == 1 else 155 if slot == 2 else -65)
            actor_cues.append(dict(slot=slot, action=ACTION_MAP.get(actor_action, actor_action), direction_action=actor_action,
                                  visible=True, position_from=vector(*start), position_to=vector(*destination), yaw_from=yaw, yaw_to=yaw + (8 if actor_action in ["Point", "Wave", "Converse", "Nod"] else 0)))
            positions[slot] = destination
        target = positions[focus]
        tx, ty, tz = target[0], target[1] + (1.12 if shot not in ["LowDetail"] else .45), target[2]
        orbit_sign = -1 if (variant + index) % 2 else 1
        offsets = {"Wide": (6.8, 3.7, -8), "SideTrack": (4.7, 1.8, .5), "FaceClose": (1.45, 1.62, 2.6),
                   "LowDetail": (2.6, .55, -1.9), "OverShoulder": (-2.1, 2.2, -3.8), "HighReveal": (1, 6.7, -5.7)}
        ox, oy, oz = offsets[shot]
        if role == "Showcase":
            # Detail framing is tied to the reviewed bike design, with different
            # front/side/rear profiles and distinct feature narration per SKU.
            shot = SHOWCASE_SHOTS[bike][index % 5]
            detail_cameras = {"LowDetail": (2.2, .7, -2, .5, 0), "SideTrack": (3.5, 1.1, .4, .85, 0),
                              "FrontDetail": (.6, 1.1, 3, .95, .55), "RearDetail": (1.1, .9, -3, .6, -.65),
                              "Wide": (4.8, 2.5, -5, .85, 0), "HighReveal": (1.8, 4.8, -4, .8, 0),
                              "EngineDetail": (2.4, .6, .2, .5, -.15), "CockpitDetail": (1.0, 2.1, -1.9, 1.12, .42),
                              "TankDetail": (1.7, 1.9, -.2, 1.05, -.08), "TailDetail": (1.4, 1.05, -2.5, .8, -.6),
                              "WheelDetail": (1.5, .45, 2, .38, .76)}
            ox, oy, oz, height, forward = detail_cameras[shot]
            tx, ty, tz = -1.1, height, -1.5 + forward
        camera_from = vector(tx + ox * orbit_sign, oy, tz + oz)
        camera_to = vector(tx + ox * orbit_sign * .86 + (.13 * (bike % 3)), oy + (.12 if index % 2 else -.08), tz + oz * .91)
        beats.append(dict(index=index, start_seconds=round(cursor, 4), duration_seconds=length, shot=shot,
                          camera_from=camera_from, camera_to=camera_to, look_at_from=vector(tx, ty, tz), look_at_to=vector(tx, ty + .02, tz + (.45 if action == "Ride" else 0)),
                          fov_from=48 if shot not in ["Wide", "HighReveal"] else 57, fov_to=47 if shot not in ["Wide", "HighReveal"] else 54,
                          speaker_slot=focus, dialogue=text, participant_mask=mask, actors=actor_cues,
                          transition="Cut" if index % 3 else "Dissolve", transition_seconds=.18 if index else .25))
        cursor += length
    return beats


def cstring(value):
    return json.dumps(value, ensure_ascii=True)


def f(value):
    text = f"{float(value):.4f}".rstrip("0").rstrip(".")
    return text + "f"


def v(value):
    return "new CinematicPoint(" + ", ".join(f(x) for x in value) + ")"


HEADER = '''// Generated from docs/p08/media/cinematic-storyboards.json by tools/p08/media/author_cinematics.py.
// Original real-time direction. No reference video, actor animation or dialogue is embedded.
using System;
using System.Collections.Generic;

namespace RacingBois.Client.Application
{
    public enum CinematicRole { Showcase, Busted, Start, Win, Lose, Wreck, Level, Intro, Duel, Rival, FinalWin }

    public readonly struct CinematicPoint
    {
        public float X { get; }
        public float Y { get; }
        public float Z { get; }
        public CinematicPoint(float x, float y, float z) { X = x; Y = y; Z = z; }
    }

    public sealed class CinematicActorCue
    {
        public int Slot { get; }
        public string Action { get; }
        public CinematicPoint PositionFrom { get; }
        public CinematicPoint PositionTo { get; }
        public float YawFrom { get; }
        public float YawTo { get; }
        public bool Visible { get; }
        public CinematicActorCue(int slot, string action, CinematicPoint from, CinematicPoint to, float yawFrom, float yawTo, bool visible)
        { Slot = slot; Action = action; PositionFrom = from; PositionTo = to; YawFrom = yawFrom; YawTo = yawTo; Visible = visible; }
    }

    public sealed class CinematicBeat
    {
        public float StartSeconds { get; }
        public float DurationSeconds { get; }
        public float EndSeconds => StartSeconds + DurationSeconds;
        public string Shot { get; }
        public CinematicPoint CameraFrom { get; }
        public CinematicPoint CameraTo { get; }
        public CinematicPoint LookAtFrom { get; }
        public CinematicPoint LookAtTo { get; }
        public float FieldOfViewFrom { get; }
        public float FieldOfViewTo { get; }
        public int SpeakerSlot { get; }
        public string Dialogue { get; }
        public int ParticipantMask { get; }
        public string Transition { get; }
        public float TransitionSeconds { get; }
        public IReadOnlyList<CinematicActorCue> Actors { get; }
        public CinematicBeat(float start, float duration, string shot, CinematicPoint cameraFrom, CinematicPoint cameraTo,
            CinematicPoint lookFrom, CinematicPoint lookTo, float fovFrom, float fovTo, int speaker, string dialogue,
            int participants, string transition, float transitionSeconds, params CinematicActorCue[] actors)
        { StartSeconds=start; DurationSeconds=duration; Shot=shot; CameraFrom=cameraFrom; CameraTo=cameraTo;
          LookAtFrom=lookFrom; LookAtTo=lookTo; FieldOfViewFrom=fovFrom; FieldOfViewTo=fovTo; SpeakerSlot=speaker;
          Dialogue=dialogue; ParticipantMask=participants; Transition=transition; TransitionSeconds=transitionSeconds;
          Actors=Array.AsReadOnly((CinematicActorCue[])actors.Clone()); }
    }

    public sealed class CinematicDefinition
    {
        public string Id { get; }
        public string Title { get; }
        public string Synopsis { get; }
        public CinematicRole Role { get; }
        public int Variant { get; }
        public float DurationSeconds { get; }
        public int BikeIndex { get; }
        public int CharacterIndex { get; }
        public string MusicId { get; }
        public string AudioId => MusicId;
        public IReadOnlyList<CinematicBeat> Beats { get; }
        public CinematicDefinition(string id, string title, string synopsis, CinematicRole role, int variant, float duration,
            int bikeIndex, int characterIndex, string musicId, params CinematicBeat[] beats)
        { Id=id; Title=title; Synopsis=synopsis; Role=role; Variant=variant; DurationSeconds=duration;
          BikeIndex=bikeIndex; CharacterIndex=characterIndex; MusicId=musicId; Beats=Array.AsReadOnly((CinematicBeat[])beats.Clone()); }
    }

    public static class CinematicCatalog
    {
        public const int Version = 1;
        public const int Count = 59;
        private static readonly CinematicDefinition[] entries = {
'''

FOOTER = '''        };
        public static IReadOnlyList<CinematicDefinition> All { get; } = Array.AsReadOnly(entries);
        public static bool TryGet(string id, out CinematicDefinition definition)
        {
            foreach (var candidate in entries)
                if (string.Equals(candidate.Id, id, StringComparison.Ordinal)) { definition=candidate; return true; }
            definition=null; return false;
        }
        public static CinematicDefinition Get(string id)
        { if (TryGet(id, out var definition)) return definition; throw new ArgumentException("Unknown cinematic ID.", nameof(id)); }
        public static IReadOnlyList<CinematicDefinition> ForRole(CinematicRole role)
        { var result = new List<CinematicDefinition>(); foreach (var item in entries) if (item.Role==role) result.Add(item); return result.AsReadOnly(); }
        public static CinematicDefinition ForEvent(CinematicRole role, int variant)
        {
            var matches=ForRole(role);
            if (matches.Count==0) throw new ArgumentOutOfRangeException(nameof(role));
            return matches[(variant & int.MaxValue) % matches.Count];
        }
    }
}
'''


def emit_cs(definitions):
    lines = [HEADER]
    for item in definitions:
        lines.append("            new CinematicDefinition(" + ", ".join([cstring(item["id"]), cstring(item["title"]), cstring(item["synopsis"]), "CinematicRole." + item["role"], str(item["variant"]), f(item["duration_seconds"]), str(item["bike_index"]), str(item["character_index"]), cstring(item["music_id"])]) + ",")
        for i, beat in enumerate(item["beats"]):
            scalars = [f(beat["start_seconds"]), f(beat["duration_seconds"]), cstring(beat["shot"]), v(beat["camera_from"]), v(beat["camera_to"]), v(beat["look_at_from"]), v(beat["look_at_to"]), f(beat["fov_from"]), f(beat["fov_to"]), str(beat["speaker_slot"]), cstring(beat["dialogue"]), str(beat["participant_mask"]), cstring(beat["transition"]), f(beat["transition_seconds"])]
            lines.append("                new CinematicBeat(" + ", ".join(scalars) + ",")
            for j, actor in enumerate(beat["actors"]):
                args = [str(actor["slot"]), cstring(actor["action"]), v(actor["position_from"]), v(actor["position_to"]), f(actor["yaw_from"]), f(actor["yaw_to"]), "true" if actor["visible"] else "false"]
                suffix = ")" if j == len(beat["actors"]) - 1 else ","
                if j == len(beat["actors"]) - 1:
                    suffix += ")," if i == len(item["beats"]) - 1 else ","
                lines.append("                    new CinematicActorCue(" + ", ".join(args) + ")" + suffix)
    lines.append(FOOTER)
    return "\n".join(lines)


def main():
    source = json.loads((ROOT / "docs/p08/content/reference-baseline.json").read_text(encoding="utf-8"))["data"]
    meta = {r["path"]: float(r["format"]["duration"]) for r in source["media"]}
    groups = {}
    for row in source["manifest"]:
        if row["category"] == "VIDEO":
            groups.setdefault(row["sha256"], []).append(row["path"])
    counters = {}; showcase = 0; definitions = []
    role_music = {"Showcase": "neon-receipt", "Busted": "last-light-repair", "Start": "found-the-line", "Win": "after-the-flag", "Lose": "blueprint-lull", "Wreck": "quiet-pitlane", "Level": "meridian-lobby", "Intro": "paddock-sunrise", "Duel": "two-lane-covenant", "Rival": "rival-frequency", "FinalWin": "safe-passage"}
    for aliases in sorted(groups.values(), key=lambda items: items[0]):
        path = aliases[0]
        stem = Path(path).stem
        if len(path.split("/")) == 3:
            role = "Showcase"
        elif stem.startswith("BUSTED"):
            role = "Busted"
        elif stem.startswith("FINALWIN"):
            role = "FinalWin"
        elif stem == "JESSIE":
            role = "Rival"
        else:
            role = ''.join(c for c in stem if not c.isdigit()).title()
        variant = counters.get(role, 0); counters[role] = variant + 1
        duration = math.ceil(meta[path] * 2) / 2
        bike = showcase if role == "Showcase" else (variant * 3 + len(role)) % 15
        if role == "Showcase":
            feature, description = SHOWCASE_FOCUS[showcase]
            title, synopsis = BIKES[showcase] + " / " + feature, description
            actions = [("Inspect", BIKES[showcase]), ("Inspect", feature), ("Inspect", "Chassis and controls."), ("Inspect", "Built for your next line."), ("Rest", "Your ride. Your choice.")]
            identity = "rb-showcase-" + slug(BIKES[showcase])
            showcase += 1
        elif role in LONG_STORIES:
            title, synopsis, actions = LONG_STORIES[role]
            identity = "rb-" + role.lower() + "-" + slug(title)
        else:
            title, synopsis, actions = STORIES[role][variant]
            identity = "rb-" + role.lower() + "-" + slug(title)
        definitions.append(dict(id=identity, title=title, synopsis=synopsis, role=role, variant=variant,
                                duration_seconds=duration, bike_index=bike, character_index=1 if role == "Rival" else variant % 8,
                                music_id=role_music[role], skip_policy="Always user-skippable; no authoritative reward/state changes inside the director.",
                                source_reference_files=aliases, source_reference_sha256=next(r["sha256"] for r in source["manifest"] if r["path"] == path),
                                source_reference_duration_seconds=meta[path], source_mapping_confidence="Source filename-family and duration mapping; exact source event branches/SPEC-to-video association remain unproven.",
                                production_state="AUTHORED_DIRECTION_RUNTIME_QA_PENDING", beats=make_beats(actions, duration, role, variant, bike)))
    assert len(definitions) == 59 and sum(d["duration_seconds"] for d in definitions) >= 1660
    payload = dict(schema=1, authoring="Original new story, text, staging and cameras; generated declarative sequences for actual real-time 3D assets. No source-video pixels or camera data imported.",
                   actor_slots={"0": "hero", "1": "rival", "2": "patrol", "3": "crew"},
                   coordinate_contract="Unity meters, +Y up, +Z road forward; camera and actor positions relative to director stage origin.",
                   role_counts=counters, sequence_count=59, total_seconds=sum(d["duration_seconds"] for d in definitions),
                   source_deduplicated_minimum_seconds=1660, definitions=definitions)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cinematic-storyboards.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CATALOG.write_text(emit_cs(definitions), encoding="utf-8", newline="\n")
    (OUT / "cinematic-catalog-receipt.json").write_text(json.dumps(dict(schema=1, sequence_count=59, total_seconds=payload["total_seconds"], beat_count=sum(len(d["beats"]) for d in definitions),
        role_counts=counters, generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        storyboards_sha256=hashlib.sha256((OUT / "cinematic-storyboards.json").read_bytes()).hexdigest(),
        catalog_path=CATALOG.relative_to(ROOT).as_posix(), catalog_sha256=hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
        runtime_director_qa="PENDING", visual_playback_qa="PENDING", source_event_equivalence="UNPROVEN"), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(sequences=len(definitions), beats=sum(len(d["beats"]) for d in definitions), total_seconds=payload["total_seconds"], roles=counters)))


if __name__ == "__main__":
    main()
