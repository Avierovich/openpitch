const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "W", width: 13.33, height: 7.5 });
p.layout = "W";

const BG="0F1320", PANEL="171C2E", LINE="232A40", TEAL="2E7D6F", MINT="7FD1C1",
      GOLD="E3B341", FG="E8ECF5", MUT="9AA3B8", RED="F0776A";
const H="Consolas", B="Calibri";
const W=13.33;

function slide(){ const s=p.addSlide(); s.background={color:BG}; return s; }
function chip(s,t,x,y){ s.addText(t,{x,y,w:3,h:0.3,fontFace:H,fontSize:11,color:MINT,charSpacing:2}); }
function foot(s,n){ s.addText("OpenPitch  ·  open · MCP-native · zero-cost",{x:0.5,y:7.05,w:9,h:0.3,fontFace:H,fontSize:9,color:MUT});
  s.addText(String(n),{x:12.4,y:7.05,w:0.5,h:0.3,fontFace:H,fontSize:9,color:MUT,align:"right"}); }
function title(s,t){ s.addText(t,{x:0.5,y:0.55,w:12.3,h:0.9,fontFace:H,fontSize:30,bold:true,color:FG}); }
function panel(s,x,y,w,h,fill=PANEL){ s.addShape(p.ShapeType.roundRect,{x,y,w,h,fill:{color:fill},line:{color:LINE,width:1},rectRadius:0.08}); }
function stat(s,x,y,w,num,lab,col=MINT){ panel(s,x,y,w,1.7);
  s.addText(num,{x:x+0.15,y:y+0.2,w:w-0.3,h:0.9,fontFace:H,fontSize:34,bold:true,color:col});
  s.addText(lab,{x:x+0.15,y:y+1.12,w:w-0.3,h:0.45,fontFace:B,fontSize:12,color:MUT}); }

// 1 — Title
let s=slide();
s.addText("›_",{x:0.5,y:1.5,w:1.5,h:0.8,fontFace:H,fontSize:40,bold:true,color:TEAL});
s.addText("OpenPitch",{x:0.5,y:2.2,w:12,h:1.1,fontFace:H,fontSize:64,bold:true,color:MINT});
s.addText("The open, real-time intelligence layer for AI startups —\nthat any agent can build on.",
  {x:0.5,y:3.4,w:12,h:1,fontFace:B,fontSize:22,color:FG,lineSpacingMultiple:1.1});
panel(s,0.5,4.7,12.3,1.1,PANEL);
s.addText([{text:"› openpitch  get anthropic --arr\n",options:{color:TEAL}},
  {text:"  ARR ~$47B  [reported · medium]  ·  source: CNBC 2026-05-28  ·  ⚑ discrepancy flagged",options:{color:FG}}],
  {x:0.7,y:4.85,w:11.9,h:0.8,fontFace:H,fontSize:13});
s.addText("A free, open alternative to PitchBook & CB Insights — focused on the AI companies VCs care about.",
  {x:0.5,y:6.0,w:12,h:0.4,fontFace:B,fontSize:13,italic:true,color:MUT});
foot(s,1);

// 2 — Problem
s=slide(); title(s,"Private-market data is expensive — and stale.");
chip(s,"THE PROBLEM",0.5,0.3);
stat(s,0.5,1.7,3.9,"$20k–100k","per seat / year",GOLD);
stat(s,4.7,1.7,3.9,"weeks–months","data latency",GOLD);
stat(s,8.9,1.7,3.9,"2–4×","AI-startup growth / yr",MINT);
panel(s,0.5,3.7,12.3,2.8);
s.addText([
  {text:"Incumbents are accurate because they're human-verified — which makes them slow and costly.\n\n",options:{color:FG,bold:true}},
  {text:"• For a company tripling yearly, a figure verified 6 months ago can be off by multiples.\n",options:{color:FG}},
  {text:"• The real numbers are already public — founders state ARR on podcasts, filings disclose raises,\n   hiring reveals growth — just scattered, unstructured, and contradictory.\n",options:{color:FG}},
  {text:"• That's exactly the problem an AI agent is built to solve.",options:{color:MINT}},
],{x:0.8,y:3.95,w:11.7,h:2.3,fontFace:B,fontSize:16,lineSpacingMultiple:1.15,valign:"top"});
foot(s,2);

// 3 — Proof / the hook
s=slide(); title(s,"Proof of the problem: our own seed went stale in 5 months.");
chip(s,"WHY THIS EXISTS",0.5,0.3);
const rows=[["Company","~Jan 2026","Jun 2026","Δ"],
 ["OpenAI valuation","$300B","$852B","2.8×"],
 ["Anthropic valuation","$60B","$965B","16×"],
 ["Anthropic ARR","$4–5B","$47B","~10×"],
 ["Cursor valuation","$9B","$50B","5.5×"],
 ["Cognition ARR","$73M","$492M","6.7×"]];
let ty=1.75;
rows.forEach((r,i)=>{ const head=i===0; panel(s,0.5,ty,8.3,0.62,head?PANEL:BG);
  ["0.6","4.0","6.2","7.6"]; const xs=[0.7,3.6,5.6,7.6], ws=[3.0,2.0,2.0,1.1];
  r.forEach((c,j)=>s.addText(c,{x:xs[j],y:ty+0.06,w:ws[j],h:0.5,fontFace:head?H:B,fontSize:head?13:15,bold:head||j===3,color:head?MUT:(j===3?GOLD:FG)}));
  ty+=0.66; });
panel(s,9.1,1.75,3.7,3.9,"131826");
s.addText("Incumbent-grade data goes stale in months.",{x:9.3,y:2.1,w:3.4,h:1.2,fontFace:H,fontSize:20,bold:true,color:MINT});
s.addText("OpenPitch refreshes it daily, every figure sourced and confidence-scored.",
  {x:9.3,y:3.5,w:3.4,h:1.6,fontFace:B,fontSize:15,color:FG});
s.addText("Latency, not coverage — that's the wedge incumbents structurally can't close.",
  {x:0.5,y:6.0,w:12,h:0.5,fontFace:B,fontSize:14,italic:true,color:MUT});
foot(s,3);

// 4 — What it is
s=slide(); title(s,"Sourced, confidence-scored intelligence — inside your agent.");
chip(s,"WHAT IT IS",0.5,0.3);
const pil=[["Every number sourced","Podcast timestamp, filing, or article — no black-box figures."],
 ["Confidence-scored","Source reliability × speaker × corroboration × freshness (decays with age)."],
 ["In your agent (MCP/A2A)","Ask Claude Code or Codex directly — no website, no key, no signup."]];
pil.forEach((c,i)=>{ const x=0.5+i*4.15; panel(s,x,1.75,3.9,2.4);
  s.addShape(p.ShapeType.ellipse,{x:x+0.25,y:2.0,w:0.5,h:0.5,fill:{color:TEAL}});
  s.addText(String(i+1),{x:x+0.25,y:2.02,w:0.5,h:0.46,fontFace:H,fontSize:16,bold:true,color:FG,align:"center"});
  s.addText(c[0],{x:x+0.25,y:2.65,w:3.4,h:0.5,fontFace:H,fontSize:15,bold:true,color:MINT});
  s.addText(c[1],{x:x+0.25,y:3.2,w:3.45,h:0.8,fontFace:B,fontSize:13,color:FG}); });
panel(s,0.5,4.45,12.3,2.0);
s.addText([{text:'› "What is Cognition\'s ARR — with sources and confidence?"\n\n',options:{color:TEAL}},
 {text:"  ARR  $492M  [reported · medium]  as of 2026-05  ·  source: Sacra  ·  +573% YoY",options:{color:FG}}],
 {x:0.75,y:4.7,w:11.8,h:1.5,fontFace:H,fontSize:15,valign:"top"});
foot(s,4);

// 5 — How it works
s=slide(); title(s,"How it works — git is the database, runs on free CI.");
chip(s,"ARCHITECTURE",0.5,0.3);
const steps=["Sources\npodcasts · filings\nnews · web","Extract\nLLM → claims","Derive\nidentities +\nvalidation","Reconcile\nconsensus +\ncontradictions","Publish\nJSON · history\nevents · digest"];
steps.forEach((t,i)=>{ const x=0.5+i*2.5; panel(s,x,2.0,2.25,1.7,PANEL);
  s.addText(t,{x:x+0.1,y:2.15,w:2.05,h:1.4,fontFace:H,fontSize:12.5,color:FG,align:"center",valign:"middle",lineSpacingMultiple:1.05});
  if(i<4) s.addText("›",{x:x+2.28,y:2.5,w:0.22,h:0.6,fontFace:H,fontSize:24,bold:true,color:TEAL,align:"center"}); });
panel(s,0.5,4.1,12.3,1.0,"131826");
s.addText("Daily on free GitHub Actions  →  commits versioned data  →  the git log IS the audit trail.",
  {x:0.7,y:4.3,w:11.9,h:0.6,fontFace:B,fontSize:15,color:MINT});
const ifc=["MCP server (local, BYO agent)","Static dashboard","Event feed + A2A agent"];
ifc.forEach((t,i)=>{ const x=0.5+i*4.15; panel(s,x,5.3,3.9,1.0,PANEL);
  s.addText(t,{x:x+0.15,y:5.5,w:3.6,h:0.6,fontFace:H,fontSize:13,color:FG,align:"center",valign:"middle"}); });
foot(s,5);

// 6 — The edge
s=slide(); title(s,"The edge nobody else has: it reasons about the numbers.");
chip(s,"DIFFERENTIATOR",0.5,0.3);
panel(s,0.5,1.75,6.0,4.5);
s.addText("⚑  Contradiction detection",{x:0.75,y:2.0,w:5.5,h:0.5,fontFace:H,fontSize:18,bold:true,color:GOLD});
s.addText([{text:"When public sources disagree, it flags it — neutrally.\n\n",options:{color:FG}},
 {text:"Mistral valuation:\n",options:{color:MUT}},
 {text:"  $13B confirmed (Series C)  vs  $23B rumored\n  → public-source discrepancy ⚑",options:{color:FG}}],
 {x:0.75,y:2.6,w:5.5,h:2.0,fontFace:H,fontSize:14,lineSpacingMultiple:1.1});
s.addText("Screenshot-worthy, defensible, and unique to OpenPitch.",{x:0.75,y:5.4,w:5.5,h:0.7,fontFace:B,fontSize:13,italic:true,color:MUT});
panel(s,6.8,1.75,6.0,4.5);
s.addText("Σ  Derivation / triangulation",{x:7.05,y:2.0,w:5.5,h:0.5,fontFace:H,fontSize:18,bold:true,color:MINT});
s.addText([{text:"Reverse-engineers metrics like an analyst:\n\n",options:{color:FG}},
 {text:"  ARR = MRR × 12\n  valuation = round ÷ equity %\n  ARR = subscribers × ACV\n  revenue multiple = valuation ÷ ARR\n\n",options:{color:FG}},
 {text:"Derived values cross-check reported ones —\nso fabricated numbers get caught.",options:{color:MUT}}],
 {x:7.05,y:2.6,w:5.5,h:3.2,fontFace:H,fontSize:14,lineSpacingMultiple:1.1});
foot(s,6);

// 7 — Competitive
s=slide(); title(s,"Complementary, not a clone — we win a narrow wedge.");
chip(s,"LANDSCAPE",0.5,0.3);
const cols=["","PitchBook /\nCB Insights","Crunchbase","OpenBB","OpenPitch"];
const cmp=[["Free & open","✗","◐","✓","✓"],["Daily freshness","✗","◐","◐","✓"],
 ["In your agent (MCP)","✗","✗","✓","✓"],["Every figure sourced","◐","◐","✗","✓"],
 ["Contradiction detection","✗","✗","✗","✓"],["AI-startup focus","◐","◐","✗","✓"]];
const cx=[0.5,4.3,6.5,8.6,10.7], cw=[3.7,2.1,2.0,2.0,2.4];
cols.forEach((c,j)=>{ panel(s,cx[j],1.7,cw[j],0.65,j===4?TEAL:PANEL);
  s.addText(c,{x:cx[j]+0.05,y:1.72,w:cw[j]-0.1,h:0.61,fontFace:H,fontSize:11,bold:true,color:FG,align:"center",valign:"middle"}); });
cmp.forEach((r,i)=>{ const y=2.4+i*0.62; r.forEach((c,j)=>{ const us=j===4;
  panel(s,cx[j],y,cw[j],0.58,us?"15302B":BG);
  const col = c==="✓"?MINT : c==="✗"?RED : c==="◐"?GOLD : FG;
  s.addText(c,{x:cx[j]+0.05,y:y+0.02,w:cw[j]-0.1,h:0.54,fontFace:j===0?B:H,fontSize:j===0?13:15,bold:us,color:j===0?FG:col,align:j===0?"left":"center",valign:"middle"}); }); });
s.addText("The honest pitch: the free, fresh, agent-native first look — before you pull the expensive verified report.",
  {x:0.5,y:6.6,w:12.3,h:0.4,fontFace:B,fontSize:13,italic:true,color:MUT});
foot(s,7);

// 8 — Why now
s=slide(); title(s,"Why now: agents need grounded data, and the rails just shipped.");
chip(s,"TIMING",0.5,0.3);
stat(s,0.5,1.9,3.9,"97M+","MCP SDK downloads / mo",MINT);
stat(s,4.7,1.9,3.9,"150+","orgs adopting A2A",MINT);
stat(s,8.9,1.9,3.9,"~2026","every app gets an AI assistant",MINT);
panel(s,0.5,3.9,12.3,2.5);
s.addText([
 {text:"The interoperability layer (MCP + A2A) is now the default — and every agent has the same problem:\n\n",options:{color:FG,bold:true}},
 {text:"it hallucinates private-company numbers.\n\n",options:{color:GOLD,bold:true}},
 {text:"OpenPitch is the free, grounded fact-base agents call so they stop making numbers up —\nthe one place the $30k incumbents structurally can't follow.",options:{color:FG}}],
 {x:0.8,y:4.15,w:11.7,h:2.0,fontFace:B,fontSize:17,lineSpacingMultiple:1.15,valign:"top"});
foot(s,8);

// 9 — Zero cost
s=slide(); title(s,"Zero cost — proven, not aspirational.");
chip(s,"UNIT ECONOMICS",0.5,0.3);
stat(s,0.5,1.9,3.9,"50","extraction calls/day (demand)",FG);
stat(s,4.7,1.9,3.9,"420","free calls/day (capacity)",MINT);
stat(s,8.9,1.9,3.9,"$0","marginal cost",MINT);
panel(s,0.5,3.9,12.3,2.5);
s.addText([
 {text:"How: ",options:{color:MINT,bold:true}},
 {text:"free GitHub Actions (compute) · git (storage) · free-tier LLM with batching + multi-model rotation ·\nGroq free Whisper · and the user brings their own agent for queries.\n\n",options:{color:FG}},
 {text:"Even if we ever paid: ",options:{color:MINT,bold:true}},
 {text:"~$2.70 / month at full 50-company daily scale. The free tier covers it 8× over.",options:{color:FG}}],
 {x:0.8,y:4.2,w:11.7,h:2.0,fontFace:B,fontSize:17,lineSpacingMultiple:1.2,valign:"top"});
foot(s,9);

// 10 — Status
s=slide(); title(s,"Status: built, tested, and live-validated.");
chip(s,"TRACTION",0.5,0.3);
const st=[["✓ 42 tests passing","Core engine, adapters, extraction, derivation, MCP — all green"],
 ["✓ Live-validated","Extracted OpenAI $852B / $24B ARR from real sources, matching verified data"],
 ["✓ MCP connected","Registered in Claude Code (✓) and Codex — answers in-agent"],
 ["✓ Verified seed + 2 contradictions","6 AI companies, real sources, Mistral & Cursor discrepancies"],
 ["✓ Zero-cost pipeline","Daily GitHub Actions, batching + rotation, $0"],
 ["◐ Remaining","Whisper key, launch-grade contradictions, PyPI publish, demo GIF"]];
st.forEach((c,i)=>{ const x=0.5+(i%2)*6.2, y=1.8+Math.floor(i/2)*1.5; panel(s,x,y,5.95,1.35);
  s.addText(c[0],{x:x+0.2,y:y+0.15,w:5.6,h:0.45,fontFace:H,fontSize:15,bold:true,color:i===5?GOLD:MINT});
  s.addText(c[1],{x:x+0.2,y:y+0.62,w:5.6,h:0.65,fontFace:B,fontSize:12.5,color:FG}); });
foot(s,10);

// 11 — GTM
s=slide(); title(s,"Go-to-market: a sharp beachhead, an honest plan.");
chip(s,"GTM",0.5,0.3);
panel(s,0.5,1.75,6.0,4.6);
s.addText("Beachhead",{x:0.75,y:2.0,w:5.5,h:0.5,fontFace:H,fontSize:18,bold:true,color:MINT});
s.addText([{text:"AI builders who need grounded company data in their own agents/products.\n\n",options:{color:FG}},
 {text:"Customer in our channel · recurring, embedded use · the spot incumbents can't reach.\n\n",options:{color:MUT}},
 {text:"Secondary: founders, VCs/scouts priced out of PitchBook, tech press.",options:{color:FG}}],
 {x:0.75,y:2.6,w:5.5,h:3.5,fontFace:B,fontSize:15,lineSpacingMultiple:1.15});
panel(s,6.8,1.75,6.0,4.6);
s.addText("30-day launch",{x:7.05,y:2.0,w:5.5,h:0.5,fontFace:H,fontSize:18,bold:true,color:MINT});
s.addText([{text:"Hook: the contradiction-finder (drama) + free PitchBook-for-AI (utility).\n\n",options:{color:FG}},
 {text:"Show HN → X thread → Product Hunt → Reddit, sustained by a renewable drip of new contradictions.\n\n",options:{color:FG}},
 {text:"Honest odds of 5,000 stars in 30 days: ~25% (base 2.5–4k). Stars ≠ PMF — we build for the retained user.",options:{color:MUT}}],
 {x:7.05,y:2.6,w:5.5,h:3.6,fontFace:B,fontSize:15,lineSpacingMultiple:1.15});
foot(s,11);

// 12 — Close
s=slide();
s.addText("›_",{x:0.5,y:1.4,w:1.5,h:0.8,fontFace:H,fontSize:36,bold:true,color:TEAL});
s.addText("The open intelligence layer\nany agent can build on.",{x:0.5,y:2.0,w:12.3,h:1.8,fontFace:H,fontSize:40,bold:true,color:MINT,lineSpacingMultiple:1.05});
panel(s,0.5,4.1,12.3,1.1,PANEL);
s.addText([{text:"Claude Code:  ",options:{color:MUT}},{text:"claude mcp add openpitch -- uvx --from openpitch openpitch-mcp",options:{color:MINT}}],
 {x:0.75,y:4.35,w:11.8,h:0.6,fontFace:H,fontSize:16});
s.addText("Free · open-source · MCP & A2A native · every number sourced.",{x:0.5,y:5.5,w:12.3,h:0.5,fontFace:B,fontSize:16,italic:true,color:FG});
s.addText("github.com/<owner>/openpitch   ·   MIT",{x:0.5,y:6.2,w:12.3,h:0.4,fontFace:H,fontSize:12,color:MUT});
foot(s,12);

p.writeFile({ fileName: require("path").join(__dirname, "..", "docs", "OpenPitch-Pitch-Deck.pptx") }).then(f=>console.log("wrote",f));
