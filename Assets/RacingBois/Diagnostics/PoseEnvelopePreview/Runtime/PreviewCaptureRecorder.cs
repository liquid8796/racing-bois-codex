using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RacingBois.Diagnostics.PoseEnvelopePreview
{
    /// <summary>Explicit engine-camera requests. GPU readback is asynchronous; PNG encoding is deferred beyond motion comparisons.</summary>
    internal sealed class PreviewCaptureRecorder
    {
        private sealed class PendingImage{internal PreviewCapture record;internal byte[] rgba;}
        private readonly List<PendingImage> images=new List<PendingImage>();
        private readonly List<PreviewCapture> written=new List<PreviewCapture>();
        private readonly string output;private readonly double began;
        internal int Pending{get;private set;}internal string Failure{get;private set;}
        internal PreviewCapture[] Captures=>written.ToArray();
        internal bool EncodingComplete=>Pending==0&&written.Count==images.Count;
        internal PreviewCaptureRecorder(string output,double began){this.output=output;this.began=began;}
        internal void Request(Camera camera,PreviewEpisode episode,string variant,string stage,double after,Vector3 rider,Vector3 bike)
        {
            if(!SystemInfo.supportsAsyncGPUReadback)throw new InvalidOperationException("async_gpu_readback_required");
            const int width=1280,height=720;
            var target=RenderTexture.GetTemporary(width,height,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);
            var record=new PreviewCapture{episode=episode.id,variant=variant,stage=stage,unityFrame=Time.frameCount,width=width,height=height,
                requestWallSeconds=Time.realtimeSinceStartupAsDouble-began,afterSeconds=after,rider=rider,bike=bike,camera=camera.transform.position,
                file=episode.id+"--"+variant+"--"+stage+".png"};
            var pending=new PendingImage{record=record};images.Add(pending);Pending++;
            try
            {
                var request=new UniversalRenderPipeline.SingleCameraRequest{destination=target};
                if(!RenderPipeline.SupportsRenderRequest(camera,request))throw new InvalidOperationException("camera_request_unsupported");
                RenderPipeline.SubmitRenderRequest(camera,request);
                AsyncGPUReadback.Request(target,0,TextureFormat.RGBA32,result=>
                {
                    try
                    {
                        if(result.hasError){Failure="gpu_readback_failed";return;}
                        pending.rgba=result.GetData<byte>().ToArray();
                        if(pending.rgba.Length!=width*height*4){Failure="gpu_readback_size";return;}
                        record.readbackCompletedWallSeconds=Time.realtimeSinceStartupAsDouble-began;
                    }
                    catch(Exception error){Failure=error.GetType().Name;}
                    finally{Pending--;RenderTexture.ReleaseTemporary(target);}
                });
            }
            catch{Pending--;RenderTexture.ReleaseTemporary(target);throw;}
        }
        internal bool EncodeOne()
        {
            if(Pending!=0||written.Count==images.Count)return false;
            var image=images[written.Count];if(image.rgba==null)throw new InvalidOperationException(Failure??"capture_pixels_absent");
            bool varied=false;var pixels=image.rgba;
            for(int i=4;i<pixels.Length;i+=124)
                if(Math.Abs(pixels[i]-pixels[0])+Math.Abs(pixels[i+1]-pixels[1])+Math.Abs(pixels[i+2]-pixels[2])>20){varied=true;break;}
            if(!varied)throw new InvalidOperationException("uniform_camera_frame");
            var texture=new Texture2D(image.record.width,image.record.height,TextureFormat.RGBA32,false,false);
            try
            {
                texture.LoadRawTextureData(pixels);texture.Apply(false,false);byte[] png=texture.EncodeToPNG();
                string path=Path.Combine(output,image.record.file);
                using(var stream=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read))stream.Write(png,0,png.Length);
                image.record.bytes=png.Length;image.record.sha256=Digest(png);image.record.variedPixels=true;
                written.Add(image.record);image.rgba=null;return true;
            }
            finally{UnityEngine.Object.Destroy(texture);}
        }
        internal static string Digest(byte[] bytes)
        {using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
        internal static string DigestFile(string path)
        {using(var sha=SHA256.Create())using(var stream=File.OpenRead(path))return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
    }
}
