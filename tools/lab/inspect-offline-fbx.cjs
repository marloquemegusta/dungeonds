const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, 'FBX-Web-Renderer-offline.html'), 'utf8');
const bundle = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
function imageStub() {
 const handlers = {};
 return {addEventListener: (type,fn)=>handlers[type]=fn, removeEventListener(){}, set src(value){ if(handlers.load) handlers.load.call(this); }, width:1, height:1};
}
const context = {console, URL, Blob, TextDecoder, TextEncoder, Buffer, setTimeout, clearTimeout, performance, document:{
 createElement:()=>({relList:{supports:()=>true}}), createElementNS:()=>imageStub()
}, window:{URL}, self:{}, require};
const api = vm.runInNewContext(bundle.slice(0,bundle.indexOf('var tp=8')) + '\n({Loader:cf,Mixer:Ts,Box:hr,Vector:K,Group:Kn,Scene:er,normalize:Lf});',context);
const helperStart=bundle.indexOf('function isHorizontalRootPosition');
const helperEnd=bundle.indexOf('function setInPlaceStatus',helperStart);
const helpers=vm.runInNewContext(bundle.slice(helperStart,helperEnd)+'\n({apply:applyInPlaceMotion});',context);
const bytes=fs.readFileSync(process.argv[2]);
const model=new api.Loader().parse(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
new vm.Script(bundle); // Parse the complete browser script without running its UI.
const assert = require('node:assert/strict');
const scene = new api.Scene(), normalized = api.normalize(model, scene, 1);
const wrapper = normalized.wrapper;
let root; model.traverse(node=>{if(!root&&node.isBone&&!node.parent?.isBone)root=node;});
assert(root, 'No root bone in fixture');
for(const clip of model.animations) {
 const originals=clip.tracks.map(track=>track.values.slice());
 function sample(facing=0) {
  wrapper.rotation.y=-facing*Math.PI/4;
  const mixer=new api.Mixer(model); mixer.clipAction(clip).play();
  const result=Array.from({length:101},(_,i)=>{
   mixer.setTime(clip.duration*i/101);model.updateWorldMatrix(true,true);
   return root.getWorldPosition(new api.Vector()).toArray();
  });
  mixer.stopAllAction();mixer.uncacheRoot(model);
  return result;
 }
 function drift(samples) {const base=samples[0];return Math.max(...samples.map(p=>Math.hypot(p[0]-base[0],p[2]-base[2])));}
 const original=sample(),originalDrift=drift(original);
 // Reproduce the previous local-X/Z implementation on the same parsed FBX.
 for(const track of clip.tracks) if(track.name===root.name+'.position') {
  for(let i=0;i<track.times.length;i++){track.values[i*3]=track.values[0];track.values[i*3+2]=track.values[2];}
 }
 const previousDrift=drift(sample());
 clip.tracks.forEach((track,i)=>track.values.set(originals[i]));
 wrapper.rotation.y=0;
 const count=helpers.apply([clip],true,model);assert(count>0, 'No root tracks corrected');
 let maxDrift=0,maxHeightError=0;
 for(let facing=0;facing<8;facing++){
  const corrected=sample(facing);
  maxDrift=Math.max(maxDrift,drift(corrected));
  maxHeightError=Math.max(maxHeightError,...corrected.map((p,i)=>Math.abs(p[1]-original[i][1])));
 }
 assert(maxDrift<1e-5,'Horizontal root drift '+maxDrift);
 assert(maxHeightError<1e-5,'Vertical motion changed '+maxHeightError);
 helpers.apply([clip],false,model);
 clip.tracks.forEach((track,i)=>assert.deepEqual(Array.from(track.values),Array.from(originals[i]),'Original track restoration'));
 assert(Math.abs(drift(sample())-originalDrift)<1e-5,'Disabled mode did not restore locomotion');
 console.log(JSON.stringify({file:path.basename(process.argv[2]),clip:clip.name,samples:101,facings:8,originalDrift,previousDrift,correctedDrift:maxDrift,maxHeightError,restoration:'PASS',result:'PASS'}));
}
