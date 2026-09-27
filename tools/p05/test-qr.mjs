// Build-time QA only: encode with the exact vendored browser library, export
// matrices for decoding by an independent ZXing implementation. Not shipped.
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import {fileURLToPath} from "node:url";
const folder=path.dirname(fileURLToPath(import.meta.url));
const context={};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(folder,"lan/qrcodegen.js"),"utf8"),context);
const urls=["http://192.168.1.13:7777/","http://10.0.0.2:7777/","http://172.16.4.8:7787/","http://192.168.255.254:65535/"];
const cases=urls.map(url=>{
  const qr=context.qrcodegen.QrCode.encodeText(url,context.qrcodegen.QrCode.Ecc.MEDIUM);
  const modules=Array.from({length:qr.size},(_,y)=>Array.from({length:qr.size},(_,x)=>qr.getModule(x,y)?1:0));
  return {url,size:qr.size,version:qr.version,modules};
});
const destination=path.resolve(folder,"../../_local/p05-qr-matrices.json");
fs.writeFileSync(destination,JSON.stringify(cases));
console.log(JSON.stringify({generated:cases.length,destination,networkAPIsAvailable:false}));
