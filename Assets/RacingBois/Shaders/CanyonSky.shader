Shader "RacingBois/CanyonSky"
{
    Properties
    {
        _Zenith("Zenith", Color) = (0.13,0.32,0.53,1)
        _Horizon("Horizon", Color) = (0.72,0.72,0.67,1)
        _Ground("Ground", Color) = (0.29,0.24,0.18,1)
    }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" "RenderPipeline"="UniversalPipeline" }
        Cull Off ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 direction : TEXCOORD0; };
            CBUFFER_START(UnityPerMaterial)
            half4 _Zenith, _Horizon, _Ground;
            CBUFFER_END
            float hash21(float2 p){float3 p3=frac(float3(p.xyx)*.1031);p3+=dot(p3,p3.yzx+33.33);return frac((p3.x+p3.y)*p3.z);}
            float cloudNoise(float2 p){float2 a=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash21(a),hash21(a+float2(1,0)),f.x),lerp(hash21(a+float2(0,1)),hash21(a+1),f.x),f.y);}
            Varyings vert(Attributes v) { Varyings o; o.positionCS=TransformObjectToHClip(v.positionOS.xyz); o.direction=v.positionOS.xyz; return o; }
            half4 frag(Varyings i) : SV_Target
            {
                float3 d=normalize(i.direction);
                half3 sky=lerp(_Horizon.rgb,_Zenith.rgb,pow(saturate(d.y),.45));
                sky=lerp(sky,_Ground.rgb,saturate(-d.y*8));
                float2 p=d.xz/max(.05,d.y)*2.1;
                float cloud=cloudNoise(p)*.56+cloudNoise(p*2.03+17)*.29+cloudNoise(p*4.11-9)*.15;
                cloud=smoothstep(.56,.76,cloud)*smoothstep(.18,.36,d.y)*.52;
                sky=lerp(sky,half3(.91,.86,.75),cloud);
                float sun=pow(saturate(dot(d,normalize(float3(-.51,.46,-.73)))),900);
                sky+=half3(1,.69,.30)*sun*2;
                return half4(sky,1);
            }
            ENDHLSL
        }
    }
}
