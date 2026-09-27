// Development-only compression regression fixture, never a production Unity
// build converter. Preserve original Brotli files and write real gzip siblings.
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import crypto from "node:crypto";
import {fileURLToPath} from "node:url";
const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const web=fs.realpathSync(process.argv[2] || "");
const relative=path.relative(path.join(repo,"_local"),web);
if(!relative || relative.startsWith("..") || path.isAbsolute(relative)) throw new Error("Fixture conversion is restricted to a child of project _local.");
const index=path.join(web,"index.html");
let html=fs.readFileSync(index,"utf8");
const files=[];
for(const property of ["dataUrl","frameworkUrl","codeUrl"]){
  const match=new RegExp(property+"\\s*:\\s*['\"]([^'\"]+)['\"]").exec(html);
  if(!match || !match[1].endsWith(".br")) throw new Error("Expected previous-phase Brotli fixture payload for "+property);
  const input=path.resolve(web,match[1]);
  if(!input.startsWith(web+path.sep)) throw new Error("Payload escaped fixture web root.");
  const decoded=zlib.brotliDecompressSync(fs.readFileSync(input));
  const outputRelative=match[1].slice(0,-3)+".gz";
  const compressed=zlib.gzipSync(decoded,{level:9});
  fs.writeFileSync(path.join(web,outputRelative),compressed);
  html=html.replace(match[1],outputRelative);
  files.push({source:match[1],fixture:outputRelative,decodedBytes:decoded.length,
    decodedSha256:crypto.createHash("sha256").update(decoded).digest("hex"),
    gzipSha256:crypto.createHash("sha256").update(compressed).digest("hex")});
}
fs.writeFileSync(index,html);
console.log(JSON.stringify({scope:"Copied previous-phase test fixture transcoded to actual gzip; not a P05 build or browser acceptance",web,files}));
