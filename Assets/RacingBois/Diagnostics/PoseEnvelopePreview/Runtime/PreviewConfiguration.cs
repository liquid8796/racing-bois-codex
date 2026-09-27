using System;
using System.Collections.Generic;
using System.IO;

namespace RacingBois.Diagnostics.PoseEnvelopePreview
{
    public sealed class PreviewConfiguration
    {
        public const double MaximumRunSeconds=100;
        public bool Enabled,Include20;public string Output="",ExpectedFingerprint="";
        public static PreviewConfiguration Parse(string[] args)
        {
            var value=new PreviewConfiguration();var seen=new HashSet<string>(StringComparer.Ordinal);
            for(int i=0;i<args.Length;i++)
            {
                string key=args[i];if(!key.StartsWith("--rb-pose-",StringComparison.Ordinal))continue;
                if(!seen.Add(key))throw new ArgumentException("duplicate_preview_option");
                if(key=="--rb-pose-preview"){value.Enabled=true;continue;}
                if(key=="--rb-pose-include20"){value.Include20=true;continue;}
                if(i+1>=args.Length)throw new ArgumentException("missing_preview_value");
                switch(key)
                {
                    case "--rb-pose-output":value.Output=args[++i];break;
                    case "--rb-pose-fingerprint":value.ExpectedFingerprint=args[++i];break;
                    default:throw new ArgumentException("unknown_preview_option");
                }
            }
            if(!value.Enabled){if(seen.Count!=0)throw new ArgumentException("preview_opt_in_required");return value;}
            if(string.IsNullOrWhiteSpace(value.Output)||!Path.IsPathRooted(value.Output))throw new ArgumentException("absolute_fresh_output_required");
            value.Output=Path.GetFullPath(value.Output);
            if(Directory.Exists(value.Output)||File.Exists(value.Output))throw new ArgumentException("output_must_not_exist");
            string parent=Path.GetDirectoryName(value.Output)??throw new ArgumentException("output_parent_required");
            for(var p=new DirectoryInfo(parent);p!=null;p=p.Parent)
                if(p.Exists&&(p.Attributes&FileAttributes.ReparsePoint)!=0)throw new ArgumentException("output_reparse_point");
            if(value.ExpectedFingerprint==null||value.ExpectedFingerprint.Length!=64)throw new ArgumentException("fingerprint_required");
            foreach(char c in value.ExpectedFingerprint)if(!Uri.IsHexDigit(c))throw new ArgumentException("invalid_fingerprint");
            value.ExpectedFingerprint=value.ExpectedFingerprint.ToLowerInvariant();return value;
        }
    }
}
