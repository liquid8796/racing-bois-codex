using System;

namespace RacingBois.Tools.NativeUi
{
    /// <summary>Float32 arithmetic allowance, capped at one thousandth of an output pixel.</summary>
    internal static class TextFit
    {
        internal const int CoordinateUlps = 4;
        internal const double MaximumOutputPixelError = 0.001;
        internal readonly struct Result
        {
            internal readonly bool Valid, Fits;
            internal readonly double SignedDifference, CoordinateUlp, RoundingBound, PixelDifference, PixelBound;
            internal Result(bool valid, bool fits, double difference, double ulp, double bound, double pixelScale)
            { Valid=valid; Fits=fits; SignedDifference=difference; CoordinateUlp=ulp; RoundingBound=bound;
              PixelDifference=difference*pixelScale; PixelBound=bound*pixelScale; }
        }
        internal static bool Finite(double value) => !double.IsNaN(value) && !double.IsInfinity(value);
        internal static double Float32Ulp(float value)
        {
            int bits=BitConverter.SingleToInt32Bits(Math.Abs(value));
            int exponent=(bits>>23)&255;
            return exponent==255 ? double.NaN : Math.Pow(2, exponent==0 ? -149 : exponent-150);
        }
        internal static Result Compare(float measured, float available, float coordinateScale, double outputPixelsPerLogicalUnit)
        {
            bool valid=Finite(measured)&&Finite(available)&&Finite(coordinateScale)&&Finite(outputPixelsPerLogicalUnit)
                && measured>=0 && available>0 && coordinateScale>=0 && outputPixelsPerLogicalUnit>0;
            if(!valid)return new Result(false,false,0,0,0,0);
            double difference=(double)measured-available;
            float magnitude=Math.Max(1,Math.Max(coordinateScale,Math.Max(measured,available)));
            double ulp=Float32Ulp(magnitude);
            double bound=Math.Min(CoordinateUlps*ulp,MaximumOutputPixelError/outputPixelsPerLogicalUnit);
            return new Result(true,difference<=bound,difference,ulp,bound,outputPixelsPerLogicalUnit);
        }
    }
}
