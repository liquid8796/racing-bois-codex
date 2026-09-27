Shader "RacingBois/SoftParticle"
{
    Properties { _BaseMap("Shape",2D)="white"{} _DstBlend("Destination blend",Float)=10 }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" }
        Blend SrcAlpha [_DstBlend] ZWrite Off Cull Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            struct Attributes {float4 positionOS:POSITION;half4 color:COLOR;float2 uv:TEXCOORD0;};
            struct Varyings {float4 positionCS:SV_POSITION;half4 color:COLOR;float2 uv:TEXCOORD0;half fog:TEXCOORD1;};
            TEXTURE2D(_BaseMap);SAMPLER(sampler_BaseMap);
            Varyings vert(Attributes i){Varyings o;o.positionCS=TransformObjectToHClip(i.positionOS.xyz);o.color=i.color;o.uv=i.uv;o.fog=ComputeFogFactor(o.positionCS.z);return o;}
            half4 frag(Varyings i):SV_Target{half4 c=SAMPLE_TEXTURE2D(_BaseMap,sampler_BaseMap,i.uv)*i.color;c.rgb=MixFog(c.rgb,i.fog);return c;}
            ENDHLSL
        }
    }
}
