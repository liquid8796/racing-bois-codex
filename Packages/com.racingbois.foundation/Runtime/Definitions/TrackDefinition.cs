using System;

namespace RacingBois.Gameplay.Definitions
{
    public readonly struct TrackSample
    {
        public readonly float CenterX, CenterY, CenterZ, ForwardX, ForwardY, ForwardZ;
        public readonly int CurvatureMicroRadiansPerMeter, GradePermille, RoadHalfWidthMillimeters;
        public TrackSample(float x, float y, float z, float forwardX, float forwardZ, int curvature, int grade, int width)
        {
            CenterX = x; CenterY = y; CenterZ = z;
            ForwardX = forwardX; ForwardY = grade / 1000f; ForwardZ = forwardZ;
            CurvatureMicroRadiansPerMeter = curvature; GradePermille = grade; RoadHalfWidthMillimeters = width;
        }
    }

    /// <summary>Immutable authored road-space data. Same course/level instance is shared by simulation and presentation.</summary>
    public sealed class TrackDefinition
    {
        private readonly int[] lengths, curves, grades;
        private readonly long[] starts;
        private readonly double[] startX, startY, startZ, startHeading;
        private static readonly TrackDefinition[,] courses = BuildAll();
        public static TrackDefinition Default => ForCourse(0, 0);
        public const long MaximumLengthMillimeters = 4000000;
        public int CourseIndex { get; }
        public int LevelIndex { get; }
        public long LengthMillimeters { get; }
        public int SectionCount => lengths.Length;
        public int RoadHalfWidthMillimeters => 6500;
        public int ShoulderWidthMillimeters => 2000;
        public int LaneCenterMillimeters => 3000;

        public static TrackDefinition ForCourse(int courseIndex, int levelIndex = 0)
        {
            if (courseIndex < 0 || courseIndex >= 5) throw new ArgumentOutOfRangeException(nameof(courseIndex));
            if (levelIndex < 0 || levelIndex >= 5) throw new ArgumentOutOfRangeException(nameof(levelIndex));
            return courses[courseIndex, levelIndex];
        }
        private static TrackDefinition[,] BuildAll()
        {
            // CLR type initialization publishes all 25 immutable definitions safely before any simulation or renderer can observe them.
            var result = new TrackDefinition[5, 5];
            for (int course = 0; course < 5; course++) for (int level = 0; level < 5; level++) result[course, level] = Author(course, level);
            return result;
        }
        private static TrackDefinition Author(int course, int level)
        {
            switch (course)
            {
                // Canyon L1 exactly preserves the P06 2.2 km centerline.
                case 0: return new TrackDefinition(course, level,
                    new[] {240,250,180,180,220,180,160,220,200,180,190},
                    new[] {0,4200,0,-7200,-2400,0,6500,2800,0,-4200,0},
                    new[] {0,25,80,-45,-40,10,65,-55,0,20,0});
                // Harbor frontage, warehouse bends and low ramps: neon-district-v1.png.
                case 1: return new TrackDefinition(course, level,
                    new[] {260,240,220,180,230,210,260,200,220,240,200},
                    new[] {0,3000,-3100,0,-4200,4300,0,3400,-3200,0,0},
                    new[] {0,0,15,0,-15,10,0,-10,5,-5,0});
                // Alpine shelf, alternating rock cuts and valley descents: ridge-pass-v1.png.
                case 2: return new TrackDefinition(course, level,
                    new[] {240,190,210,230,180,220,200,190,210,220,240},
                    new[] {0,5000,-6800,0,5800,-4700,0,3900,-4300,2700,0},
                    new[] {0,40,85,-30,-65,25,90,-80,20,-55,0});
                // Exposed clifftop sweep, level bridge approach and ocean-side descent: coastal-line-v1.png.
                case 3: return new TrackDefinition(course, level,
                    new[] {280,260,240,220,250,210,270,230,240,220,230},
                    new[] {0,3400,-2200,0,-3800,3600,0,2800,-3200,0,0},
                    new[] {0,25,40,-20,-35,0,0,30,-45,15,0});
                // Farm straights linked by rolling orchard bends: orchard-road-v1.png.
                case 4: return new TrackDefinition(course, level,
                    new[] {250,220,270,240,200,260,230,250,210,270,240},
                    new[] {0,-2600,3200,0,3500,-3700,0,-2900,3400,-1800,0},
                    new[] {0,20,-25,30,-15,20,-30,25,-20,10,0});
                default: throw new ArgumentOutOfRangeException(nameof(course));
            }
        }
        private TrackDefinition(int course, int level, int[] authoredLengths, int[] authoredCurves, int[] authoredGrades)
        {
            CourseIndex = course; LevelIndex = level;
            if (authoredLengths.Length != authoredCurves.Length || authoredLengths.Length != authoredGrades.Length || authoredLengths.Length < 3)
                throw new ArgumentException("Track section arrays differ.");
            lengths = new int[authoredLengths.Length]; curves = new int[lengths.Length]; grades = new int[lengths.Length];
            for (int i = 0; i < lengths.Length; i++)
            {
                // Higher levels expand each route and increase corner/grade demand; exact integer data travels in the content contract.
                lengths[i] = authoredLengths[i] * (100 + level * 4) / 100;
                curves[i] = authoredCurves[i] * (100 + level * 2) / 100;
                grades[i] = authoredGrades[i] * (100 + level * 2) / 100;
                if (lengths[i] < 100 || lengths[i] > 400 || Math.Abs(curves[i]) > 10000 || Math.Abs(grades[i]) > 100)
                    throw new ArgumentException("Authored track section is outside safe bounds.");
            }
            starts = new long[lengths.Length]; startX = new double[lengths.Length]; startY = new double[lengths.Length];
            startZ = new double[lengths.Length]; startHeading = new double[lengths.Length];
            double x = 0, y = 0, z = 0, heading = 0; long distance = 0;
            for (int i = 0; i < lengths.Length; i++)
            {
                starts[i] = distance; startX[i] = x; startY[i] = y; startZ[i] = z; startHeading[i] = heading;
                double curve = curves[i] / 1000000.0, length = lengths[i];
                if (curve == 0) { x += Math.Sin(heading) * length; z += Math.Cos(heading) * length; }
                else { x += (Math.Cos(heading) - Math.Cos(heading + curve * length)) / curve; z += (Math.Sin(heading + curve * length) - Math.Sin(heading)) / curve; }
                y += length * grades[i] / 1000.0; heading += curve * length; distance += lengths[i] * 1000L;
                // Constant curvature is monotonic in heading inside a section. Endpoint bounds prove forward-Z remains positive everywhere.
                if (Math.Abs(heading) >= 1.5) throw new ArgumentException("Route must remain longitudinally monotone.");
            }
            LengthMillimeters = distance;
            if (distance > MaximumLengthMillimeters || distance < 1500000) throw new ArgumentException("Track length outside production bounds.");
        }
        public long SectionStartMillimeters(int index)
        { if (index < 0 || index >= starts.Length) throw new ArgumentOutOfRangeException(nameof(index)); return starts[index]; }

        public int SectionIndex(long distance)
        {
            int section = starts.Length - 1;
            while (section > 0 && distance < starts[section]) section--;
            return section;
        }

        public int CurvatureAt(long distance) => curves[SectionIndex(distance)];
        public int GradeAt(long distance) => grades[SectionIndex(distance)];
        public int HeightMillimetersAt(long distance)
        {
            int section = SectionIndex(distance); int elevation = 0;
            for (int i = 0; i < section; i++) elevation += lengths[i] * grades[i];
            return elevation + (int)((distance - starts[section]) * grades[section] / 1000);
        }

        public TrackSample Sample(long distanceMillimeters)
        {
            int i = SectionIndex(distanceMillimeters);
            double length = (distanceMillimeters - starts[i]) / 1000.0, curve = curves[i] / 1000000.0;
            double heading = startHeading[i] + curve * length;
            double x = startX[i], z = startZ[i];
            if (curve == 0) { x += Math.Sin(heading) * length; z += Math.Cos(heading) * length; }
            else { x += (Math.Cos(startHeading[i]) - Math.Cos(heading)) / curve; z += (Math.Sin(heading) - Math.Sin(startHeading[i])) / curve; }
            return new TrackSample((float)x, (float)(startY[i] + length * grades[i] / 1000.0), (float)z,
                (float)Math.Sin(heading), (float)Math.Cos(heading), curves[i], grades[i], RoadHalfWidthMillimeters);
        }
    }
}
