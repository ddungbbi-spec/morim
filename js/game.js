
(()=>{'use strict';
// Attached 8-frame taiji animation; embedded to keep this a standalone HTML file.
const taijiSprite = new Image();
taijiSprite.src = '/assets/taiji-sprite.png?v=original-20261105';
let martialSpriteTime = 0, martialSpriteArt = 'taegeuk', martialSpriteSkill = true;
const TAIJI_FRAME_DURATIONS = [0.14,0.10,0.10,0.08,0.12,0.12,0.10,0.18];
const TAIJI_DURATION = TAIJI_FRAME_DURATIONS.reduce((a,b)=>a+b,0);
function martialStyle(art,skill){
  return art==='cloud'?{tint:'#7ef0d2', glow:'#3cd1b3', width:158, height:170, offX:0, offY:0, lean:-0.03, trail:true, halo:false, shock:false, lightning:false}:
         art==='palm'?{tint:'#ffb36f', glow:'#ff8a45', width:164, height:166, offX:10, offY:0, lean:0.08, trail:false, halo:false, shock:true, lightning:false}:
         art==='thunder'?{tint:'#b798ff', glow:'#7d5cff', width:168, height:172, offX:0, offY:-2, lean:-0.05, trail:false, halo:true, shock:false, lightning:true}:
         art==='basic'?{tint:'#f1e6c2', glow:'#efd08b', width:154, height:168, offX:0, offY:0, lean:0, trail:false, halo:false, shock:false, lightning:false}:
         {tint:'#9feaff', glow:'#54cfe8', width:160, height:170, offX:0, offY:0, lean:0, trail:false, halo:true, shock:false, lightning:false};
}
// Procedural, frame-based attack poses: each school uses a distinct body/weapon silhouette.
// Every martial art reuses the same character illustration as the original taiji animation.
// Art-specific pose transforms preserve costume, face, hair and weapon proportions.
const MARTIAL_SHEET_W=210, MARTIAL_SHEET_H=194;
const martialSheets = new Map();
function martialPoseSettings(art,frame){
 const p=frame/7;
 switch(art){
 case 'cloud': return {rot:-.12+.22*p,dx:8+30*p,dy:-8*Math.sin(p*Math.PI),sx:1.06,sy:.96,accent:'#7df5d8'};
 case 'palm': return {rot:.10-.19*p,dx:12+25*p,dy:-3,sx:1.04,sy:.92,accent:'#ffb47c'};
 case 'thunder': return {rot:-.18+.35*p,dx:0+17*p,dy:-14+13*p,sx:1.1,sy:1.02,accent:'#b99cff'};
 default: return {rot:-.09+.17*p,dx:6+19*p,dy:0,sx:1,sy:1,accent:'#efe1be'};
 }
}
function getMartialSpriteSheet(art){
 if(!taijiSprite.complete || !taijiSprite.naturalWidth)return null;
 if(martialSheets.has(art))return martialSheets.get(art);
 const sheet=document.createElement('canvas');sheet.width=MARTIAL_SHEET_W*8;sheet.height=MARTIAL_SHEET_H;
 const g=sheet.getContext('2d');g.imageSmoothingEnabled=true;
 for(let f=0;f<8;f++){
   const s=martialPoseSettings(art,f); const px=f*MARTIAL_SHEET_W+MARTIAL_SHEET_W*.43,py=MARTIAL_SHEET_H-4;
   g.save();g.translate(px+s.dx,py+s.dy);g.rotate(s.rot);g.scale(s.sx,s.sy);
   // The eight original taiji frames supply consistent costume and character detail.
   g.drawImage(taijiSprite,f*160,0,160,172,-80,-172,160,172);g.restore();
   g.save();g.translate(f*MARTIAL_SHEET_W,0);
   g.strokeStyle=s.accent;g.shadowColor=s.accent;g.shadowBlur=10;g.lineCap='round';
   const q=f/7;
   if(art==='cloud'){
     g.globalAlpha=.45;g.lineWidth=4;g.beginPath();g.moveTo(81,91);g.bezierCurveTo(125,52,161,48+18*q,192,87+22*q);g.stroke();
   }else if(art==='palm'){
     g.globalAlpha=.55;g.lineWidth=5;g.beginPath();g.ellipse(153,88,14+27*q,12+11*q,0,0,Math.PI*2);g.stroke();
   }else if(art==='thunder'){
     g.globalAlpha=.7;g.lineWidth=4;g.beginPath();g.moveTo(115,38);g.lineTo(138,64);g.lineTo(125,76);g.lineTo(174,112);g.stroke();
   }else{
     g.globalAlpha=.35;g.lineWidth=4;g.beginPath();g.arc(122,105,39,-1.5,-.12);g.stroke();
   }
   g.restore();
 }
 martialSheets.set(art,sheet);return sheet;
}
// Visual phases: anticipation → strike → follow-through → recovery.
// Blends a small portion of the next pose to reduce frame popping without changing hitboxes.
function attackMotion(t,art){
 const anticipation=art==='thunder'?.23:art==='palm'?.17:.19;
 const impact=art==='cloud'?.53:art==='palm'?.46:.48;
 if(t<anticipation)return .16*(t/anticipation);
 if(t<impact){const u=(t-anticipation)/(impact-anticipation);return .16+.64*(u*u*(3-2*u));}
 const u=(t-impact)/(1-impact);return .80+.20*(1-(1-u)*(1-u));
}
function drawCachedMartialSprite(x,y,face,art,frame,phase=0){
 const sheet=getMartialSpriteSheet(art);if(!sheet)return false;
 const motion=Math.max(0,Math.min(1,phase));
 const active=motion>.19&&motion<.76;
 const dx=active?(art==='cloud'?12:art==='palm'?7:art==='thunder'?3:5):0;
 const lift=active?(art==='thunder'?-9:art==='cloud'?-4:0):0;
 const smear=active?Math.sin((motion-.19)/.57*Math.PI):0;
 ctx.save();ctx.translate(Math.round(x+face*dx),Math.round(y+lift));ctx.scale(face,1);
 ctx.imageSmoothingEnabled=true;
 if(smear>.15){ctx.save();ctx.globalAlpha=.13*smear;ctx.drawImage(sheet,Math.max(0,frame-1)*MARTIAL_SHEET_W,0,MARTIAL_SHEET_W,MARTIAL_SHEET_H,-MARTIAL_SHEET_W*.43-19,-MARTIAL_SHEET_H+4,MARTIAL_SHEET_W,MARTIAL_SHEET_H);ctx.restore()}
 ctx.drawImage(sheet,frame*MARTIAL_SHEET_W,0,MARTIAL_SHEET_W,MARTIAL_SHEET_H,-MARTIAL_SHEET_W*.43,-MARTIAL_SHEET_H+4,MARTIAL_SHEET_W,MARTIAL_SHEET_H);
 // A restrained trail follows the weapon, instead of tinting the whole character.
 if(smear>.08){ctx.save();ctx.globalAlpha=.7*smear;ctx.strokeStyle=art==='cloud'?'#88f5dd':art==='palm'?'#ffb57d':art==='thunder'?'#b5a1ff':'#f4e2b6';ctx.lineWidth=art==='palm'?8:5;ctx.shadowColor=ctx.strokeStyle;ctx.shadowBlur=14;ctx.beginPath();if(art==='palm'){ctx.moveTo(36,-68);ctx.lineTo(90,-72)}else if(art==='thunder'){ctx.moveTo(22,-128);ctx.quadraticCurveTo(102,-105,84,-42)}else{ctx.moveTo(12,-116);ctx.quadraticCurveTo(84,-122,108,-64)}ctx.stroke();ctx.restore()}
 ctx.restore();return true;
}
function drawMartialSprite(x,y,face,art,skill){
  if(art==='taegeuk' && (!taijiSprite.complete || !taijiSprite.naturalWidth)) return false;
  let elapsed = TAIJI_DURATION - martialSpriteTime;
  let frame = 0;
  for (let i=0;i<TAIJI_FRAME_DURATIONS.length-1;i++) {
    if(elapsed < TAIJI_FRAME_DURATIONS[i]) break;
    elapsed -= TAIJI_FRAME_DURATIONS[i]; frame++;
  }
  if(art!=='taegeuk'){const motion=attackMotion(Math.max(0,Math.min(1,1-martialSpriteTime/TAIJI_DURATION)),art);return drawCachedMartialSprite(x,y,face,art,Math.min(7,Math.floor(motion*8)),motion)}
  const st = martialStyle(art,skill);
  const sx = frame*160, sy = 0, sw = 160, sh = 172;
  const progress = 1 - Math.max(0, martialSpriteTime)/TAIJI_DURATION;
  ctx.save();
  ctx.translate(x,y+st.offY);
  ctx.scale(face,1);
  ctx.rotate(st.lean*face);
  ctx.imageSmoothingEnabled=false;
  if(st.trail){
    for(let i=2;i>=1;i--){
      ctx.save();
      ctx.globalAlpha=0.14*i;
      ctx.translate(-18*i, 3*i);
      ctx.drawImage(taijiSprite,sx,sy,sw,sh,-st.width/2,-st.height+st.offY,st.width,st.height);
      ctx.restore();
    }
  }
  ctx.save();
  ctx.shadowBlur=20; ctx.shadowColor=st.glow; ctx.globalAlpha=1;
  ctx.drawImage(taijiSprite,sx,sy,sw,sh,-st.width/2+st.offX,-st.height,st.width,st.height);
  ctx.restore();
  if(st.halo){
    ctx.save();
    ctx.globalAlpha=.55;
    ctx.strokeStyle=st.glow;
    ctx.lineWidth=3;
    ctx.beginPath();
    ctx.arc(8,-90,22+progress*10,0,Math.PI*2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(32,-56,10+progress*8,0,Math.PI*2);
    ctx.stroke();
    ctx.restore();
  }
  if(st.shock){
    ctx.save();
    ctx.globalAlpha=.7;
    ctx.strokeStyle=st.glow;
    ctx.lineWidth=5;
    ctx.beginPath();
    ctx.ellipse(54,-62,28+progress*26,14+progress*7,0,0,Math.PI*2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(12,-64); ctx.lineTo(105,-64);
    ctx.stroke();
    ctx.restore();
  }
  if(st.lightning){
    ctx.save();
    ctx.globalAlpha=.8;
    ctx.strokeStyle=st.glow;
    ctx.lineWidth=4;
    ctx.beginPath();
    ctx.moveTo(6,-118); ctx.lineTo(24,-84); ctx.lineTo(10,-84); ctx.lineTo(48,-42); ctx.lineTo(26,-42); ctx.lineTo(76,-4);
    ctx.stroke();
    ctx.restore();
  }
  ctx.restore();
  return true;
}
const canvas=document.getElementById('game'),ctx=canvas.getContext('2d');let W=innerWidth,H=innerHeight,dpr=1,scale=1,viewW=1200,viewH=700;function resize(){W=innerWidth;H=innerHeight;dpr=Math.min(devicePixelRatio||1,2);canvas.width=W*dpr;canvas.height=H*dpr;scale=Math.min(W/1200,H/700);viewW=W/scale;viewH=H/scale;ctx.setTransform(dpr*scale,0,0,dpr*scale,0,0)}window.addEventListener('resize',resize);resize();const GROUND=550,WORLD=3600,keys=new Set(),pressed=new Set();let state='menu',camera=0,time=0,last=0,shake=0,particles=[],slashes=[],artEffects=[],impactEffects=[],bossEffects=[],allyEffects=[],enemies=[],spawnClock=0,noticeTime=0,trialBoss=false,bossDefeated=false;let dashTimer=0,dashCooldown=0,afterimages=[],floatingTexts=[],bossRings=[],lastAttackArt='basic',lastAttackSkill=false;const MARTIAL_ARTS={basic:{name:"무당기초검",description:"균형 잡힌 무당파 기초 검술",power:1,range:1,mp:0},cloud:{name:"유운검법",description:"구름처럼 길게 뻗는 검기 · 타격거리 증가",power:1.14,range:1.35,mp:0},palm:{name:"무당장권",description:"근거리 충격파 · 강한 한 방",power:1.46,range:.82,mp:0},taegeuk:{name:"태극검법",description:"내공을 실은 태극검기",power:1,range:1,mp:25},thunder:{name:"진무뇌검",description:"응축한 뇌광으로 적을 관통",power:1.55,range:1.2,mp:38}};let learnedArts=["basic","taegeuk"],equippedArts={J:"basic",K:"taegeuk"};let customCombo={sequence:"JKJ",name:"유운삼환",power:1.65,range:1.25},comboEnabled=true;let cultivationPoints=0, cultivationTree={sword:0,palm:0,qi:0,movement:0},innerArt="balanced",breakthroughs=0;let mastery=0,comboBuffer=[],comboWindow=0,comboFlash=0,comboLabel="",contribution=0,manuals=0,secretLevel=0,zone='수련장',gold=30,herbs=0,ore=0,potions=2,weapon=0,armor=0,skillLevel=1,questStage=0,questKills=0,questClaimed=0;const JOBS={disciple:{name:'무당 제자',desc:'모든 무공의 기본형'},swordsman:{name:'태극검수',desc:'검격·검기 피해 +18%, 검기 내공 -12%'},fist:{name:'무당권사',desc:'장법 피해 +32%, 받는 피해 -10%'},taoist:{name:'순양도사',desc:'검기 피해 +10%, 내공 소모 -25%, 운기 회복 +25%'}};let selectedJob='disciple',advancedJob='',ultimateCooldown=0;const ADVANCED_JOBS={swordsman:{id:'swordlord',name:'진무검종',ultimate:'태극만검진',desc:'다수의 검기를 전방에 펼치는 광역 필살기',art:'taegeuk',color:'#77e8ff'},fist:{id:'fistlord',name:'태극권종',ultimate:'무극붕천장',desc:'강력한 근접 장력으로 적을 제압하는 필살기',art:'palm',color:'#ffc080'},taoist:{id:'sage',name:'진무도인',ultimate:'구천뇌광결',desc:'넓은 범위에 뇌광을 내려치는 필살기',art:'thunder',color:'#c7a8ff'}};const player={x:180,y:GROUND,vx:0,vy:0,face:1,hp:100,maxhp:100,mp:100,maxmp:100,level:1,xp:0,need:50,kills:0,rank:0,attackCD:0,skillCD:0,inv:0,attackAnim:0,meditate:0,trial:false,dashInv:0,walkCycle:0};let sectFunds=180,sectFame=0,sectSupplies=6,sectMissions=0;const facilities={training:1,library:1,alchemy:1};let disciples=[];let factionRelations={"소림파":0,"화산파":0,"아미파":0},leagueWins=0,warWins=0,arenaFaction=null;const DISCIPLE_NAMES=['청허','유진','소연','명윤','백송','서란','도현','운정','무진','하령','서풍','정월'];const RANKS=['삼대제자','이대제자','일대제자','진전제자','장로','장문인'];const TRIALS=[null,null,{name:'흑풍산 살수',hp:580,level:9,kills:12,contribution:35},{name:'마교 흑의호법',hp:860,level:13,kills:16,contribution:100},{name:'무당 장문인 선발전',hp:1250,level:17,kills:20,contribution:180}];let trialTier=0;let storyStage=0,storyChoice='',storyBossActive=false;let companions=[],activeCompanion="",bondArts=[],companionAttackClock=0;let npcTrust={청죽림:0,낙양성:0,혈마곡:0},sideQuest={청죽림:0,낙양성:0,혈마곡:0},sideKills={청죽림:0,낙양성:0,혈마곡:0};const STORY_ZONES=['수련장','청운진','흑풍산','청죽림','낙양성','혈마곡'];const STORY_BOSSES={청죽림:{name:'청죽림 검객',hp:390},낙양성:{name:'흑련회 당주',hp:660},혈마곡:{name:'혈마곡 마군',hp:1050}};const $=id=>document.getElementById(id);function safeSet(k,v){try{localStorage.setItem(k,v);return true}catch(e){console.warn('저장 실패',e);return false}}function safeGet(k){try{return localStorage.getItem(k)}catch(e){return null}}function toast(t){$('toast').textContent=t;$('toast').classList.add('show');noticeTime=2.8}const SAVE_KEY='wudang-v1', BACKUP_KEY='wudang-v1-backup';
let pendingBattleRestore=null, saveRevision=3;
function savedBattle(){return {player:{x:player.x,y:player.y,hp:player.hp,mp:player.mp,face:player.face},trial:!!player.trial,trialBoss:!!trialBoss,storyBossActive:!!storyBossActive,arenaFaction:arenaFaction||null,spawnClock:spawnClock,enemies:enemies.filter(e=>!e.dead).slice(0,25).map(e=>({kind:e.kind,x:e.x,y:e.y,hp:e.hp,maxhp:e.maxhp,boss:!!e.boss,storyBoss:!!e.storyBoss,storyStageAfter:e.storyStageAfter,storyReward:e.storyReward,attackCD:e.attackCD,patternClock:e.patternClock,patternRadius:e.patternRadius,patternIndex:e.patternIndex||0,phaseAnnounced:!!e.phaseAnnounced,counterStance:!!e.counterStance,patternKind:e.patternKind||"center",patternX:e.patternX,aggro:e.aggro,w:e.w}))}}
function snapshot(){return {saveFormat:saveRevision,level:player.level,xp:player.xp,need:player.need,maxhp:player.maxhp,maxmp:player.maxmp,kills:player.kills,rank:player.rank,selectedJob,advancedJob,bossDefeated,trialTier,zone,gold,herbs,ore,potions,weapon,armor,skillLevel,questStage,questKills,questClaimed,contribution,manuals,secretLevel,sectFunds,sectFame,sectSupplies,sectMissions,facilities,disciples,factionRelations,leagueWins,warWins,mastery,learnedArts,equippedArts,customCombo,comboEnabled,cultivationPoints,cultivationTree,innerArt,breakthroughs,storyStage,storyChoice,npcTrust,sideQuest,sideKills,companions,activeCompanion,bondArts,battle:savedBattle(),savedAt:new Date().toISOString()}}
function validateSave(d){return !!(d&&typeof d==='object'&&!Array.isArray(d)&&Number.isInteger(d.level)&&d.level>=1&&d.level<=100000&&Number.isInteger(d.rank)&&d.rank>=0&&d.rank<=5&&Number.isFinite(d.maxhp)&&d.maxhp>0&&d.maxhp<1e8&&Number.isFinite(d.maxmp)&&d.maxmp>0&&d.maxmp<1e8&&STORY_ZONES.includes(d.zone||'수련장')&&(d.saveFormat===undefined||Number.isInteger(d.saveFormat)&&d.saveFormat>=1&&d.saveFormat<=saveRevision))}
function storeSave(silent=false){try{const data=JSON.stringify(snapshot());const previous=safeGet(SAVE_KEY);const ok=safeSet(SAVE_KEY,data);if(ok&&previous){try{if(validateSave(JSON.parse(previous)))safeSet(BACKUP_KEY,previous)}catch(e){console.warn('이전 저장 기록 백업 건너뜀',e)}}if(!silent)toast(ok?'수련 기록이 저장되었습니다':'저장 실패 · 브라우저 저장 공간/권한을 확인하세요');return ok}catch(e){if(!silent)toast('저장에 실패했습니다');return false}}
function save(){return storeSave(false)}
function load(){try{let d=null;for(const key of [SAVE_KEY,BACKUP_KEY]){try{const candidate=JSON.parse(safeGet(key));if(validateSave(candidate)){d=candidate;break}}catch(e){}}if(!d)return false;for(const k of ['level','xp','need','maxhp','maxmp','kills','rank'])if(typeof d[k]==='number')player[k]=d[k];selectedJob=Object.hasOwn(JOBS,d.selectedJob)?d.selectedJob:'disciple';advancedJob=ADVANCED_JOBS[selectedJob]?.id===d.advancedJob?d.advancedJob:'';ultimateCooldown=0;mastery=Number.isFinite(d.mastery)?Math.max(0,Math.floor(d.mastery)):0;learnedArts=Array.isArray(d.learnedArts)?["basic","taegeuk",...d.learnedArts.filter(x=>Object.hasOwn(MARTIAL_ARTS,x))].filter((x,i,a)=>a.indexOf(x)===i):["basic","taegeuk"];equippedArts={J:learnedArts.includes(d.equippedArts?.J)?d.equippedArts.J:"basic",K:learnedArts.includes(d.equippedArts?.K)?d.equippedArts.K:"taegeuk"};customCombo=validateCombo(d.customCombo);comboEnabled=d.comboEnabled!==false;cultivationPoints=Number.isFinite(d.cultivationPoints)?Math.max(0,Math.floor(d.cultivationPoints)):0;breakthroughs=Number.isFinite(d.breakthroughs)?Math.max(0,Math.floor(d.breakthroughs)):0;innerArt=['balanced','pure','fluid'].includes(d.innerArt)?d.innerArt:'balanced';for(const k of Object.keys(cultivationTree))cultivationTree[k]=Number.isInteger(d.cultivationTree?.[k])?Math.max(0,Math.min(5,d.cultivationTree[k])):0;comboBuffer=[];comboWindow=0;bossDefeated=!!d.bossDefeated;trialTier=Number.isInteger(d.trialTier)&&d.trialTier>=0&&d.trialTier<=4?d.trialTier:0;for(const k of ['gold','herbs','ore','potions','weapon','armor','skillLevel','questStage','questKills','questClaimed','contribution','manuals','secretLevel'])if(typeof d[k]==='number')evalAssign(k,d[k]);sectFunds=Number.isFinite(d.sectFunds)?Math.max(0,d.sectFunds):180;sectFame=Number.isFinite(d.sectFame)?Math.max(0,d.sectFame):0;sectSupplies=Number.isFinite(d.sectSupplies)?Math.max(0,d.sectSupplies):6;sectMissions=Number.isFinite(d.sectMissions)?Math.max(0,d.sectMissions):0;for(const f of Object.keys(facilities))facilities[f]=Number.isInteger(d.facilities?.[f])?Math.max(1,Math.min(8,d.facilities[f])):1;disciples=Array.isArray(d.disciples)?d.disciples.filter(x=>x&&typeof x.name==='string'&&Number.isFinite(x.level)).slice(0,20).map(x=>({name:x.name.slice(0,10),level:Math.max(1,Math.min(30,x.level)),talent:Math.max(1,Math.min(5,Number(x.talent)||1)),xp:Math.max(0,Number(x.xp)||0)})):[];for(const f of Object.keys(factionRelations))factionRelations[f]=Number.isFinite(d.factionRelations?.[f])?Math.max(-100,Math.min(100,Math.round(d.factionRelations[f]))):0;leagueWins=Number.isInteger(d.leagueWins)?Math.max(0,d.leagueWins):0;warWins=Number.isInteger(d.warWins)?Math.max(0,d.warWins):0;arenaFaction=null;zone=STORY_ZONES.includes(d.zone)?d.zone:'수련장';companions=Array.isArray(d.companions)?d.companions.filter(x=>["청죽림","낙양성","혈마곡"].includes(x)).slice(0,3):[];activeCompanion=companions.includes(d.activeCompanion)?d.activeCompanion:"";bondArts=Array.isArray(d.bondArts)?d.bondArts.filter(x=>["청죽림","낙양성","혈마곡"].includes(x)):[];storyStage=Number.isInteger(d.storyStage)?Math.max(0,Math.min(6,d.storyStage)):0;storyChoice=['','구휼','추적'].includes(d.storyChoice)?d.storyChoice:'';for(const z of ['청죽림','낙양성','혈마곡']){npcTrust[z]=Math.max(0,Math.min(100,Number(d.npcTrust?.[z])||0));sideQuest[z]=Math.max(0,Math.min(2,Number(d.sideQuest?.[z])||0));sideKills[z]=Math.max(0,Number(d.sideKills?.[z])||0)}storyBossActive=false;player.hp=player.maxhp;player.mp=player.maxmp;pendingBattleRestore=d.saveFormat>=3?d.battle:null;return true}catch{return false}}function evalAssign(k,v){switch(k){case 'contribution':contribution=v;break;case 'manuals':manuals=v;break;case 'secretLevel':secretLevel=v;break;case 'gold':gold=v;break;case 'herbs':herbs=v;break;case 'ore':ore=v;break;case 'potions':potions=v;break;case 'weapon':weapon=v;break;case 'armor':armor=v;break;case 'skillLevel':skillLevel=v;break;case 'questStage':questStage=v;break;case 'questKills':questKills=v;break;case 'questClaimed':questClaimed=v;break;}}function restoreBattle(b){if(!b||typeof b!=='object'||!b.player||!Array.isArray(b.enemies))return false;
 const p=b.player;if(![p.x,p.y,p.hp,p.mp].every(Number.isFinite))return false;
 player.x=Math.max(45,Math.min(WORLD-45,p.x));player.y=Math.max(0,Math.min(GROUND,p.y));player.hp=Math.max(1,Math.min(player.maxhp,p.hp));player.mp=Math.max(0,Math.min(player.maxmp,p.mp));player.face=p.face===-1?-1:1;
 const valid=[];for(const e of b.enemies.slice(0,25)){if(!e||typeof e.kind!=='string'||e.kind.length>50||![e.x,e.y,e.hp,e.maxhp].every(Number.isFinite)||e.hp<=0||e.maxhp<=0||e.maxhp>1e8)continue;valid.push({...e,kind:e.kind,x:Math.max(0,Math.min(WORLD,e.x)),y:GROUND,vx:0,face:-1,hp:Math.min(e.hp,e.maxhp),hit:0,windup:0,attackDone:false,dead:false,attackCD:Number.isFinite(e.attackCD)?Math.max(0,Math.min(5,e.attackCD)):1,patternClock:Number.isFinite(e.patternClock)?Math.max(.2,Math.min(8,e.patternClock)):3,patternWindup:0,patternRadius:Number.isFinite(e.patternRadius)?Math.max(0,Math.min(500,e.patternRadius)):0,patternIndex:Number.isInteger(e.patternIndex)?Math.max(0,Math.min(100000,e.patternIndex)):0,phaseAnnounced:!!e.phaseAnnounced,counterStance:false,patternKind:['tracking','counter','blood','sword','center'].includes(e.patternKind)?e.patternKind:'center',patternX:Number.isFinite(e.patternX)?Math.max(0,Math.min(WORLD,e.patternX)):e.x,aggro:e.boss?700:300,w:e.boss?55:34})}
 enemies=valid;player.trial=!!b.trial&&valid.some(e=>e.boss);trialBoss=!!b.trialBoss&&valid.some(e=>e.boss);storyBossActive=!!b.storyBossActive&&valid.some(e=>e.storyBoss);arenaFaction=valid.some(e=>e.boss)&&['소림파','화산파','아미파'].includes(b.arenaFaction)?b.arenaFaction:null;spawnClock=Number.isFinite(b.spawnClock)?Math.max(.5,Math.min(6,b.spawnClock)):2;return true}
function start(doLoad=false){if(doLoad&&!load()){toast('유효한 저장 기록이 없습니다');return}state='play';$('overlay').style.display='none';resetField();const restored=doLoad&&restoreBattle(pendingBattleRestore);pendingBattleRestore=null;updateUI();toast(doLoad?(restored?'전투 진행 상태까지 복원했습니다':'저장된 수련 기록을 불러왔습니다'):'무당파 수련장에 입문했습니다')}function resetField(){ultimateVisuals=[];ultimateCooldown=0;storyBossActive=false;martialSpriteTime=0;martialSpriteArt='taegeuk';martialSpriteSkill=true;companionAttackClock=0;comboBuffer=[];comboWindow=0;comboFlash=0;dashTimer=0;dashCooldown=0;afterimages=[];floatingTexts=[];bossRings=[];arenaFaction=null;enemies=[];particles=[];artEffects=[];impactEffects=[];bossEffects=[];allyEffects=[];player.x=180;player.y=GROUND;player.vx=player.vy=0;player.trial=false;trialBoss=false;spawnClock=2;for(let i=0;i<(['청운진','낙양성'].includes(zone)?0:4);i++)spawnEnemy(zone==='수련장'?510+i*320:790+i*380,false,zone==='수련장'?'목인':null)}const ENEMY_TYPES={
 '목인':{hp:65,xp:10},
 '산적':{hp:65,xp:40},'산적 궁수':{hp:58,xp:50},
 '회색늑대':{hp:72,xp:70},'자객':{hp:95,xp:80},
 '낭인 무사':{hp:110,xp:90},'산적 투사':{hp:135,xp:110},
 '산적 대장':{hp:170,xp:120},'호랑이':{hp:190,xp:150},
 '흑풍채 두목':{hp:300,xp:200},
 '청죽림 검객':{hp:95,xp:90},'마교 추격자':{hp:135,xp:110}
};
const ZONE_ENEMY_POOLS={
 '흑풍산':['산적','산적','산적 궁수','자객','산적 투사','산적 대장','흑풍채 두목'],
 '청죽림':['청죽림 검객','낭인 무사','회색늑대','호랑이'],
 '혈마곡':['마교 추격자','자객','낭인 무사','호랑이']
};
function spawnEnemy(x,boss=false,forcedKind=null){
 if(['청운진','낙양성'].includes(zone)&&!boss)return;
 // Training grounds never spawn hostile humanoids or wildlife.
 if(zone==='수련장'&&boss&&!trialBoss)return;
 const pool=ZONE_ENEMY_POOLS[zone]||['산적','산적 궁수','회색늑대','낭인 무사'];
 const kind=forcedKind||(boss?(trialTier>=2?TRIALS[trialTier].name:'흑풍채 두목'):zone==='수련장'?'목인':pool[Math.floor(Math.random()*pool.length)]);
 const base=ENEMY_TYPES[kind]||{hp:80,xp:115};
 const hp=boss?(trialTier>=2?TRIALS[trialTier].hp:340):base.hp+(kind==='목인'?0:player.rank*18);
 enemies.push({kind,x,y:GROUND,vx:0,face:-1,hp,maxhp:hp,hit:0,attackCD:Math.random()*1.5,windup:0,attackDone:false,dead:false,boss,patternClock:boss?3.2:99,patternWindup:0,patternRadius:0,aggro:boss?700:300,w:boss?55:34});
}
function showPanel(title,text,button='계속',cb=()=>resume()){state='pause';$('panel').classList.remove('panelScrollable');$('overlay').style.display='flex';$('panel').innerHTML='<div class="gold">武當派 · 장문인의 길</div><h1>'+title+'</h1><p>'+text+'</p><button class="btn" id="dialogBtn">'+button+'</button>';$('dialogBtn').onclick=cb}function resume(){state='play';$('overlay').style.display='none'}function levelUp(){cultivationPoints++;player.level++;player.maxhp+=15;player.maxmp+=10;player.hp=player.maxhp;player.mp=player.maxmp;player.xp-=player.need;player.need=Math.floor(player.need*1.38);toast('경지 상승! '+player.level+'경지 돌파 · 기혈과 내공 증가');burst(player.x,player.y-45,'#f4d68e',28)}function gainXP(v){player.xp+=v;while(player.xp>=player.need)levelUp()}function interact(){if(['청죽림','낙양성','혈마곡'].includes(zone)&&player.x<460){showLocalNPC();return}if(zone==='낙양성'){showStory();return}if(zone==='청죽림'||zone==='혈마곡'){showStory();return}if(zone==='청운진'){showTown();return}if(zone==='흑풍산'){toast('흑풍산입니다. M으로 다른 지역에 이동할 수 있습니다');return}if(player.x>400){toast('교관은 수련장 입구에 있습니다 (왼쪽)');return}if(player.rank===0){if(player.kills<5){showPanel('현진 도장','"무당의 도는 강함보다 마음의 수련에 있느니라."<br>이대제자 시험 조건: 산적 5명 제압.<br>현재: '+player.kills+' / 5명')}else if(player.level<3){showPanel('현진 도장','"기초 내공이 부족하구나. 3경지에 도달한 후 다시 오너라."')}else if(!player.trial&&!bossDefeated){player.trial=true;trialBoss=true;enemies=[];spawnEnemy(950,true,'흑풍채 두목');toast('승급 시험 개시! 흑풍채 두목을 제압하라.');}else if(bossDefeated){player.rank=1;player.trial=false;bossDefeated=false;player.hp=player.maxhp;player.mp=player.maxmp;player.kills=0;showPanel('이대제자 승급','교관이 당신의 검을 인정했습니다.<br><span class="gold">이대제자에 올랐습니다!</span><br>다음 단계: 강호에서 10명의 적을 제압하고 6경지에 도달하십시오.','수련 계속',()=>{resume();save()})}}else if(player.rank===1){if(player.kills>=10&&player.level>=6){player.rank=2;player.kills=0;showPanel('일대제자 승급','무당의 장로가 직접 이름을 호명합니다.<br><span class="gold">일대제자에 올랐습니다!</span>','수련 계속',()=>{resume();save()})}else showPanel('현진 도장','다음 승급 조건: 적 10명 제압 + 6경지.<br>현재: '+player.kills+'/10명, '+player.level+'/6경지')}else if(player.rank>=2&&player.rank<=4){const t=TRIALS[player.rank];if(bossDefeated&&trialTier===player.rank){player.rank++;bossDefeated=false;trialTier=0;player.kills=0;player.hp=player.maxhp;player.mp=player.maxmp;const final=player.rank===5;showPanel(final?'무당파 장문인 등극':'문파 승급 성공',final?'태극의 도를 깨우친 당신은 제자와 장로들의 추대를 받아 무당파의 새 장문인으로 등극했습니다.<br><span class=gold>武當掌門 · 무당파 장문인</span><br>앞으로도 강호에서 무공과 문파를 성장시킬 수 있습니다.':'<span class=gold>'+RANKS[player.rank]+' 승급!</span><br>다음 승급까지 강호에서 수련하고 문파 공헌도를 쌓으십시오.','강호로 돌아가기',()=>{resume();save()});}else if(player.trial){showPanel('승급 대결 진행 중','시험 상대가 수련장 오른편에 있습니다. 검격과 태극검기로 승리하십시오.')}else if(player.level>=t.level&&player.kills>=t.kills&&contribution>=t.contribution){trialTier=player.rank;player.trial=true;trialBoss=true;enemies=[];spawnEnemy(850,true);toast(t.name+' 승급 대결 시작!');}else showPanel('현진 도장 · 승급 조건','다음 승급: '+RANKS[player.rank+1]+'<br>경지 '+player.level+'/'+t.level+'<br>적 제압 '+player.kills+'/'+t.kills+'<br>공헌도 '+contribution+'/'+t.contribution+'<br>조건을 달성한 뒤 다시 대화하십시오.')}else{showPanel('장문인 집무','무당파의 장문인입니다. 무공을 연마하고 제자들을 지키며 무림을 수호하십시오.<br>G키 또는 상단 문파 경영 버튼으로 제자와 시설을 관리하십시오.')}}function comboTier(){return mastery>=100?3:mastery>=40?2:1}
const COMBO_RECIPES={JKJ:{name:"유운삼환",power:1.65,range:1.25,required:"cloud"},KJJ:{name:"진무파공",power:1.9,range:1.15,required:"palm"},JKK:{name:"뇌광쌍극",power:2.1,range:1.5,required:"thunder"},KJK:{name:"태극회천",power:1.8,range:1.35,required:"taegeuk"}};function validateCombo(c){const recipe=COMBO_RECIPES[c?.sequence];return recipe?{sequence:c.sequence,...recipe}:{sequence:"JKJ",...COMBO_RECIPES.JKJ}}function activeCombo(){const r=COMBO_RECIPES[customCombo.sequence];return !!(comboEnabled&&r&&learnedArts.includes(r.required)&&mastery>=40)}
function showComboEditor(){let html='<p>세 번의 공격을 1.8초 안에 입력해 나만의 초식을 발동합니다. 맞춤 연계기는 숙련도 40 이상이며 해당 비급을 배워야 활성화됩니다.</p><p>현재 숙련 '+mastery+' · 선택: '+customCombo.name+' ('+customCombo.sequence+') '+(activeCombo()?'✓ 사용 가능':'🔒 잠김')+'</p><p>기본 연계기 JJJ / JJK도 그대로 사용할 수 있습니다.</p>';
for(const [sequence,r] of Object.entries(COMBO_RECIPES)){const learned=learnedArts.includes(r.required);html+='<div class="factionLine"><b>'+r.name+' · '+sequence.split('').join(' → ')+'</b><p>피해 배율 '+r.power+'배 · 사거리 '+Math.round(r.range*100)+'% · 필요 비급: '+MARTIAL_ARTS[r.required].name+' '+(learned?'✓':'(미습득)')+'</p><button class="chooseCombo" data-seq="'+sequence+'">'+(customCombo.sequence===sequence?'선택됨':'이 연계기 등록')+'</button></div>'}html+='<p>설정 상태: '+(comboEnabled?'사용':'사용 안 함')+'</p><button class="btn" id="toggleCombo">'+(comboEnabled?'맞춤 연계기 비활성화':'맞춤 연계기 활성화')+'</button>';modal('비전 초식 · 연계 편집기',html);document.querySelectorAll('.chooseCombo').forEach(b=>b.onclick=()=>{customCombo=validateCombo({sequence:b.dataset.seq});saveSilent();showComboEditor();toast(customCombo.name+' 등록 완료')});$('toggleCombo').onclick=()=>{comboEnabled=!comboEnabled;saveSilent();showComboEditor()}}
function recordCombo(code){if(comboWindow<=0)comboBuffer=[];comboBuffer.push(code);comboBuffer=comboBuffer.slice(-3);comboWindow=1.8;const seq=comboBuffer.join('');if(seq===customCombo.sequence&&activeCombo()){comboBuffer=[];comboWindow=0;comboFlash=1.5;comboLabel=customCombo.name;return 'custom'}if(seq==='JJJ'&&mastery>=15){comboBuffer=[];comboWindow=0;comboFlash=1.2;comboLabel='삼재검결';return 'samjae'}if(seq==='JJK'&&mastery>=40){comboBuffer=[];comboWindow=0;comboFlash=1.5;comboLabel='태극연환';return 'taegeuk'}return ''}
function attack(skill=false){if(state!=='play')return;if(skill){if(player.skillCD>0)return;const art=MARTIAL_ARTS[equippedArts.K]||MARTIAL_ARTS.taegeuk;const cost=Math.max(1,Math.round(art.mp*(innerArt==='pure'?.82:1)*(selectedJob==='swordsman'?.88:selectedJob==='taoist'?.75:1)));if(player.mp<cost){toast("내공 "+cost+"이 필요합니다 · L 운기조식");return}player.mp-=cost;player.skillCD=.85;player.attackAnim=.32;martialSpriteTime=TAIJI_DURATION; martialSpriteArt=equippedArts.K; martialSpriteSkill=true; lastAttackArt=equippedArts.K;lastAttackSkill=true;const combo=recordCombo('K');slashes.push({x:player.x+player.face*42,y:player.y-60,dir:player.face,life:combo==='taegeuk'?.95:.72,windup:.17,range:(combo==='custom'?520*customCombo.range:combo==='taegeuk'?560:450)*art.range,art:equippedArts.K,hit:new Set(),skill:true,combo});spawnArtEffect(player.x+player.face*52,player.y-62,player.face,equippedArts.K,true,combo);burst(player.x+player.face*60,player.y-60,combo?'#ffc981':'#91e4e6',combo?35:12);if(combo)toast('✦ '+(combo==='custom'?customCombo.name:'태극연환')+' 발동!')}else{if(player.attackCD>0)return;player.attackCD=.36;player.attackAnim=.24;martialSpriteTime=TAIJI_DURATION; martialSpriteArt=equippedArts.J; martialSpriteSkill=false; lastAttackArt=equippedArts.J;lastAttackSkill=false;const combo=recordCombo('J');slashes.push({x:player.x,y:player.y-52,dir:player.face,life:combo==='samjae'?.44:.32,windup:.11,range:(combo==='custom'?210*customCombo.range:combo==='samjae'?210:110)*(MARTIAL_ARTS[equippedArts.J]||MARTIAL_ARTS.basic).range,art:equippedArts.J,hit:new Set(),skill:false,combo});spawnArtEffect(player.x+player.face*28,player.y-54,player.face,equippedArts.J,false,combo);if(combo){burst(player.x+player.face*75,player.y-60,'#ffdd96',22);toast('✦ '+(combo==='custom'?customCombo.name:'삼재검결')+' 발동!')}}}

const ULTIMATE_TIMINGS={
  swordsman:{duration:.96,windup:.24,frames:12},
  fist:{duration:.72,windup:.17,frames:10},
  taoist:{duration:1.12,windup:.32,frames:12}
};
let ultimateVisuals=[];
function launchUltimateVisual(kind,x,y,dir){
 const spec=ULTIMATE_TIMINGS[kind];if(!spec)return;
 if(ultimateVisuals.length>=4)ultimateVisuals.shift();ultimateVisuals.push({kind,x,y,dir,t:0,duration:spec.duration,windup:spec.windup,frames:spec.frames});
}
function drawUltimateVisual(u){
 const t=Math.min(1,u.t/u.duration), f=Math.min(u.frames-1,Math.floor(t*u.frames));
 const active=u.t>=u.windup, phase=active?(u.t-u.windup)/(u.duration-u.windup):u.t/u.windup;
 const alpha=active?Math.max(.12,1-phase*.8):(.3+.3*phase);
 const range=u.kind==='swordsman'?680:u.kind==='fist'?210:570;
 const color=u.kind==='swordsman'?'#8beaff':u.kind==='fist'?'#ffbd75':'#c6a7ff';
 ctx.save();ctx.translate(u.x,u.y);ctx.scale(u.dir,1);
 ctx.strokeStyle=color;ctx.fillStyle=color;ctx.shadowColor=color;ctx.shadowBlur=12;
 ctx.globalAlpha=alpha;
 if(!active){
  ctx.lineWidth=4;ctx.beginPath();ctx.ellipse(48,-59,30+phase*25,38+phase*12,0,0,Math.PI*2);ctx.stroke();
 }else if(u.kind==='swordsman'){
  // Sword wall sweeps from caster out to the exact 680-unit hit range.
  const tip=80+phase*(range-80);ctx.lineWidth=5;
  for(let i=0;i<Math.min(6,2+Math.floor(f/2));i++){
   const x=Math.max(30,tip-i*45);ctx.beginPath();ctx.moveTo(x-36,-115+i*12);ctx.quadraticCurveTo(x+15,-65,x+25,-17+i*7);ctx.stroke();
  }
  ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(38,-62);ctx.lineTo(tip,-62);ctx.stroke();
 }else if(u.kind==='fist'){
  // Melee palm shock never extends beyond actual 210-unit reach.
  const tip=38+phase*(range-38);ctx.lineWidth=7;
  for(let j=0;j<3;j++){const x=Math.max(40,tip-j*27);ctx.beginPath();ctx.ellipse(x,-58,19+j*8,28+j*6,0,0,Math.PI*2);ctx.stroke()}
 }else{
  // Lightning travels through the same 570-unit directional attack corridor.
  const tip=80+phase*(range-80);ctx.lineWidth=5;
  for(let i=0;i<3;i++){
   const x=Math.min(range,Math.max(35,tip-i*62));ctx.beginPath();ctx.moveTo(x,-210);ctx.lineTo(x-18,-141);ctx.lineTo(x+11,-141);ctx.lineTo(x-8,-35);ctx.stroke();
  }
  ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(38,-62);ctx.lineTo(tip,-62);ctx.stroke();
 }
 ctx.restore();
}

function useUltimate(){if(state!=='play')return;const info=ADVANCED_JOBS[selectedJob];if(!info||advancedJob!==info.id){toast('2차 전직 후 X 필살기를 사용할 수 있습니다');return}if(ultimateCooldown>0){toast('필살기 재사용까지 '+ultimateCooldown.toFixed(1)+'초');return}if(player.mp<45){toast('필살기에 내공 45가 필요합니다');return}player.mp-=45;ultimateCooldown=12;player.attackAnim=.55;martialSpriteTime=TAIJI_DURATION;martialSpriteArt=info.art;martialSpriteSkill=true;lastAttackArt=info.art;lastAttackSkill=true;const isFist=selectedJob==='fist';const reach=isFist?210:selectedJob==='swordsman'?680:570;slashes.push({x:player.x,y:player.y-59,dir:player.face,life:ULTIMATE_TIMINGS[selectedJob].duration,windup:ULTIMATE_TIMINGS[selectedJob].windup,range:reach,art:info.art,hit:new Set(),skill:!isFist,combo:'ultimate',ultimate:true});launchUltimateVisual(selectedJob,player.x,player.y,player.face);burst(player.x+player.face*80,player.y-75,info.color,38);floatText(player.x,player.y-160,info.ultimate,info.color);shake=Math.max(shake,9);toast('✦ '+info.ultimate+' 발동!')}
function artPalette(art,combo,skill){
const core=combo==='custom'?'#ffd571':art==='thunder'?'#b39cff':art==='cloud'?'#7ef0d2':art==='palm'?'#ffaf6e':skill?'#8fe9ff':'#f5dea4';
const glow=combo==='custom'?'#ffefb2':art==='thunder'?'#6f59df':art==='cloud'?'#42caae':art==='palm'?'#ff8f56':skill?'#53d7ff':'#efd08b';
const accent=combo?'#fff7d2':art==='thunder'?'#efe8ff':art==='cloud'?'#d8fff2':art==='palm'?'#fff0d9':'#fff8e6';
return {core,glow,accent}}
function spawnArtEffect(x,y,dir,art,skill=false,combo=''){const max=(skill?.36:.22)+(combo?.12:0);artEffects.push({x,y,dir,art,skill,combo,life:max,max,phase:Math.random()*Math.PI*2,pal:artPalette(art,combo,skill)})}
function drawArtEffect(a){const p=1-a.life/a.max;const pal=a.pal;ctx.save();ctx.translate(a.x,a.y);ctx.scale(a.dir,1);ctx.globalAlpha=Math.max(0,a.life/a.max);ctx.lineCap='round';ctx.lineJoin='round';ctx.shadowBlur=26;ctx.shadowColor=pal.glow;
if(a.combo==='custom'){
  ctx.strokeStyle=pal.core;ctx.lineWidth=12;ctx.beginPath();ctx.moveTo(-30,-48);ctx.quadraticCurveTo(55,-105,155,-20);ctx.stroke();
  ctx.strokeStyle=pal.accent;ctx.lineWidth=7;ctx.beginPath();ctx.moveTo(-10,-5);ctx.lineTo(135,-82);ctx.moveTo(8,-74);ctx.lineTo(118,14);ctx.stroke();
  ctx.fillStyle=pal.accent;for(let i=0;i<5;i++){const ang=p*4+i*Math.PI*2/5;ctx.beginPath();ctx.arc(70+Math.cos(ang)*38,-42+Math.sin(ang)*20,4.5,0,Math.PI*2);ctx.fill()}
}else if(a.art==='basic'){
  ctx.strokeStyle=pal.core;ctx.lineWidth=9;ctx.beginPath();ctx.arc(30,-8,68,-1.2,-.1);ctx.stroke();
  ctx.strokeStyle=pal.accent;ctx.lineWidth=4;ctx.beginPath();ctx.arc(44,-2,47,-1.1,.08);ctx.stroke();
}else if(a.art==='cloud'){
  ctx.strokeStyle=pal.core;ctx.lineWidth=10;ctx.beginPath();ctx.moveTo(-18,-30);ctx.bezierCurveTo(25,-72,82,-67,132,-42);ctx.bezierCurveTo(92,-8,37,-4,-12,-18);ctx.stroke();
  ctx.strokeStyle=pal.accent;ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(10,-45);ctx.quadraticCurveTo(72,-82,122,-35);ctx.stroke();
}else if(a.art==='palm'){
  ctx.fillStyle=pal.core;ctx.beginPath();ctx.moveTo(8,-18);ctx.lineTo(92,-58);ctx.lineTo(104,10);ctx.lineTo(20,28);ctx.closePath();ctx.fill();
  ctx.strokeStyle=pal.accent;ctx.lineWidth=5;ctx.beginPath();ctx.arc(68,-12,42+p*26,-.75,.95);ctx.stroke();
}else if(a.art==='taegeuk'){
  ctx.strokeStyle=pal.core;ctx.lineWidth=9;ctx.beginPath();ctx.arc(72,-28,46+p*10,.35,Math.PI*1.7);ctx.stroke();
  ctx.strokeStyle=pal.accent;ctx.lineWidth=4;ctx.beginPath();ctx.arc(72,-28,26,-2.6,.6);ctx.stroke();
  ctx.fillStyle=pal.accent;ctx.beginPath();ctx.arc(56,-42,5,0,Math.PI*2);ctx.fill();ctx.beginPath();ctx.arc(87,-13,5,0,Math.PI*2);ctx.fill();
}else if(a.art==='thunder'){
  ctx.strokeStyle=pal.core;ctx.lineWidth=8;ctx.beginPath();ctx.moveTo(-8,-42);ctx.lineTo(38,-76);ctx.lineTo(22,-28);ctx.lineTo(82,-66);ctx.lineTo(61,-10);ctx.lineTo(136,-45);ctx.stroke();
  ctx.strokeStyle=pal.accent;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(12,-62);ctx.lineTo(34,-38);ctx.lineTo(68,-48);ctx.lineTo(104,-26);ctx.stroke();
}
if(a.skill&&a.art!=='palm'){ctx.strokeStyle=pal.glow;ctx.lineWidth=3;ctx.globalAlpha*=.7;ctx.beginPath();ctx.ellipse(76,-26,84,18,0,0,Math.PI*2);ctx.stroke()}
ctx.restore()}
function burst(x,y,color,count){for(let i=0;i<count;i++)particles.push({x,y,vx:(Math.random()-.5)*230,vy:(Math.random()-.8)*230,life:.3+Math.random()*.6,color,size:2+Math.random()*4})}function damagePlayer(v){if(player.inv>0||player.dashInv>0)return;const damage=Math.max(1,Math.round((v-armor*3)*(innerArt==='fluid'?.85:1)*(selectedJob==='fist'?.90:1)));player.hp=Math.max(0,player.hp-damage);player.inv=.8;shake=7;burst(player.x,player.y-48,'#e9a7a1',10);floatText(player.x,player.y-125,'-'+damage,'#ffb0a9');if(player.hp<=0)showPanel('전투 불능','쓰러진 당신을 무당파 동료가 수련장으로 옮겼습니다.<br>현재 수련 경험과 경지는 유지됩니다.','다시 수련',()=>{player.hp=player.maxhp;player.mp=player.maxmp;player.x=180;player.y=GROUND;player.vx=0;resume()})}function floatText(x,y,text,color){floatingTexts.push({x,y,text:String(text),color,life:.85})}
function dash(){if(state!=='play'||dashCooldown>0||player.mp<12)return;player.mp-=Math.max(5,12-cultivationTree.movement);dashTimer=.19;dashCooldown=Math.max(.5,.95-cultivationTree.movement*.07);player.dashInv=.27;player.vy=Math.min(player.vy,0);burst(player.x,player.y-35,'#92e8e7',15);toast('제운종! 경공 발동')}
function update(dt){time+=dt;noticeTime-=dt;if(noticeTime<=0)$('toast').classList.remove('show');if(state!=='play')return;companionTick(dt);comboWindow=Math.max(0,comboWindow-dt);comboFlash=Math.max(0,comboFlash-dt);if(comboWindow===0)comboBuffer=[];ultimateCooldown=Math.max(0,ultimateCooldown-dt);for(const u of ultimateVisuals)u.t+=dt;ultimateVisuals=ultimateVisuals.filter(u=>u.t<u.duration);player.attackCD=Math.max(0,player.attackCD-dt);player.skillCD=Math.max(0,player.skillCD-dt);player.inv=Math.max(0,player.inv-dt);player.attackAnim=Math.max(0,player.attackAnim-dt);martialSpriteTime=Math.max(0,martialSpriteTime-dt);shake*=Math.max(0,1-dt*10);dashTimer=Math.max(0,dashTimer-dt);dashCooldown=Math.max(0,dashCooldown-dt);player.dashInv=Math.max(0,player.dashInv-dt);let move=(keys.has('KeyD')||keys.has('ArrowRight')?1:0)-(keys.has('KeyA')||keys.has('ArrowLeft')?1:0);if(move)player.face=move;player.vx=dashTimer>0?player.face*930:move*(260+cultivationTree.movement*12);player.walkCycle+=Math.abs(player.vx)*dt/37;if(dashTimer>0){afterimages.push({x:player.x,y:player.y,face:player.face,life:.27});if(Math.random()<.55)burst(player.x,player.y-40,'#8fe9e1',2)}if((keys.has('Space')||keys.has('ArrowUp'))&&player.y>=GROUND-.1){player.vy=-520;burst(player.x,GROUND,'#dfd4ab',5)}if(keys.has('KeyL')){player.mp=Math.min(player.maxmp,player.mp+(30+cultivationTree.qi*3)*(innerArt==='pure'?1.3:1)*(selectedJob==='taoist'?1.25:1)*dt);player.hp=Math.min(player.maxhp,player.hp+(5+(innerArt==='fluid'?5:0))*(bondArts.includes('낙양성')?1.4:1)*dt);player.meditate+=dt}else player.meditate=0;player.mp=Math.min(player.maxmp,player.mp+(3.5+cultivationTree.qi*.7)*dt);player.vy+=1250*dt;player.x=Math.max(45,Math.min(WORLD-45,player.x+player.vx*dt));player.y=Math.min(GROUND,player.y+player.vy*dt);if(player.y>=GROUND)player.vy=0;spawnClock-=dt;if(spawnClock<=0&&!['청운진','낙양성'].includes(zone)&&!trialBoss&&!storyBossActive&&!enemies.some(e=>e.boss&&!e.dead)&&enemies.filter(e=>!e.dead).length<5){spawnEnemy(Math.min(WORLD-140,Math.max(750,player.x+500+Math.random()*300)));spawnClock=3.8}for(const e of enemies){if(e.dead)continue;if(e.boss){
// Second phase begins at half health; alternating centered and tracking telegraphs.
e.phase=e.hp<=e.maxhp*.5?2:1;
if(e.phase===2&&!e.phaseAnnounced){e.phaseAnnounced=true;burst(e.x,e.y-60,'#ff746e',32);toast('⚠ '+e.kind+' 2페이즈! 공격 속도와 범위가 강화됩니다')}
e.patternClock-=dt;
if(e.patternClock<=0&&e.patternWindup<=0){
 e.patternIndex=(e.patternIndex||0)+1;
 e.patternKind=e.phase===2&&e.patternIndex%2===0?'tracking':'center';
 const bossName=String(e.kind||'');
 if(/장문인|선발전/.test(bossName)&&e.patternIndex%3===0)e.patternKind='counter';
 else if(/마교|혈마|흑의호법/.test(bossName)&&e.patternIndex%3===0)e.patternKind='blood';
 else if(/검객|검수|살수|두목/.test(bossName)&&e.patternIndex%3===0)e.patternKind='sword';
 e.counterStance=e.patternKind==='counter';
 e.patternX=['tracking','blood','sword'].includes(e.patternKind)?Math.max(80,Math.min(WORLD-80,player.x)):e.x;
 e.patternWindup=(e.storyBoss?.78:1.05)*(e.phase===2?.8:1);
 e.patternRadius=(e.storyBoss?(e.kind==='청죽림 검객'?145:e.kind==='흑련회 당주'?220:265):195)*(e.phase===2?1.23:1);
 e.patternClock=(e.storyBoss?(e.kind==='혈마곡 마군'?2.8:3.5):4.2)*(e.phase===2?.7:1);
 toast(e.patternKind==='counter'?'☯ 태극 반격 자세! 공격하지 말고 거리를 벌리세요':e.patternKind==='blood'?'⚠ 혈기 폭발! 폭발 중심에서 벗어나세요':e.patternKind==='sword'?'⚠ 연속 검기! 경공으로 피하세요':e.patternKind==='tracking'?'⚠ 추적 필살기! 붉은 위치에서 벗어나세요':'⚠ '+e.kind+'의 광역 초식! 경공으로 회피하세요');
}
if(e.patternWindup>0){e.patternWindup-=dt;if(e.patternWindup<=0){const cx=Number.isFinite(e.patternX)?e.patternX:e.x;
 bossRings.push({x:cx,y:GROUND-5,life:.5,max:.5,radius:e.patternRadius});
 bossEffects.push({x:cx,y:GROUND-56,kind:e.kind,radius:e.patternRadius,life:.8,max:.8});
 if(e.patternKind==='counter'){e.counterStance=false;}
 else if(e.patternKind==='sword'){
  for(let i=0;i<3;i++)bossEffects.push({x:cx+(i-1)*58,y:GROUND-56,kind:e.kind,radius:75+i*12,life:.65,max:.65});
  if(Math.abs(player.x-cx)<Math.min(190,e.patternRadius)&&Math.abs(player.y-GROUND)<110)damagePlayer((38+player.rank*3)*(e.phase===2?1.25:1));
 }else if(e.patternKind==='blood'){
  if(Math.abs(player.x-cx)<e.patternRadius&&Math.abs(player.y-GROUND)<110)damagePlayer((48+player.rank*3)*(e.phase===2?1.35:1));
  burst(cx,GROUND-70,'#d63654',65);
 }else if(Math.abs(player.x-cx)<e.patternRadius&&Math.abs(player.y-GROUND)<110)damagePlayer(((e.storyBoss?(e.kind==='혈마곡 마군'?50:e.kind==='흑련회 당주'?39:28):32)+player.rank*3)*(e.phase===2?1.3:1));
 burst(cx,GROUND-35,e.phase===2?'#ff656c':'#f4a0a0',e.phase===2?40:33)
}}}e.hit=Math.max(0,e.hit-dt);e.attackCD-=dt;const dist=player.x-e.x,abs=Math.abs(dist);if(e.boss&&e.patternWindup>0){e.vx=0;e.windup=0;e.attackDone=true}else if(abs<e.aggro){e.face=Math.sign(dist)||1;if(abs>(e.boss?86:58)){e.vx=e.face*(e.boss?(e.phase===2?156:118):e.kind==='자객'?155:80);e.x+=e.vx*dt}else{e.vx=0;if(e.attackCD<=0){e.windup=e.boss?(e.phase===2?.32:.48):.36;e.attackDuration=e.windup;e.attackCD=e.boss?(e.phase===2?.94:1.4):e.kind==='자객'?1.05:1.8;e.attackDone=false}}}else e.vx=0;if(e.windup>0){e.windup-=dt;if(e.windup<=0&&!e.attackDone){e.attackDone=true;if((player.x-e.x)*e.face>=-12&&(player.x-e.x)*e.face<(e.boss?128:83)&&Math.abs(player.y-e.y)<90)damagePlayer(e.boss?22:10+player.rank*2)}}}for(const s of slashes){s.life-=dt;if(s.windup>0){s.windup-=dt;if(s.windup>0)continue;s.windup=0;}if(s.skill&&!s.ultimate)s.x+=s.dir*690*dt;for(const e of enemies){if(e.dead||s.hit.has(e))continue;const dx=(e.x-s.x)*s.dir;if(dx>=(s.skill?-25:0)&&dx<s.range&&(Math.abs((e.y-58)-s.y)<85)){s.hit.add(e);const isCounter=!!(e.boss&&e.counterStance&&e.patternWindup>0);const dmg=Math.round(((s.skill?56:25)+player.level*(s.skill?7:4)+weapon*8+(skillLevel-1)*(s.skill?13:4)+secretLevel*(s.skill?12:3))*(1+Math.min(0.3,mastery*.001))*(s.combo==='samjae'?1.85:s.combo==='taegeuk'?2.15:s.combo==='custom'?customCombo.power:s.combo==='ultimate'?3.3:1)*(MARTIAL_ARTS[s.art]?.power||1)*(1+(s.art==='palm'?cultivationTree.palm:cultivationTree.sword)*.08)*(1+breakthroughs*.045)*(selectedJob==='swordsman'?1.18:selectedJob==='fist'&&s.art==='palm'?1.32:selectedJob==='taoist'&&s.skill?1.10:1)*(innerArt==='pure'&&s.skill?1.12:1)*(bondArts.includes('청죽림')&&!s.skill?1.10:1)*(bondArts.includes('혈마곡')&&s.skill?1.12:1));mastery+=s.combo?3:1;
 let actualDamage=dmg;if(isCounter){actualDamage=Math.max(1,Math.floor(dmg*.22));e.hp-=actualDamage;e.counterStance=false;e.patternWindup=0;e.patternClock=2.4;damagePlayer(26+player.rank*2);burst(e.x,e.y-60,'#a9f5ec',30);toast('☯ 태극 반격! 공격이 되돌아왔습니다');}
 else e.hp-=dmg;
 e.hit=.15;e.hitDir=s.dir;impactEffects.push({x:e.x,y:e.y-62,life:.28,max:.28,color:artPalette(s.art,s.combo,s.skill).core,dir:s.dir});floatText(e.x,e.y-123,actualDamage,s.skill?'#9af3ff':'#ffe1a5');burst(e.x,e.y-50,s.combo==='custom'?'#ffd07a':s.art==='thunder'?'#b7aaff':s.art==='cloud'?'#9bf8da':s.art==='palm'?'#ffb387':s.skill?'#a4f4ff':'#e9d7a0',s.combo==='custom'?18:8);if(e.hp<=0)defeatEnemy(e,'player')}}}slashes=slashes.filter(s=>s.life>0);impactEffects=impactEffects.filter(a=>(a.life-=dt)>0);bossEffects=bossEffects.filter(a=>(a.life-=dt)>0);allyEffects=allyEffects.filter(a=>(a.life-=dt)>0);artEffects=artEffects.filter(a=>(a.life-=dt)>0);for(const a of artEffects){a.phase+=dt*10;if(a.skill)a.x+=a.dir*280*dt}afterimages=afterimages.filter(a=>(a.life-=dt)>0);floatingTexts=floatingTexts.filter(a=>(a.life-=dt)>0);for(const f of floatingTexts)f.y-=40*dt;bossRings=bossRings.filter(a=>(a.life-=dt)>0);particles=particles.filter(p=>p.life>0);for(const p of particles){p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy+=310*dt;p.life-=dt}enemies=enemies.filter(e=>!e.dead||(e.deathTimer=(e.deathTimer||0)+dt)<(e.boss?1.1:.8));camera+=(Math.max(0,Math.min(WORLD-viewW,player.x-viewW*.35))-camera)*Math.min(1,dt*5);updateUI()}
function updateUI(){$('regionLabel').textContent={'수련장':'무당파 본산 · 수련장','청운진':'청운진 · 강호 마을','흑풍산':'흑풍산 · 산적 소굴','청죽림':'청죽림 · 밀림의 검객','낙양성':'낙양성 · 무림의 중심','혈마곡':'혈마곡 · 마교의 은거지'}[zone];$('goldInfo').textContent='동행 '+(activeCompanion?BOND_INFO[activeCompanion].name:'없음')+' · 은전 '+gold+'냥 · 공헌도 '+contribution+' · 비급 조각 '+manuals+' · 약초 '+herbs+' · 철광석 '+ore;$('quest2').innerHTML=questStage===0?'청운진의 약재상에게 의뢰를 받으세요.':questStage===1?'약초 채집 의뢰 · '+herbs+'/3 (흑풍산에서 적 처치)':'산적 토벌 의뢰 · '+questKills+'/5';$('rank').textContent=RANKS[player.rank]+' · '+(advancedJob&&ADVANCED_JOBS[selectedJob]?ADVANCED_JOBS[selectedJob].name:JOBS[selectedJob].name)+' | '+player.level+'경지 · '+INNER_ARTS[innerArt].name+' · 돌파 '+breakthroughs+'회';$('hptext').textContent=Math.ceil(player.hp)+' / '+player.maxhp;$('mptext').textContent=Math.floor(player.mp)+' / '+player.maxmp;$('xptext').textContent=player.xp+' / '+player.need;$('hpbar').style.width=100*player.hp/player.maxhp+'%';$('mpbar').style.width=100*player.mp/player.maxmp+'%';$('xpbar').style.width=100*player.xp/player.need+'%';$('questtext').innerHTML=player.rank===0?(bossDefeated?'✓ 승급 시험 합격! 교관에게 보고':player.trial?'흑풍채 두목 격파하기':`산적 제압 ${Math.min(5,player.kills)} / 5<br>3경지 달성 ${Math.min(3,player.level)} / 3<br>입구의 교관에게 E로 대화`):player.rank===1?`산적 제압 ${Math.min(10,player.kills)} / 10<br>6경지 달성 ${Math.min(6,player.level)} / 6<br>교관에게 승급 보고`:player.rank===5?'✓ 무당파 장문인 · G 문파 경영<br>문파 명성 '+sectFame+' · 제자 '+disciples.length+'명' :`다음 승급 ${RANKS[player.rank+1]}<br>경지 ${player.level}/${TRIALS[player.rank].level}<br>적 제압 ${player.kills}/${TRIALS[player.rank].kills}<br>공헌도 ${contribution}/${TRIALS[player.rank].contribution}<br>${player.trial?'⚔ 승급 대결 진행 중':bossDefeated?'✓ 승리! 교관에게 보고':'교관에게 E로 대화'}`; $('stats').textContent='누적 전투 성과 · 현재 단계 처치 '+player.kills+'명';$('masteryInfo').textContent='초식 숙련 '+mastery+' · '+(mastery>=100?'원숙':mastery>=40?'숙련':mastery>=15?'초급 연계':'기초 수련')+' · 수련점 '+cultivationPoints+' · J '+MARTIAL_ARTS[equippedArts.J].name+' / K '+MARTIAL_ARTS[equippedArts.K].name;$('comboInfo').textContent=comboFlash>0?'✦ '+comboLabel+'!':(comboWindow>0?'입력 '+comboBuffer.join(' → ')+' · '+comboWindow.toFixed(1)+'초':'기본 JJJ/JJK · 맞춤 '+customCombo.sequence+' ('+(activeCombo()?'활성':'잠김')+')')}function poly(points,fill,stroke){ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fillStyle=fill;ctx.fill();if(stroke){ctx.strokeStyle=stroke;ctx.stroke()}}function drawBackground(){let sky=ctx.createLinearGradient(0,0,0,GROUND);sky.addColorStop(0,zone==='혈마곡'?'#220d19':zone==='청죽림'?'#10342d':zone==='낙양성'?'#4b3760':zone==='흑풍산'?'#160e27':zone==='청운진'?'#315675':'#0b233b');sky.addColorStop(.55,zone==='혈마곡'?'#723844':zone==='청죽림'?'#507f68':zone==='낙양성'?'#b5969c':zone==='흑풍산'?'#54405c':zone==='청운진'?'#89a9b1':'#496674');sky.addColorStop(1,zone==='혈마곡'?'#af6d65':zone==='청죽림'?'#b9bb82':zone==='낙양성'?'#e2be9e':zone==='흑풍산'?'#9c796d':zone==='청운진'?'#d3c59d':'#c4ba9d');ctx.fillStyle=sky;ctx.fillRect(0,0,viewW,viewH);ctx.fillStyle='#efe0ae';ctx.globalAlpha=.7;ctx.beginPath();ctx.arc(viewW*.77,110,48,0,Math.PI*2);ctx.fill();ctx.globalAlpha=1;for(let layer=0;layer<3;layer++){const par=[.12,.26,.43][layer];ctx.save();ctx.translate(-camera*par%820,0);for(let n=-1;n<Math.ceil(viewW/820)+2;n++){const base=n*820;poly([[base-100,GROUND],[base+180,175+layer*65],[base+340,320+layer*25],[base+540,165+layer*82],[base+790,GROUND]],['#476473','#35535f','#294852'][layer])}ctx.restore()}ctx.save();ctx.translate(-camera*.65,0);for(let x=100;x<WORLD+600;x+=380){const sx=x;ctx.fillStyle='#172f37';ctx.fillRect(sx,390,9,175);poly([[sx-63,430],[sx+75,430],[sx+4,260]],'#173c40');poly([[sx-90,468],[sx+94,468],[sx+4,318]],'#17363a')}ctx.restore();ctx.fillStyle='#273f3d';ctx.fillRect(0,GROUND,viewW,viewH-GROUND);ctx.fillStyle='#475748';ctx.fillRect(0,GROUND,viewW,11);for(let i=0;i<Math.ceil(viewW/58)+2;i++){const x=i*58-(camera%58);ctx.strokeStyle='#58614d';ctx.beginPath();ctx.moveTo(x,GROUND+15);ctx.lineTo(x+17,GROUND+70);ctx.stroke()}ctx.save();ctx.translate(-camera,0);drawTemple(50);
// Region-specific pixel-style terrain, structures, and foreground landmarks.
for(let tx=0;tx<WORLD;tx+=110){const alt=Math.sin(tx*.016)*7;ctx.fillStyle=zone==='혈마곡'?'#64424b':zone==='낙양성'?'#88745e':zone==='청죽림'?'#557750':zone==='흑풍산'?'#5b5261':'#77775a';ctx.fillRect(tx,GROUND+3+alt,54,5);ctx.fillStyle='#aaa17a';ctx.fillRect(tx+35,GROUND+10,8,4)}
if(zone==='청죽림'){for(let tx=500;tx<WORLD;tx+=220){ctx.fillStyle='#29614d';ctx.fillRect(tx,GROUND-135,11,136);ctx.fillStyle='#73ac69';for(let h=0;h<5;h++)ctx.fillRect(tx-30+h*11,GROUND-120-h*18,48,8)}}
if(zone==='낙양성'){for(let tx=560;tx<WORLD;tx+=610){ctx.fillStyle='#9e7b58';ctx.fillRect(tx,GROUND-116,200,116);poly([[tx-22,GROUND-115],[tx+100,GROUND-165],[tx+220,GROUND-115]],'#493a46','#d3a86e');ctx.fillStyle='#e0bb81';ctx.fillRect(tx+60,GROUND-70,50,70);ctx.fillStyle='#9b403e';ctx.fillRect(tx+130,GROUND-98,30,26)}}
if(zone==='혈마곡'){for(let tx=520;tx<WORLD;tx+=340){poly([[tx-50,GROUND],[tx+20,GROUND-142],[tx+95,GROUND]],'#35232e');ctx.fillStyle='#d24c59';ctx.fillRect(tx+15,GROUND-108,8,42);ctx.fillStyle='#ffb3a3';ctx.fillRect(tx+17,GROUND-105,4,16)}}
if(zone==='흑풍산'){for(let tx=500;tx<WORLD;tx+=450){ctx.fillStyle='#332f38';ctx.fillRect(tx,GROUND-132,132,132);ctx.fillStyle='#b88057';ctx.fillRect(tx+17,GROUND-96,13,65);ctx.fillRect(tx+95,GROUND-96,13,65);ctx.fillStyle='#252733';poly([[tx-18,GROUND-132],[tx+66,GROUND-180],[tx+148,GROUND-132]],'#272b39')}}
if(zone==='수련장'){for(let tx=720;tx<WORLD;tx+=700){ctx.fillStyle='#a68f69';ctx.fillRect(tx,GROUND-58,145,9);ctx.fillRect(tx+12,GROUND-49,12,47);ctx.fillRect(tx+122,GROUND-49,12,47);ctx.fillStyle='#d9bd8b';ctx.fillRect(tx+55,GROUND-80,24,24)}}
if(zone==='흑풍산'){for(let i=0;i<8;i++){let x=560+i*390;ctx.fillStyle='#392c3a';ctx.fillRect(x,410,26,140);poly([[x-100,455],[x+120,455],[x+12,290]],'#2c303c');poly([[x-75,410],[x+90,410],[x+12,323]],'#303745')}}if(zone==='낙양성'){for(let x=430;x<3200;x+=510)drawTemple(x)}if(zone==='청죽림'){for(let x=430;x<3200;x+=270){ctx.fillStyle='#243d2b';ctx.fillRect(x,335,9,220);poly([[x-55,440],[x+65,440],[x+5,260]],'#30634e')}}if(zone==='혈마곡'){for(let x=570;x<3200;x+=440){poly([[x-80,GROUND],[x+20,275],[x+110,GROUND]],'#3d2738')}}if(zone==='청운진'){drawTemple(650);drawTemple(1500);drawTemple(2400)}else drawTemple(2800);ctx.restore()}
function drawTemple(x){ctx.fillStyle='#604635';ctx.fillRect(x,370,290,180);ctx.fillStyle='#8a6650';for(let i=0;i<5;i++)ctx.fillRect(x+19+i*61,378,12,172);poly([[x-20,365],[x+145,285],[x+310,365]],'#20363b','#c0a36d');poly([[x+12,344],[x+145,282],[x+278,344]],'#456161');ctx.fillStyle='#c1a576';ctx.fillRect(x+100,400,90,150);ctx.fillStyle='#172a30';ctx.fillRect(x+108,408,74,142);ctx.fillStyle='#bba16c';ctx.fillRect(x+78,366,136,10);ctx.fillStyle='#d7c69b';ctx.font='bold 18px serif';ctx.fillText('武 當',x+112,358)}// v1.9 pixel-art character sprites: distinct idle, run, jump, attack, hurt and fall poses.
// Generated in-memory sprite sheets: 6 stances x 4 frames for heroes, enemies and bosses.
const SPRITE_MODES=['idle','run','jump','attack','skill','hurt','runAttack','airAttack','combo'];
const SPRITE_W=100,SPRITE_H=156,SPRITE_COUNT=4;
const spriteSheets=new Map();
function makeSpriteSheet(enemy,boss,art,robeRank=0){
 const sheet=document.createElement('canvas');sheet.width=SPRITE_W*SPRITE_COUNT;sheet.height=SPRITE_H*SPRITE_MODES.length;
 const c=sheet.getContext('2d');c.imageSmoothingEnabled=false;
 const pixels=['.....HHHHHH.....','....HHHHHHHH....','.....SSSSSS.....','.....SESSSS.....','.....SSSSSS.....','....CCCCCCCC....','...ACCCCCCCCA...','..AACCCCCCCCAA..','....CCCCCCCC....','.....BBBBBB.....','.....LLLLLL.....','.....LLLLLL.....','.....LL..LL.....','.....LL..LL.....','.....FF..FF.....'];
 const colors=enemy?{H:'#2d2534',S:'#d19c7c',E:'#3d1626',C:boss?'#692e48':'#7c5363',A:'#b67d6b',B:'#372a3d',L:'#292638',F:'#1b1925'}:{H:'#1c3444',S:'#edc6a1',E:'#243847',C:'#d2e6db',A:'#91c6c0',B:'#427d7e',L:'#324c5c',F:'#202d38'};
 if(!enemy){const robes=[['#d2e6db','#91c6c0','#427d7e'],['#cee2ef','#8db9d2','#335e8b'],['#eef0d8','#a5b87b','#677c4c'],['#e8d9ec','#bca2d8','#66568f'],['#e9e1c7','#c9ae73','#775e37'],['#f5e8cf','#d9b66e','#765832']];const r=robes[Math.max(0,Math.min(5,robeRank))];colors.C=r[0];colors.A=r[1];colors.B=r[2]}
 const blade=!enemy?(art==='thunder'?'#d1b8ff':art==='cloud'?'#8bf4d8':art==='palm'?'#ffcc91':art==='taegeuk'?'#9feaff':'#e2eef0'):'#e2d9d1';
 for(let m=0;m<SPRITE_MODES.length;m++)for(let f=0;f<SPRITE_COUNT;f++){
 const mode=SPRITE_MODES[m],cx=f*SPRITE_W+SPRITE_W/2,cy=m*SPRITE_H+SPRITE_H-8;
 c.save();c.translate(cx,cy);if(mode==='idle')c.translate(0,f%2?-2:0);if(mode==='hurt')c.translate(f%2?-4:3,0);
 if(mode==='jump')c.translate(0,-6);if(['attack','skill','runAttack','airAttack','combo'].includes(mode))c.translate(f*2,mode==='airAttack'?-13:-2);
 for(let r=0;r<pixels.length;r++)for(let col=0;col<pixels[r].length;col++){
 const ch=pixels[r][col];if(ch==='.')continue;let dx=0,dy=0;
 if(r>=10&&(mode==='run'||mode==='runAttack')){dx=(col<8?-1:1)*(f%2?6:-6);dy=(f%2&&col<8)?-5:0}
 if(r>=10&&(mode==='jump'||mode==='airAttack')){dx=col<8?-7:7;dy=-7}
 if(r>=6&&r<=8&&(['attack','skill','runAttack','airAttack','combo'].includes(mode))&&col>=10){dx=9+f*2;dy=-7-f*2}
 if(r>=6&&r<=8&&mode==='hurt')dx=-5;
 c.fillStyle=colors[ch];c.fillRect(-32+col*4+dx,-124+r*4+dy,4,4);
 }
 c.fillStyle=enemy?'#ba6572':'#65b9b4';c.fillRect(-13,-111,27,4);if(!enemy&&robeRank>=3){c.fillStyle=robeRank===5?'#f1d18b':'#d3bd9e';c.fillRect(-22,-91,9,7);c.fillRect(15,-91,9,7);if(robeRank===5){c.fillRect(-15,-118,30,5);c.fillRect(-5,-126,10,8)}}
 if(!enemy){c.fillStyle='#dfefee';c.fillRect(-10,-83,6,28);c.fillStyle='#5ba4a6';c.fillRect(11,-75,9,5)}
 c.save();c.translate(26,-72);
 let angle=-.26;
 if(mode==='jump')angle=-1.1;
 if(mode==='attack'||mode==='runAttack')angle=[-1.8,-1.15,-.5,.15][f];if(mode==='airAttack')angle=[-2.25,-1.55,-.6,.3][f];if(mode==='combo')angle=[-2.7,-1.3,.25,1.1][f];
 if(mode==='skill')angle=art==='thunder'?[-2.2,-1.3,-.3,.5][f]:art==='cloud'?[-1.35,-.9,-.2,.35][f]:art==='palm'?[-1.8,-1.5,-.9,-.45][f]:[-1.9,-1.1,-.25,.6][f];
 c.rotate(angle);c.fillStyle=blade;c.fillRect(0,-56,5,57);c.fillStyle='#d7ae69';c.fillRect(-6,-3,17,6);c.restore();c.restore();
 }
 return sheet;
}

const ENEMY_ATLAS_SOURCES={"boss": "/assets/enemy-atlas-boss.webp?v=original-20261105", "bandit": "/assets/enemy-atlas-bandit.webp?v=original-20261105", "assassin": "/assets/enemy-atlas-assassin.webp?v=original-20261105"};

const REAL_ENEMY_SOURCES={"boss": "/assets/enemy-real-boss.webp?v=original-20261105", "bandit": "/assets/enemy-real-bandit.webp?v=original-20261105", "assassin": "/assets/enemy-real-assassin.webp?v=original-20261105"};

const ENEMY_FRAME_W=192,ENEMY_FRAME_H=192;
const enemyFrameImages={};
for(const [kind,source] of Object.entries(REAL_ENEMY_SOURCES)){
 const img=new Image();img.src=source;enemyFrameImages[kind]=img;
}
// Wooden dummy 20-frame animation atlas embedded for offline/mobile play.
const woodenDummyAtlas=new Image();
woodenDummyAtlas.src='/assets/wooden-dummy.png?v=original-20261105';
function drawWoodenDummy(x,y,face,hit,state){
 if(!woodenDummyAtlas.complete||!woodenDummyAtlas.naturalWidth)return false;
 const moving=Math.abs(state?.vx||0)>8,attacking=(state?.windup||0)>0,dying=!!state?.dead;
 const phase=Math.floor(time*(moving?8:3));
 let frame=dying?16+Math.min(3,Math.floor((state?.deathTimer||0)*6)):attacking?8+(Math.floor(time*12)%4):hit>0?12+(Math.floor(time*12)%4):moving?4+(phase%4):phase%4;
 const sx=(frame%5)*192,sy=Math.floor(frame/5)*205;
 const targetW=134,targetH=144;
 ctx.save();ctx.translate(Math.round(x),Math.round(y));ctx.scale(-face,1);
 ctx.fillStyle='#071b2388';ctx.beginPath();ctx.ellipse(0,2,27,6,0,0,Math.PI*2);ctx.fill();
 if(hit>0&&Math.floor(time*20)%2===0)ctx.globalAlpha=.65;
 ctx.imageSmoothingEnabled=true;
 ctx.drawImage(woodenDummyAtlas,sx,sy,192,205,-targetW/2,-targetH,targetW,targetH);
 ctx.restore();return true;
}
// Per-enemy PNG animation frames; keep the previously deployed SVG as a safe fallback.
const CUSTOM_ENEMY_SOURCES={'산적 궁수':['archer',0],'산적 투사':['fighter',1],'산적 대장':['captain',2],'낭인 무사':['ronin',3],'회색늑대':['wolf',4],'호랑이':['tiger',5],'흑풍채 두목':['blackwind_boss',6],'자객':['assassin',null],'산적':['bandit',null],'목인':['dummy',null]};
const customEnemyImages={},customEnemyFrameImages={};
for(const [name,[slug,index]] of Object.entries(CUSTOM_ENEMY_SOURCES)){
 if(index!==null){const fallback=new Image();fallback.src='/assets/enemy-custom-'+index+'.svg?v=20261105';customEnemyImages[name]=fallback}
 customEnemyFrameImages[name]=Array.from({length:4},(_,i)=>{
  const img=new Image();img.src='/assets/enemy-frames/'+slug+'_'+i+'.svg?v=20261105c';return img;
 });
}
function drawCustomEnemy(x,y,face,kind,hit,state){
 const frames=customEnemyFrameImages[kind];
 const moving=Math.abs(state?.vx||0)>8,attacking=(state?.windup||0)>0||(state?.patternWindup||0)>0;
 const dead=!!state?.dead,action=dead?'death':hit>0?'hurt':attacking?'attack':moving?'walk':'idle';
 const fps=action==='walk'?9:action==='attack'?12:action==='hurt'?10:action==='death'?6:4;
 const phase=action==='death'?Math.min(3,Math.floor((state?.deathTimer||0)*fps)):
 action==='attack'?Math.max(0,Math.min(3,3-Math.floor((state?.windup||state?.patternWindup||0)*8))):
 Math.floor(time*fps+(state?.x||0)*.002)%4;
 const frame=frames?.[phase];
 const pngReady=!!(frame&&frame.complete&&frame.naturalWidth);
 const img=pngReady?frame:customEnemyImages[kind];
 if(!img||!img.complete||!img.naturalWidth)return false;
 const scale=kind==='흑풍채 두목'||kind==='호랑이'?1.5:1.25;
 const bob=action==='walk'?Math.sin(time*14)*2:0;
 ctx.save();ctx.translate(Math.round(x),Math.round(y+bob));ctx.scale(-face,1);
 if(hit>0&&Math.floor(time*20)%2===0)ctx.globalAlpha=.65;
 if(dead)ctx.globalAlpha=Math.max(.25,1-(state?.deathTimer||0)*.4);
 ctx.imageSmoothingEnabled=false;
 ctx.drawImage(img,-48*scale,-96*scale,96*scale,96*scale);
 ctx.restore();return true;
}
// User-supplied original pixel-art atlas: 18 frames of 192x192 pixels.
// The asset is optional until assets/enemy-original/archer-atlas.png is uploaded.
const originalArcherAtlas=new Image();
originalArcherAtlas.src='/assets/enemy-original/archer-atlas.png?v=20261106';
function drawOriginalArcher(x,y,face,hit,state){
 if(!originalArcherAtlas.complete||originalArcherAtlas.naturalWidth!==3456||originalArcherAtlas.naturalHeight!==192)return false;
 const moving=Math.abs(state?.vx||0)>8;
 const attacking=(state?.windup||0)>0||(state?.patternWindup||0)>0;
 const dead=!!state?.dead;
 const action=dead?'death':hit>0?'hurt':attacking?'attack':moving?'walk':'idle';
 const start={idle:0,walk:4,attack:8,hurt:12,death:14}[action];
 const count=action==='hurt'?2:4;
 const fps=action==='walk'?9:action==='attack'?12:action==='hurt'?10:action==='death'?6:4;
 const frame=action==='death'?Math.min(count-1,Math.floor((state?.deathTimer||0)*fps)):
 action==='attack'?Math.min(count-1,Math.max(0,Math.floor((1-Math.min(1,(state?.windup||state?.patternWindup||0)/Math.max(.01,(state?.windup||0)>0?(state?.attackDuration||.36):1.05)))*count))):
 Math.floor(time*fps+(state?.x||0)*.002)%count;
 ctx.save();ctx.translate(Math.round(x),Math.round(y));ctx.scale(face,1);
 if(hit>0&&Math.floor(time*20)%2===0)ctx.globalAlpha=.65;
 ctx.imageSmoothingEnabled=false;
 // Preserve the original transparent cell and anchor the feet at the ground.
 ctx.drawImage(originalArcherAtlas,(start+frame)*192,0,192,192,-96,-176,192,192);
 ctx.restore();return true;
}
// User-provided original 18-frame pixel art (4 idle, 4 walk, 4 attack, 2 hurt, 4 death).
const originalBanditAtlases={};
for(const [kind,slug] of [['산적 대장','captain'],['산적 투사','fighter'],['낭인 무사','ronin'],['회색늑대','wolf'],['흑풍채 두목','blackwind_boss']]){
 const img=new Image();img.src='/assets/enemy-original/'+slug+'-atlas.png?v=20261106';
 originalBanditAtlases[kind]=img;
}
function drawOriginalBandit(x,y,face,kind,hit,state){
 const img=originalBanditAtlases[kind];
 if(!img||!img.complete||img.naturalWidth!==3456||img.naturalHeight!==192)return false;
 const dead=!!state?.dead,moving=Math.abs(state?.vx||0)>8;
 const attacking=(state?.windup||0)>0||(state?.patternWindup||0)>0;
 const action=dead?'death':hit>0?'hurt':attacking?'attack':moving?'walk':'idle';
 const start={idle:0,walk:4,attack:8,hurt:12,death:14}[action],count=action==='hurt'?2:4;
 const fps=action==='walk'?9:action==='attack'?9:action==='hurt'?9:action==='death'?7:7;
 const frame=action==='death'?Math.min(count-1,Math.floor((state?.deathTimer||0)*fps)):
 action==='attack'?Math.min(count-1,Math.max(0,Math.floor((1-Math.min(1,(state?.windup||state?.patternWindup||0)/Math.max(.01,(state?.windup||0)>0?(state?.attackDuration||.36):1.05)))*count))):
 Math.floor(time*fps+(state?.x||0)*.002)%count;
 ctx.save();ctx.translate(Math.round(x),Math.round(y));ctx.scale(face,1);
 if(hit>0&&Math.floor(time*20)%2===0)ctx.globalAlpha=.65;
 ctx.imageSmoothingEnabled=false;
 ctx.drawImage(img,(start+frame)*192,0,192,192,-96,-176,192,192);
 ctx.restore();return true;
}
function drawEnemyPortrait(x,y,face,boss,kind,hit,state=null){
 if(drawOriginalBandit(x,y,face,kind,hit,state))return true;
 if(!boss&&kind==='산적 궁수'&&drawOriginalArcher(x,y,face,hit,state))return true;
 // Original pixel-art atlases take priority over temporary SVG stand-ins.
 // Do not render custom SVG frames until the real PNG atlas is committed.
 if(!boss&&kind==='목인'&&drawWoodenDummy(x,y,face,hit,state))return true;
 const key=boss?'boss':['자객'].includes(kind)?'assassin':['산적','산적 궁수','산적 투사','산적 대장','낭인 무사','청죽림 검객','마교 추격자','흑풍채 두목','호랑이','회색늑대'].includes(kind)?'bandit':null;
 const img=key?enemyFrameImages[key]:null;
 if(!img||!img.complete||!img.naturalWidth)return false;
 const moving=Math.abs(state?.vx||0)>8;
 const attacking=(state?.windup||0)>0;
 const skilling=(state?.patternWindup||0)>0;
 const hurt=hit>0;
 const dying=!!state?.dead;
 const row=dying?4:hurt?3:skilling?3:attacking?2:moving?1:0;
 let frame=0;
 if(dying){frame=3}
 else if(attacking){
  const duration=boss?(state?.phase===2?.32:.48):.36;
  frame=Math.max(0,Math.min(3,Math.floor((1-Math.max(0,state.windup)/duration)*4)));
 }else if(skilling){frame=Math.floor(time*6+(state?.x||0)*.005)%4}
 else if(hurt){frame=Math.floor(time*10)%4}
 else {frame=Math.floor(time*(moving?8:3)+(state?.x||0)*.005)%4}
 ctx.save();ctx.translate(Math.round(x),Math.round(y));
 // Original contact-sheet sprites face left; negative face makes movement face right.
 ctx.scale(-face,1);
 if(hurt&&Math.floor(time*20)%2===0)ctx.globalAlpha=.64;
 ctx.fillStyle='#071b2388';ctx.beginPath();ctx.ellipse(0,2,boss?39:28,6,0,0,Math.PI*2);ctx.fill();
 ctx.imageSmoothingEnabled=true;
 const target=boss?180:152;
 // Clamp source frames to the actual atlas dimensions to avoid blank frames.
 const cols=Math.floor(img.naturalWidth/ENEMY_FRAME_W),rows=Math.floor(img.naturalHeight/ENEMY_FRAME_H);
 if(cols<1||rows<1){ctx.restore();return false}
 const safeFrame=Math.min(Math.max(frame,0),cols-1),safeRow=Math.min(Math.max(row,0),rows-1);
 ctx.drawImage(img,safeFrame*ENEMY_FRAME_W,safeRow*ENEMY_FRAME_H,ENEMY_FRAME_W,ENEMY_FRAME_H,-target/2,-target+10,target,target);
 ctx.restore();return true;
}

const heroPortrait=new Image();
heroPortrait.src='/assets/hero-portrait.webp?v=original-20261105';
function drawNewHero(x,y,face,mode,hit){
 if(!heroPortrait.complete||!heroPortrait.naturalWidth)return false;
 // The original hero image is a 2x2 pose sheet, not a multi-frame animation atlas.
 // Keep its four source cells fixed to prevent a different-looking character.
 const pose=mode==='idle'||mode==='hurt'||mode==='run'||mode==='jump'?1:mode==='attack'||mode==='runAttack'||mode==='airAttack'||mode==='combo'?2:mode==='skill'?3:1;
 const tile=627, sx=(pose%2)*tile,sy=Math.floor(pose/2)*tile;
 const destW=125,destH=125;
 // Keep the feet anchored to the ground across poses; only the artwork moves.
 const idle=mode==='idle',hurt=mode==='hurt';
 const bob=idle?Math.sin(time*3)*1.2:0;
 const recoil=hurt?Math.sin(time*38)*2.5:0;
 ctx.save();ctx.translate(Math.round(x+recoil),Math.round(y+bob));ctx.scale(face,1);
 if(hit>0&&Math.floor(time*20)%2===0)ctx.globalAlpha=.55;
 ctx.fillStyle='#071b2388';ctx.beginPath();ctx.ellipse(0,2,28,6,0,0,Math.PI*2);ctx.fill();
 ctx.imageSmoothingEnabled=true;
 ctx.drawImage(heroPortrait,sx,sy,tile,tile,-destW/2,-destH+3,destW,destH);
 ctx.restore();return true;
}
function character(x,y,enemy=false,boss=false,face=1,attack=0,hit=0,kind='',enemyState=null){
 const moving=!enemy&&Math.abs(player.vx)>12,airborne=!enemy&&player.y<GROUND-7;
 const art=enemy?'basic':lastAttackArt;
 const mode=hit>0?'hurt':attack>0?(comboFlash>0?'combo':airborne?'airAttack':moving?'runAttack':lastAttackSkill?'skill':'attack'):airborne?'jump':moving?'run':'idle';
 const fps=mode==='run'?12:['attack','skill','runAttack','airAttack','combo'].includes(mode)?15:mode==='hurt'?14:mode==='idle'?4:7;
 const frame=['attack','skill','runAttack','airAttack','combo'].includes(mode)?Math.min(3,Math.floor((1-Math.min(1,attack/(lastAttackSkill?.32:.24)))*4)):Math.floor(time*fps)%4;
 if(enemy&&drawEnemyPortrait(x,y,face,boss,kind,hit,enemyState))return;
 if(!enemy&&drawNewHero(x,y,face,mode,hit))return;
 const robeRank=enemy?0:player.rank;const key=(enemy?(boss?'boss':'enemy'):'hero'+robeRank)+'_'+art;
 if(!spriteSheets.has(key))spriteSheets.set(key,makeSpriteSheet(enemy,boss,art,robeRank));
 const sheet=spriteSheets.get(key),row=SPRITE_MODES.indexOf(mode);
 ctx.save();ctx.translate(Math.round(x),Math.round(y));ctx.scale(face*(boss?1.16:1),boss?1.16:1);
 if(hit>0&&Math.floor(time*20)%2===0)ctx.globalAlpha=.55;
 ctx.fillStyle='#071b2388';ctx.beginPath();ctx.ellipse(0,2,31,6,0,0,Math.PI*2);ctx.fill();
 ctx.imageSmoothingEnabled=false;
 ctx.drawImage(sheet,frame*SPRITE_W,row*SPRITE_H,SPRITE_W,SPRITE_H,-SPRITE_W/2,-SPRITE_H+8,SPRITE_W,SPRITE_H);
 ctx.restore();
}
function drawBossTechnique(e){if(!e.boss||e.patternWindup<=0)return;
 const p=Math.max(0,Math.min(1,1-e.patternWindup/(e.storyBoss?.78:1.05)));
 const k=e.kind||'', isDemon=/마군|마교|혈/.test(k), isBlack=/흑련/.test(k);
 const color=isDemon?'#ff5863':isBlack?'#b597ff':'#95e4ff';
 ctx.save();ctx.translate(e.x,e.y-85);ctx.globalAlpha=.5+.5*p;ctx.shadowColor=color;ctx.shadowBlur=18;ctx.strokeStyle=color;ctx.lineWidth=4;
 if(isDemon){for(let i=0;i<3;i++){ctx.beginPath();ctx.moveTo(-44+i*42,10);ctx.quadraticCurveTo(-60+i*42,-40-p*26,-24+i*42,-75-p*36);ctx.stroke()}}
 else if(isBlack){ctx.beginPath();ctx.arc(0,0,38+p*31,0,Math.PI*2);ctx.stroke();ctx.beginPath();ctx.arc(0,0,22+p*18,0,Math.PI*2);ctx.stroke()}
 else {for(let i=-1;i<=1;i++){ctx.beginPath();ctx.moveTo(-54,-24+i*24);ctx.quadraticCurveTo(0,-55+i*24,64+40*p,-24+i*24);ctx.stroke()}}
 ctx.restore();}
function drawSpecialEffects(){
 for(const a of impactEffects){const q=Math.max(0,a.life/a.max);ctx.save();ctx.globalAlpha=q;ctx.translate(a.x,a.y);ctx.strokeStyle=a.color||'#ffe3b2';ctx.lineWidth=3+q*4;ctx.shadowColor=ctx.strokeStyle;ctx.shadowBlur=14;for(let j=0;j<6;j++){const t=j*Math.PI/3;ctx.beginPath();ctx.moveTo(Math.cos(t)*13,Math.sin(t)*13);ctx.lineTo(Math.cos(t)*(13+(1-q)*38),Math.sin(t)*(13+(1-q)*38));ctx.stroke()}ctx.restore()}
 for(const a of bossEffects){const q=Math.max(0,a.life/a.max);ctx.save();ctx.globalAlpha=q*.85;ctx.translate(a.x,a.y);ctx.strokeStyle=String(a.kind).includes('마')?'#ff666d':String(a.kind).includes('흑련')?'#b69aff':'#8ce6fa';ctx.lineWidth=5;ctx.shadowColor=ctx.strokeStyle;ctx.shadowBlur=20;ctx.beginPath();ctx.ellipse(0,0,a.radius*(1-q*.45),22,0,0,Math.PI*2);ctx.stroke();ctx.restore()}
 for(const a of allyEffects){const q=Math.max(0,a.life/a.max);ctx.save();ctx.globalAlpha=q;ctx.translate(a.x,a.y);ctx.strokeStyle=a.kind==='청죽림'?'#7df3db':a.kind==='낙양성'?'#92eab5':'#f7ab63';ctx.lineWidth=6;ctx.shadowBlur=18;ctx.shadowColor=ctx.strokeStyle;ctx.beginPath();if(a.kind==='낙양성'){ctx.arc(0,0,30+(1-q)*22,0,Math.PI*2)}else{ctx.moveTo(-40,-26);ctx.lineTo(35,14);ctx.moveTo(-40,17);ctx.lineTo(38,-29)}ctx.stroke();ctx.restore()}
}
function render(){ctx.save();ctx.clearRect(0,0,viewW,viewH);ctx.translate((Math.random()-.5)*shake,(Math.random()-.5)*shake);drawBackground();ctx.save();ctx.translate(-camera,0);ctx.fillStyle='#d7c9a2';ctx.font='15px Malgun Gothic';ctx.fillText(zone==='청죽림'?'은둔 검객 청하 · E/Y 대화':zone==='낙양성'?'의원 소연 · E/Y 대화':zone==='혈마곡'?'정찰대장 무진 · E/Y 대화':zone==='청운진'?'청운진 상인 · E로 대화':zone==='흑풍산'?'흑풍산 입구':'현진 도장 · E로 대화',110,342);ctx.fillStyle='#7ebfc4';ctx.fillRect(147,371,3,41);ctx.beginPath();ctx.arc(148,366,10,0,Math.PI*2);ctx.fill();ctx.fillStyle='#d9c8b0';ctx.fillRect(143,352,10,15);if(['청죽림','낙양성','혈마곡'].includes(zone)){ctx.fillStyle='#cfbe91';ctx.fillRect(276,390,24,45);ctx.fillStyle='#91d3c8';ctx.fillRect(272,429,32,75);ctx.fillStyle='#e3bd9a';ctx.beginPath();ctx.arc(288,380,14,0,Math.PI*2);ctx.fill();ctx.fillStyle='#f0dab0';ctx.font='14px Malgun Gothic';ctx.fillText('지역 인연 NPC · Y',240,354)}ctx.fillStyle='#d9ca95';ctx.font='bold 14px Malgun Gothic';ctx.fillText(zone==='청운진'?'평화 지역':zone==='흑풍산'?'산적 출몰 지역':'수련장 →',490,482);for(const e of enemies){character(e.x,e.y,true,e.boss,e.face,0,e.hit,e.kind,e);if(e.dead)continue;drawBossTechnique(e);ctx.fillStyle='#121f25';ctx.fillRect(e.x-(e.boss?49:27),e.y-(e.boss?155:139),e.boss?98:54,7);ctx.fillStyle=e.boss?'#ce6e57':'#b78c68';ctx.fillRect(e.x-(e.boss?49:27),e.y-(e.boss?155:139),(e.boss?98:54)*Math.max(0,e.hp/e.maxhp),7);if(e.boss&&e.patternWindup>0){if(e.counterStance){ctx.strokeStyle='#8ff3e2';ctx.lineWidth=7;ctx.beginPath();ctx.arc(e.x,e.y-65,54,0,Math.PI*2);ctx.stroke();}ctx.fillStyle='#f582822d';ctx.beginPath();ctx.ellipse(Number.isFinite(e.patternX)?e.patternX:e.x,GROUND-4,e.patternRadius,24,0,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#ff8e8e';ctx.lineWidth=4;ctx.beginPath();ctx.ellipse(Number.isFinite(e.patternX)?e.patternX:e.x,GROUND-4,e.patternRadius,24,0,0,Math.PI*2);ctx.stroke()}if(e.windup>0){ctx.strokeStyle='#f7b27a';ctx.lineWidth=3;ctx.beginPath();ctx.arc(e.x,e.y-64,e.boss?69:43,0,Math.PI*2);ctx.stroke()}if(!e.boss){ctx.font='13px Malgun Gothic';ctx.fillStyle=e.kind==='자객'?'#ffb1a0':'#eee1bf';ctx.fillText(e.kind,e.x-17,e.y-145)}if(e.boss){if(e.hp<=e.maxhp*.5){ctx.fillStyle='#ff8a83';ctx.font='bold 13px Malgun Gothic';ctx.fillText('2페이즈',e.x-27,e.y-185)}ctx.font='bold 17px Malgun Gothic';ctx.fillStyle='#ffd7b1';ctx.fillText(e.kind,e.x-65,e.y-165)}}for(const a of afterimages){ctx.save();ctx.globalAlpha=Math.max(0,a.life/.27)*.28;character(a.x,a.y,false,false,a.face,0,0);ctx.restore()}drawCompanion();if(heroPortrait.complete&&heroPortrait.naturalWidth){character(player.x,player.y,false,false,player.face,player.attackAnim,player.inv)}else if(!(martialSpriteTime>0&&drawMartialSprite(player.x,player.y,player.face,martialSpriteArt,martialSpriteSkill)))character(player.x,player.y,false,false,player.face,player.attackAnim,player.inv);for(const fx of artEffects)drawArtEffect(fx);drawSpecialEffects();for(const u of ultimateVisuals)drawUltimateVisual(u);if(player.dashInv>0){ctx.save();ctx.strokeStyle='#91f7ef';ctx.globalAlpha=.6;ctx.lineWidth=3;ctx.beginPath();ctx.ellipse(player.x,player.y-55,24,63,0,0,Math.PI*2);ctx.stroke();ctx.restore()}for(const ring of bossRings){ctx.save();ctx.globalAlpha=ring.life/ring.max*.8;ctx.strokeStyle='#ffa6a6';ctx.lineWidth=9;ctx.beginPath();ctx.ellipse(ring.x,ring.y,ring.radius,25,0,0,Math.PI*2);ctx.stroke();ctx.restore()}for(const f of floatingTexts){ctx.save();ctx.globalAlpha=Math.min(1,f.life*2);ctx.fillStyle=f.color;ctx.font='bold 19px Malgun Gothic,sans-serif';ctx.textAlign='center';ctx.fillText(f.text,f.x,f.y);ctx.restore()}for(const s of slashes){if(s.ultimate)continue;ctx.save();ctx.globalAlpha=Math.min(1,s.life/(s.skill?.2:.08));ctx.strokeStyle=s.combo==='custom'?(s.art==='thunder'?'#b4a1ff':s.art==='palm'?'#ffae73':'#7df3db'):s.combo?'#ffd18b':s.art==='thunder'?'#b7abff':s.art==='palm'?'#ffb279':s.art==='cloud'?'#80f6d8':s.skill?'#90edff':'#f4dfaa';ctx.lineWidth=s.combo?23:s.skill?15:11;ctx.lineCap='round';ctx.shadowBlur=24;ctx.shadowColor=s.art==='thunder'?'#ad9aff':s.art==='cloud'?'#5be6d0':s.art==='palm'?'#f8a675':s.skill?'#67d6ed':'#f2d3a0';ctx.beginPath();if(s.skill){ctx.moveTo(s.x-s.dir*26,s.y-23);ctx.quadraticCurveTo(s.x,s.y-55,s.x+s.dir*56,s.y+12)}else{ctx.arc(s.x+s.dir*29,s.y,69,-.95,.7)}ctx.stroke();ctx.restore()}for(const p of particles){ctx.globalAlpha=Math.min(1,p.life*2);ctx.fillStyle=p.color;ctx.fillRect(p.x,p.y,p.size,p.size)}ctx.globalAlpha=1;ctx.restore();ctx.restore();if(state==='play'&&player.x<500){ctx.fillStyle='#f2e4c6';ctx.font='15px Malgun Gothic';ctx.textAlign='center';ctx.fillText('무당파 수련장',Math.max(120,viewW/2),80);ctx.textAlign='start'}}function frame(t){const dt=Math.min(.033,(t-last)/1000||.016);last=t;update(dt);render();requestAnimationFrame(frame)}requestAnimationFrame(frame);window.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','ArrowUp','Space'].includes(e.code))e.preventDefault();if(e.repeat&&['KeyJ','KeyK','KeyE','KeyP','ShiftLeft','ShiftRight'].includes(e.code))return;keys.add(e.code);if(state==='play'){if(e.code==='ShiftLeft'||e.code==='ShiftRight')dash();if(e.code==='KeyJ')attack(false);if(e.code==='KeyX')useUltimate();if(e.code==='KeyK')attack(true);if(e.code==='KeyE')interact();if(e.code==='KeyP')save();if(e.code==='KeyM')showMap();if(e.code==='KeyO')showStory();if(e.code==='KeyY')showLocalNPC();if(e.code==='KeyV')showCompanions();if(e.code==='KeyQ')showQuest();if(e.code==='KeyU')showSkills();if(e.code==='KeyC')showComboEditor();if(e.code==='KeyZ')showJobs();if(e.code==='KeyT')showCultivation();if(e.code==='KeyN')showInnerArts();if(e.code==='KeyR')showBreakthrough();if(e.code==='KeyB')showLibrary();if(e.code==='KeyI')showBag();if(e.code==='KeyG')showSect();if(e.code==='KeyF')showDiplomacy();if(e.code==='KeyH')usePotion()}});window.addEventListener('keyup',e=>keys.delete(e.code));const mobilePointerReleases=[];
document.querySelectorAll('[data-key]').forEach(b=>{
 const k=b.dataset.key;let pointer=null;
 function release(){
   pointer=null;keys.delete(k);b.classList.remove('pressed');
 }
 function down(e){
   if(state!=='play'||pointer!==null||e.button!==0)return;
   e.preventDefault();pointer=e.pointerId;
   try{b.setPointerCapture(e.pointerId)}catch(_){}
   keys.add(k);b.classList.add('pressed');
   if(k==='ShiftLeft')dash();
   else if(k==='KeyJ')attack(false);
   else if(k==='KeyK')attack(true);
   else if(k==='KeyX')useUltimate();
   else if(k==='KeyE')interact();
 }
 function up(e){
   if(pointer!==e.pointerId)return;
   if(e.cancelable)e.preventDefault();
   release();
 }
 b.addEventListener('pointerdown',down,{passive:false});
 b.addEventListener('pointerup',up,{passive:false});
 b.addEventListener('pointercancel',up,{passive:false});
 b.addEventListener('lostpointercapture',e=>{if(pointer===e.pointerId)release()});
 b.addEventListener('contextmenu',e=>e.preventDefault());
 mobilePointerReleases.push(release);
});
function resetMobileInput(){
 mobilePointerReleases.forEach(release=>release());
 keys.clear();
}
window.addEventListener('blur',resetMobileInput);
document.addEventListener('visibilitychange',()=>{
 if(document.hidden){resetMobileInput();if(state==='play')saveSilent()}
});
window.addEventListener('pagehide',()=>{
 resetMobileInput();if(state==='play')saveSilent()
});
function regionMove(dest){if(player.trial){toast('승급 시험 또는 무림 대회 중에는 지역을 이동할 수 없습니다');return}if(!STORY_ZONES.includes(dest))return;if(dest==='청죽림'&&storyStage<1||dest==='낙양성'&&storyStage<3||dest==='혈마곡'&&storyStage<5){toast('이야기를 진행해야 개방되는 지역입니다');return;}zone=dest;resetField();camera=0;resume();updateUI();toast(dest+'에 도착했습니다');saveSilent()}
function saveSilent(){return storeSave(true)}
document.getElementById('jobBtn').addEventListener('click',()=>{if(state!=='menu')showJobs()});
function showJobs(){
 let html='<p>1차 전직: 3경지 이상 · 은전 80냥. 2차 전직: 10경지·일대제자 이상 · 은전 150냥·공헌도 60. 전직 장소: 수련장.</p><p>현재 전공: <b>'+JOBS[selectedJob].name+'</b>'+(advancedJob?' → <b>'+ADVANCED_JOBS[selectedJob].name+'</b>':'')+'</p>'; 
 for(const [id,j] of Object.entries(JOBS)){if(id==='disciple')continue;html+='<div class="factionLine"><b>'+j.name+'</b><p>'+j.desc+'</p><button class="btn jobChoice" data-job="'+id+'" '+(selectedJob===id?'disabled':'')+'>'+ (selectedJob===id?'현재 전공':'전직 (80냥)')+'</button></div>'}
 if(ADVANCED_JOBS[selectedJob]){const a=ADVANCED_JOBS[selectedJob];html+='<div class="factionLine"><b>2차 전직 · '+a.name+'</b><p>'+a.desc+' · X 필살기: '+a.ultimate+'</p><button class="btn" id="advancedJobButton" '+(advancedJob?'disabled':'')+'>'+(advancedJob?'2차 전직 완료':'2차 전직 (150냥·공헌도 60)')+'</button></div>';}modal('무당파 전직 · 전공 선택',html);const adv=$('advancedJobButton');if(adv)adv.onclick=()=>{if(advancedJob){toast('이미 2차 전직을 완료했습니다');return}if(player.level<10||player.rank<2){toast('10경지·일대제자 이상이 필요합니다');return}if(zone!=='수련장'||player.trial){toast('수련장에서 시험 중이 아닐 때 전직할 수 있습니다');return}if(gold<150||contribution<60){toast('은전 150냥·공헌도 60이 필요합니다');return}gold-=150;contribution-=60;advancedJob=ADVANCED_JOBS[selectedJob].id;saveSilent();showJobs();toast(ADVANCED_JOBS[selectedJob].name+' 등극! X 필살기 개방');};
 document.querySelectorAll('.jobChoice').forEach(b=>b.onclick=()=>{
  const job=b.dataset.job;if(!Object.hasOwn(JOBS,job)||job==='disciple')return;
  if(player.level<3){toast('전직에는 3경지 이상이 필요합니다');return}
  if(zone!=='수련장'){toast('무당파 수련장에서 전직할 수 있습니다');return}
  if(player.trial){toast('승급 시험 중에는 전직할 수 없습니다');return}
  if(gold<80){toast('전직에 필요한 은전 80냥이 부족합니다');return}
  gold-=80;selectedJob=job;advancedJob='';saveSilent();showJobs();toast(JOBS[job].name+' 전직 완료');
 });
}
function modal(title,content){if(state==='menu')return;showPanel(title,content,'닫기',resume);$('panel').classList.add('panelScrollable')}
function showLibrary(){if(zone!=='수련장'){toast('장경각은 무당파 본산에 있습니다');return}const cost=3+secretLevel*2;modal('무당파 장경각 · 비급 연구','<p>태극검법 비전 '+secretLevel+'성 / 5성</p><p>비급 조각 '+manuals+'개 · 문파 공헌도 '+contribution+'</p><p>수련 비용: 비급 조각 '+cost+'개, 공헌도 '+(15+secretLevel*15)+'점</p><p>비전 수련 시 검격과 태극검기의 피해가 증가합니다.</p><button class="btn" id="learnSecret">비전 무공 연마</button><p><button class="btn" id="martialLibrary">신규 무공 비급 열람</button></p>');$('martialLibrary').onclick=showMartialLibrary;$('learnSecret').onclick=()=>{if(secretLevel>=5){toast('비전 무공을 모두 연마했습니다');return}if(manuals<cost||contribution<15+secretLevel*15){toast('비급 조각이나 문파 공헌도가 부족합니다');return}manuals-=cost;contribution-=15+secretLevel*15;secretLevel++;resume();toast('태극검법 비전 '+secretLevel+'성 습득!');saveSilent()}}function showMap(){modal('강호 지도','<p>목적지를 선택하면 즉시 이동합니다.</p><button class="btn" id="z1">무당파 수련장</button><button class="btn" id="z2">청운진 (상점·의뢰)</button><button class="btn" id="z3">흑풍산 (자객·산적)</button><button class="btn" id="z4">청죽림 (1장 개방)</button><button class="btn" id="z5">낙양성 (2장 개방)</button><button class="btn" id="z6">혈마곡 (3장 개방)</button>');$('z1').onclick=()=>regionMove('수련장');$('z2').onclick=()=>regionMove('청운진');$('z3').onclick=()=>regionMove('흑풍산');$('z4').onclick=()=>regionMove('청죽림');$('z5').onclick=()=>regionMove('낙양성');$('z6').onclick=()=>regionMove('혈마곡')}
function startStoryBoss(where,after){if(zone!==where){toast(where+'에서 도전할 수 있습니다');return}if(storyBossActive){toast('이미 보스와 대결 중입니다');return}const b=STORY_BOSSES[where];storyBossActive=true;player.trial=true;trialBoss=true;enemies=[];spawnEnemy(Math.min(WORLD-300,player.x+580),true);const e=enemies[enemies.length-1];e.kind=b.name;e.hp=e.maxhp=b.hp+player.rank*45;e.storyBoss=true;e.storyStageAfter=after;e.storyReward=60+after*35;e.patternClock=2.7;if(sideQuest[where]===2){e.hp=Math.round(e.hp*.9);e.maxhp=e.hp}resume();toast(b.name+' 등장! 붉은 범위를 피하며 싸우세요')}
const BOND_INFO={청죽림:{name:'청하',art:'유운일섬',effect:'유운검법 계열 피해 +10%'},낙양성:{name:'소연',art:'회춘진기',effect:'운기조식 기혈 회복 +40%'},혈마곡:{name:'무진',art:'파마검기',effect:'검기 피해 +12%'}};
function showCompanions(){let html='<p>지역 NPC 의뢰를 완료하고 인연도 35 이상이면 동료로 영입할 수 있습니다. 한 명만 동행합니다.</p>';
for(const z of Object.keys(BOND_INFO)){const b=BOND_INFO[z],recruited=companions.includes(z),ready=sideQuest[z]===2&&npcTrust[z]>=35;
html+='<div class="factionLine"><b>'+b.name+'</b> · '+z+'<br><span>인연도 '+npcTrust[z]+'/100 · '+(recruited?'영입 완료':ready?'영입 가능':'의뢰 완료 및 인연도 35 필요')+'</span><br><span>비전: '+b.art+' · '+b.effect+'</span><div class="factionBtns">';
if(!recruited)html+='<button class="recruitAlly" data-zone="'+z+'" '+(!ready?'disabled':'')+'>동료 영입</button>';
else {html+='<button class="equipAlly" data-zone="'+z+'">'+(activeCompanion===z?'동행 해제':'동행하기')+'</button>';if(!bondArts.includes(z))html+='<button class="bondLearn" data-zone="'+z+'" '+(manuals<3||contribution<25?'disabled':'')+'>인연 비전 전수 (비급 3 · 공헌 25)</button>';else html+='<span>비전 습득 완료 ✓</span>';}html+='</div></div>'}
modal('강호 동료 · 인연 무공',html);document.querySelectorAll('.recruitAlly').forEach(b=>b.onclick=()=>{const z=b.dataset.zone;if(sideQuest[z]!==2||npcTrust[z]<35||companions.includes(z))return;companions.push(z);activeCompanion=z;saveSilent();showCompanions();toast(BOND_INFO[z].name+' 동료 합류!')});document.querySelectorAll('.equipAlly').forEach(b=>b.onclick=()=>{activeCompanion=activeCompanion===b.dataset.zone?'':b.dataset.zone;saveSilent();showCompanions();toast(activeCompanion?BOND_INFO[activeCompanion].name+' 동행 시작':'동행 해제')});document.querySelectorAll('.bondLearn').forEach(b=>b.onclick=()=>{const z=b.dataset.zone;if(!companions.includes(z)||bondArts.includes(z)||manuals<3||contribution<25)return;manuals-=3;contribution-=25;bondArts.push(z);saveSilent();showCompanions();toast(BOND_INFO[z].art+' 습득!')})}
function defeatEnemy(e,source){
 if(e.dead)return;e.dead=true;e.deathTimer=0;burst(e.x,e.y-45,'#ffd59b',22);const earnedXP=e.boss?(ENEMY_TYPES[e.kind]?.xp||115):(ENEMY_TYPES[e.kind]?.xp||40);gainXP(earnedXP);
 if(!e.boss){if(Object.hasOwn(sideKills,zone))sideKills[zone]++;gold+=zone==='흑풍산'?12:5;questKills++;contribution+=zone==='흑풍산'?3:1;if(Math.random()<.16)manuals++;if(Math.random()<.34)herbs++;if(Math.random()<.20)ore++;player.kills++;if(player.kills%3===0)saveSilent();toast((source==='companion'?'동료 협공 성공! ':'적 제압! ')+e.kind+' · 경험치 +'+earnedXP)}
 else if(e.storyBoss){storyBossActive=false;player.trial=false;trialBoss=false;storyStage=Math.max(storyStage,e.storyStageAfter||0);gold+=e.storyReward||0;contribution+=25;gainXP(125);toast('강호 보스 격파! 은전 +'+(e.storyReward||0)+' · 공헌도 +25');saveSilent()}
 else if(arenaFaction){const f=arenaFaction;arenaFaction=null;player.trial=false;trialBoss=false;leagueWins++;sectFame+=30;sectFunds+=90;factionRelations[f]=Math.min(100,factionRelations[f]+12);toast(f+' 대련 승리! 명성 +30, 자금 +90');saveSilent()}
 else {contribution+=trialTier>=2?50:30;manuals+=trialTier>=2?4:2;bossDefeated=true;trialBoss=false;player.trial=false;toast('승급 대결 승리! 입구에서 교관에게 보고하세요');saveSilent()}
}
function companionTick(dt){if(!activeCompanion||!companions.includes(activeCompanion))return;companionAttackClock=Math.max(0,companionAttackClock-dt);if(companionAttackClock>0)return;const target=enemies.filter(e=>!e.dead&&Math.abs(e.x-player.x)<330).sort((a,b)=>Math.abs(a.x-player.x)-Math.abs(b.x-player.x))[0];if(!target)return;companionAttackClock=activeCompanion==='청죽림'?1.05:1.5;const dmg=Math.round((12+player.level*2)*(activeCompanion==='혈마곡'?1.4:1));if(activeCompanion==='낙양성'){player.hp=Math.min(player.maxhp,player.hp+Math.max(3,Math.round(player.maxhp*.04)));floatText(player.x,player.y-125,'+회복','#86ebc2')}allyEffects.push({x:target.x,y:target.y-61,from:player.x-player.face*77,kind:activeCompanion,life:.52,max:.52});target.hp-=dmg;target.hit=.24;floatText(target.x,target.y-110,'동료 -'+dmg,'#a2f2d0');burst(target.x,target.y-65,'#83d8bb',7);if(target.hp<=0&&!target.dead){defeatEnemy(target,'companion');toast(BOND_INFO[activeCompanion].name+' 협공 성공!')}}
function drawCompanion(){if(!activeCompanion)return;
 const x=player.x-player.face*77, kind=activeCompanion;
 const color=kind==='청죽림'?'#74bf9e':kind==='낙양성'?'#f0dabb':'#c38e7d';
 const flare=kind==='청죽림'?'#8ff9d4':kind==='낙양성'?'#b8f2c8':'#ffb66d';
 const busy=allyEffects.some(a=>a.kind===kind);
 ctx.save();ctx.translate(x,player.y);ctx.scale(player.face,1);ctx.globalAlpha=.92;
 ctx.fillStyle='#0c1c2388';ctx.beginPath();ctx.ellipse(0,2,25,6,0,0,Math.PI*2);ctx.fill();
 ctx.fillStyle='#2c3545';ctx.fillRect(-15,-32,12,32);ctx.fillRect(3,-32,12,32);
 ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(-22,-92);ctx.lineTo(20,-92);ctx.lineTo(27,-31);ctx.lineTo(-27,-31);ctx.fill();
 ctx.fillStyle='#d8bea0';ctx.fillRect(-13,-119,26,27);ctx.fillStyle='#262d3a';ctx.fillRect(-15,-121,30,9);ctx.fillRect(-6,-130,13,12);
 ctx.strokeStyle=color;ctx.lineCap='round';ctx.lineWidth=11;ctx.beginPath();ctx.moveTo(-16,-83);ctx.lineTo(-23,-56);ctx.moveTo(17,-84);ctx.lineTo(busy?45:26,busy?-89:-60);ctx.stroke();
 ctx.strokeStyle=flare;ctx.lineWidth=4;ctx.shadowBlur=busy?16:0;ctx.shadowColor=flare;ctx.beginPath();
 if(kind==='낙양성'){ctx.arc(busy?51:30,busy?-88:-62,8,0,Math.PI*2)}
 else{ctx.moveTo(busy?43:26,busy?-92:-64);ctx.lineTo(busy?84:43,busy?-138:-98)}ctx.stroke();ctx.restore();
 ctx.save();ctx.fillStyle='#a8f1ce';ctx.font='bold 13px Malgun Gothic';ctx.textAlign='center';ctx.fillText(BOND_INFO[kind].name,x,player.y-145);ctx.restore()}

function showLocalNPC(){if(!['청죽림','낙양성','혈마곡'].includes(zone)){toast('지역 NPC는 청죽림·낙양성·혈마곡에서 만날 수 있습니다');return}
const data={청죽림:{who:'은둔 검객 청하',intro:'죽림 깊숙한 곳에서 검법의 흔적을 찾는 은둔 고수.',task:'검객의 호위병 3명을 제압하고 돌아오라.',need:3},낙양성:{who:'의원 소연',intro:'낙양에서 다친 백성을 돌보는 의원.',task:'약초 2개를 구해 의원에게 전달하라.',need:2},혈마곡:{who:'정찰대장 무진',intro:'마교의 움직임을 감시하는 무당파 정찰대장.',task:'추격자 5명을 물리쳐 혈마곡의 매복을 해제하라.',need:5}}[zone];
const q=sideQuest[zone],progress=zone==='낙양성'?herbs:sideKills[zone],remaining=Math.max(0,data.need-progress);
let html='<p><b>'+data.who+'</b><br>'+data.intro+'</p>';
if(q===0)html+='<p>「'+data.task+'」</p><button class="btn" id="npcAccept">의뢰 수락</button>';
else if(q===1)html+='<p>의뢰 진행 중 · '+Math.min(progress,data.need)+' / '+data.need+'</p><button class="btn" id="npcTurn">'+(remaining===0?'임무 완료 보고':'진행 상황 확인')+'</button>';
else html+='<p>「은혜는 잊지 않겠소. 앞으로도 무당의 도가 함께하길.」</p><p class="gold">인연 +'+npcTrust[zone]+' · 완료한 지역 의뢰</p>';
if(q===2)html+='<button class="btn" id="npcParty">동료 영입·인연 무공</button>';html+='<button class="btn" id="npcStory">메인 이야기 보기</button>';
modal(data.who+' · 지역 인연',html);
if(q===0)$('npcAccept').onclick=()=>{sideQuest[zone]=1;if(zone!=='낙양성')sideKills[zone]=0;saveSilent();resume();toast(data.who+'의 의뢰 수락!')};
if(q===1)$('npcTurn').onclick=()=>{if(remaining>0){toast('의뢰 조건이 부족합니다 · 남은 수량 '+remaining);return}if(zone==='낙양성')herbs-=2;sideQuest[zone]=2;npcTrust[zone]=Math.min(100,npcTrust[zone]+35);gold+=65;contribution+=25;manuals+=2;sectFame+=15;saveSilent();showLocalNPC();toast('인연 의뢰 완료! 은전 +65 · 공헌 +25 · 비급 +2')};
if(q===2)$('npcParty').onclick=showCompanions;$('npcStory').onclick=showStory;
}
function showStory(){let title='강호 이야기 · 제'+(Math.min(3,Math.floor(storyStage/2)+1))+'장',body='';
if(storyStage===0){body='<p>청운진에 수상한 서찰이 도착했다. 사라진 무당파 비급을 쫓아 청죽림으로 향하자.</p><button class="btn" id="storyAction">서찰을 받고 청죽림 개방</button>';modal(title,body);$('storyAction').onclick=()=>{storyStage=1;resume();toast('청죽림 개방! M으로 이동하세요');saveSilent()};return}
if(storyStage===1){modal(title,'<p>청죽림에서 무당파 비급을 훔친 검객과 맞선다. 청죽림으로 이동한 뒤 결투하라.</p><button class="btn" id="storyAction">청죽림 검객 도전</button>');$('storyAction').onclick=()=>startStoryBoss('청죽림',2);return}
if(storyStage===2){modal('제1장 완료 · 갈림길','<p>비급을 되찾았으나 낙양성에 위협이 다가온다. 민초를 돕거나 적의 조직을 추적할 수 있다.</p><button class="btn" id="helpPeople">민초 구휼 — 명성 상승</button><button class="btn" id="pursue">흑련회 추적 — 공헌도 상승</button>');$('helpPeople').onclick=()=>chooseStory('구휼');$('pursue').onclick=()=>chooseStory('추적');return}
if(storyStage===3){modal('제2장 · 낙양의 그림자','<p>선택한 행보: '+storyChoice+' — 낙양성에서 흑련회 당주의 행방을 밝혀라.</p><button class="btn" id="storyAction">흑련회 당주 도전</button>');$('storyAction').onclick=()=>startStoryBoss('낙양성',4);return}
if(storyStage===4){modal('제2장 완료','<p>당주에게서 혈마곡의 위치가 적힌 지도를 얻었다. 혈마곡의 마군을 막아라.</p><button class="btn" id="storyAction">혈마곡 개방</button>');$('storyAction').onclick=()=>{storyStage=5;resume();toast('혈마곡 개방!');saveSilent()};return}
if(storyStage===5){modal('제3장 · 혈마곡의 결전','<p>혈마곡 마군과 최후의 대결. 무당의 이름으로 강호의 혼란을 끝내라.</p><button class="btn" id="storyAction">혈마곡 마군 도전</button>');$('storyAction').onclick=()=>startStoryBoss('혈마곡',6);return}
modal('강호 이야기 완결','<p>마군이 쓰러졌다. 당신의 선택('+storyChoice+')은 무림에 오래도록 기억될 것이다.</p><p>이야기를 완결해도 수련, 문파 경영, 무림 대련은 계속할 수 있습니다.</p>')}
function chooseStory(choice){if(storyStage!==2)return;storyChoice=choice;storyStage=3;if(choice==='구휼'){sectFame+=45;potions+=3}else{contribution+=50;gold+=80}resume();toast(choice+' 선택! 낙양성이 개방됐습니다');saveSilent()}
function showQuest(){let t=questStage===0?'청운진에 방문하여 약초 채집 의뢰를 수락하세요.':questStage===1?'약초 3개를 모아 청운진 약재상에게 전달하세요. 현재 '+herbs+'/3': '흑풍산의 산적 5명을 제압하세요. 현재 '+questKills+'/5';modal('의뢰 기록',t+'<p>완료 보상: 은전 · 경험치 · 회복약</p>')}
function showTown(){if(questStage===0){modal('청운진 · 약재상','약초 3개를 모아오면 은전 70냥과 경험치 60을 드리겠습니다.<p><button class="btn" id="takeQuest">의뢰 수락</button></p>');$('takeQuest').onclick=()=>{questStage=1;resume();toast('약초 채집 의뢰 수락! 흑풍산으로 가세요')}}else if(questStage===1&&herbs>=3){modal('약재상 · 의뢰 완료','약초를 잘 구해왔군요. 수고했습니다.<p><button class="btn" id="finishQuest">보상 받기</button></p>');$('finishQuest').onclick=()=>{herbs-=3;gold+=70;gainXP(60);questStage=2;questKills=0;potions++;resume();toast('의뢰 완료! 은전 +70, 경험치 +60, 회복약 +1');saveSilent()}}else if(questStage===2&&questKills>=5){modal('청운진 · 포도두령','산적 소탕에 큰 공을 세웠습니다.<p><button class="btn" id="finishQuest">보상 받기</button></p>');$('finishQuest').onclick=()=>{gold+=120;gainXP(90);potions+=2;questKills=0;questClaimed++;resume();toast('산적 토벌 완료! 은전 +120, 경험치 +90');saveSilent()}}else modal('청운진 · 상인','현재 의뢰 상황을 확인하고 사냥터에서 필요한 재료를 모으세요.<p>마을에서는 적이 등장하지 않습니다.</p>')}
const INNER_ARTS={balanced:{name:'태극심법',desc:'공격과 회복이 균형을 이루는 기본 심법'},pure:{name:'순양무극공',desc:'검기 위력 +12%, 검기 내공 소비 -18%, 운기 회복 +30%'},fluid:{name:'유수심법',desc:'받는 피해 -15%, 운기 중 기혈 회복 강화'}};
function showCultivation(){let h='<p>사용 가능한 수련점 <b>'+cultivationPoints+'</b>점 · 경지 상승마다 1점 지급 · 각 계통 최대 5단계</p>';const defs=[['sword','검술','검격·검기 피해 단계당 +8%'],['palm','장법','무당장권 피해 단계당 +8%'],['qi','내공','운기 회복량과 자연 내공 회복 상승'],['movement','경공','이동 속도 증가와 경공 재사용 시간 감소']];for(const [k,n,d] of defs){h+='<div class="factionLine"><b>'+n+' '+cultivationTree[k]+'/5</b><p>'+d+'</p><button class="treeUpgrade" data-tree="'+k+'" '+(cultivationPoints<=0||cultivationTree[k]>=5?'disabled':'')+'>수련점 1점 투자</button></div>'}modal('무당파 비전 · 무공 수련 트리',h);document.querySelectorAll('.treeUpgrade').forEach(b=>b.onclick=()=>{const k=b.dataset.tree;if(cultivationPoints<=0||cultivationTree[k]>=5)return;cultivationPoints--;cultivationTree[k]++;saveSilent();showCultivation();toast('수련 트리 강화: '+k)})}
function showInnerArts(){let h='<p>현재 심법: <b>'+INNER_ARTS[innerArt].name+'</b> · 심법 변경은 무당파 수련장에서만 가능합니다.</p>';for(const [k,v] of Object.entries(INNER_ARTS))h+='<div class="factionLine"><b>'+v.name+(innerArt===k?' ✓':'')+'</b><p>'+v.desc+'</p><button class="chooseInner" data-inner="'+k+'" '+(innerArt===k||zone!=='수련장'?'disabled':'')+'>심법 선택</button></div>';modal('내공 심법 선택',h);document.querySelectorAll('.chooseInner').forEach(b=>b.onclick=()=>{if(zone!=='수련장')return;innerArt=b.dataset.inner;saveSilent();showInnerArts();toast(INNER_ARTS[innerArt].name+' 운용 시작')})}
function showBreakthrough(){const target=(breakthroughs+1)*5;const amount=20+breakthroughs*20;const pieces=2+breakthroughs;let h='<p>현재 '+player.level+'경지 · 돌파 '+breakthroughs+'회</p><p>다음 돌파 조건: '+target+'경지 이상, 공헌도 '+amount+', 비급 조각 '+pieces+'개</p><p>돌파에 성공하면 최대 기혈 +30, 최대 내공 +20, 모든 무공 피해 +4.5%가 영구 적용됩니다.</p><p>보유 공헌도 '+contribution+' · 비급 조각 '+manuals+'</p><button class="btn" id="doBreakthrough">경지 돌파 시도</button>';modal('경지 돌파 · 폐관수련',h);$('doBreakthrough').onclick=()=>{if(zone!=='수련장'){toast('돌파는 무당파 수련장에서만 가능합니다');return}if(player.level<target||contribution<amount||manuals<pieces){toast('경지·공헌도·비급 조각이 부족합니다');return}contribution-=amount;manuals-=pieces;breakthroughs++;player.maxhp+=30;player.maxmp+=20;player.hp=player.maxhp;player.mp=player.maxmp;burst(player.x,player.y-65,'#f8d68e',55);saveSilent();showBreakthrough();toast('경지 돌파 성공! 기혈과 내공 상승')}}
function showSkills(){const cost=40*skillLevel;let html='<p>초식 숙련 '+mastery+' · 연계기 J→J→J (15), J→J→K (40)</p><p>장착한 무공은 검격(J)과 검기(K)의 공격 거리, 피해량, 내공 소모에 반영됩니다.</p><p>기본 태극검법 '+skillLevel+'성 · 비전 '+secretLevel+'성 · 다음 수련비 '+cost+'냥</p>';
 for(const slot of ['J','K']){html+='<div class="factionLine"><b>'+slot+' 키 장착: '+MARTIAL_ARTS[equippedArts[slot]].name+'</b><div class="factionBtns">';for(const id of learnedArts){if((slot==='J'&&MARTIAL_ARTS[id].mp>0)||(slot==='K'&&MARTIAL_ARTS[id].mp===0))continue;html+='<button class="equipArt" data-slot="'+slot+'" data-art="'+id+'">'+MARTIAL_ARTS[id].name+(equippedArts[slot]===id?' ✓':'')+'</button>'}html+='</div></div>'}
 html+='<button class="btn" id="trainSkill">태극검법 수련 ('+cost+'냥)</button><button class="btn" id="gotoLibrary">장경각 무공 비급 열람 (B)</button><button class="btn" id="openComboEditor">연계 편집기 (C)</button>';modal('무공 수련 · 초식 장착',html);document.querySelectorAll('.equipArt').forEach(b=>b.onclick=()=>{equippedArts[b.dataset.slot]=b.dataset.art;saveSilent();showSkills();toast(MARTIAL_ARTS[b.dataset.art].name+' 장착 완료')});$('trainSkill').onclick=()=>{if(gold<cost){toast('은전이 부족합니다');return}gold-=cost;skillLevel++;saveSilent();showSkills();toast('태극검법 '+skillLevel+'성 도달!')};$('gotoLibrary').onclick=showMartialLibrary;$('openComboEditor').onclick=showComboEditor}
function showMartialLibrary(){if(zone!=='수련장'){toast('장경각은 무당파 본산에서 이용할 수 있습니다');return}const offers=[['cloud',2,25],['palm',3,40],['thunder',7,100]];let html='<p>비급 조각 '+manuals+'개 · 은전 '+gold+'냥<br>수련장과 흑풍산의 적을 제압하면 비급 조각을 획득할 수 있습니다.</p>';for(const [id,pieces,coins] of offers){const a=MARTIAL_ARTS[id],owned=learnedArts.includes(id);html+='<div class="factionLine"><b>'+a.name+'</b><p>'+a.description+'</p><button class="obtainArt" data-id="'+id+'" '+(owned?'disabled':'')+'>'+(owned?'습득 완료':`비급 ${pieces}개 · ${coins}냥으로 습득`)+'</button></div>'}modal('장경각 · 비급 수집',html);document.querySelectorAll('.obtainArt').forEach(b=>b.onclick=()=>{const [id,pieces,coins]=offers.find(x=>x[0]===b.dataset.id);if(learnedArts.includes(id))return;if(manuals<pieces||gold<coins){toast('비급 조각 또는 은전이 부족합니다');return}manuals-=pieces;gold-=coins;learnedArts.push(id);saveSilent();showMartialLibrary();toast(MARTIAL_ARTS[id].name+' 습득! U에서 장착하세요')})}
function usePotion(){if(potions<=0){toast('회복약이 없습니다');return}if(player.hp>=player.maxhp){toast('기혈이 이미 가득합니다');return}potions--;player.hp=Math.min(player.maxhp,player.hp+65);toast('회복약 사용 · 기혈 +65');updateUI()}
function sectOnly(){if(player.rank<5){toast('장문인 등극 후 문파 경영이 열립니다');return false}return true}
function sectButton(label,fun){const b=document.createElement('button');b.className='btn';b.textContent=label;b.onclick=fun;return b}
function showSect(){if(!sectOnly())return;modal('무당파 · 장문인 집무전','<p>문파 자금 <b>'+sectFunds+'</b>냥 · 명성 <b>'+sectFame+'</b> · 보급품 <b>'+sectSupplies+'</b><br>제자 '+disciples.length+'/20명 · 완수한 임무 '+sectMissions+'회</p><p>연무장 '+facilities.training+'급 · 장경각 '+facilities.library+'급 · 단약방 '+facilities.alchemy+'급</p><div id="sectActions"></div><p style="font-size:12px">천하제일문파 목표: 명성 500 · 제자 10명 · 시설 모두 3급</p>');const place=$('sectActions');place.append(sectButton('제자 모집 (자금 60)',()=>{if(disciples.length>=20||sectFunds<60){toast('자금 부족 또는 제자 정원이 가득 찼습니다');return}sectFunds-=60;const talent=1+Math.floor(Math.random()*5);const name=DISCIPLE_NAMES[disciples.length%DISCIPLE_NAMES.length]+(disciples.length>=DISCIPLE_NAMES.length?String(disciples.length+1):'');disciples.push({name,level:1,talent,xp:0});saveSilent();showSect()}));place.append(sectButton('제자 육성',showDisciples));place.append(sectButton('시설 증축',showFacilities));place.append(sectButton('문파 임무',showMissions));place.append(sectButton('무림 외교 · 세력전 (F)',showDiplomacy));place.append(sectButton('천하제일문파 평가',showSectGoal));}
function showDisciples(){if(!sectOnly())return;const list=disciples.map((d,i)=>'<div class="itemLine">'+d.name+' | '+d.level+'급 · 자질 '+('★'.repeat(d.talent))+' <button class="trainDisc" data-i="'+i+'">수련 (보급품 2)</button></div>').join('')||'<p>제자가 없습니다. 먼저 모집하십시오.</p>';modal('문파 제자 관리','<p>보급품 '+sectSupplies+' · 연무장 '+facilities.training+'급 (훈련 효과 증가)</p>'+list);document.querySelectorAll('.trainDisc').forEach(b=>b.onclick=()=>{const d=disciples[Number(b.dataset.i)];if(!d||sectSupplies<2){toast('보급품이 부족합니다');return}sectSupplies-=2;d.xp+=facilities.training*2+d.talent;if(d.xp>=d.level*4){d.xp-=d.level*4;d.level++}saveSilent();showDisciples()})}
function showFacilities(){if(!sectOnly())return;let str='<p>문파 자금 '+sectFunds+'냥 · 시설은 최고 8급</p>';for(const [k,n] of [['training','연무장'],['library','장경각'],['alchemy','단약방']])str+='<div class="itemLine">'+n+' '+facilities[k]+'급 <button class="build" data-id="'+k+'">증축 ('+(facilities[k]*95)+'냥)</button></div>';modal('문파 시설 확장',str);document.querySelectorAll('.build').forEach(b=>b.onclick=()=>{const k=b.dataset.id,cost=facilities[k]*95;if(facilities[k]>=8||sectFunds<cost){toast('자금이 부족하거나 최고 등급입니다');return}sectFunds-=cost;facilities[k]++;sectFame+=5;saveSilent();showFacilities()})}
function showMissions(){if(!sectOnly())return;const power=disciples.reduce((n,d)=>n+d.level*(1+d.talent*.2),0);modal('무당파 파견 임무','<p>제자 전투력 '+Math.floor(power)+' · 보급품 '+sectSupplies+'</p><p>① 산문 순찰: 제자 1명, 보급품 1 → 자금 45 · 명성 8<br>② 산적 소탕: 제자 3명, 합계 전투력 12, 보급품 3 → 자금 110 · 명성 24<br>③ 강호 구휼: 제자 5명, 장경각 2급, 보급품 4 → 명성 50 · 자금 80</p><div id="missionBtns"></div>');[['산문 순찰',1,0,1,45,8,1],['산적 소탕',3,12,3,110,24,1],['강호 구휼',5,0,4,80,50,2]].forEach(([name,num,req,cost,money,fame,lib])=>$('missionBtns').append(sectButton(name,()=>{if(disciples.length<num||power<req||sectSupplies<cost||facilities.library<lib){toast('제자·전투력·보급품 또는 장경각 조건이 부족합니다');return}sectSupplies-=cost;sectFunds+=money;sectFame+=fame;sectMissions++;disciples.slice(0,num).forEach(d=>{d.xp+=1;if(d.xp>=d.level*4){d.xp=0;d.level++}});saveSilent();showMissions()})));$('missionBtns').append(sectButton('보급품 조달 (자금 30 → 보급품 5)',()=>{if(sectFunds<30){toast('문파 자금이 부족합니다');return}sectFunds-=30;sectSupplies+=5+Math.floor((facilities.alchemy-1)/2);saveSilent();showMissions()}))}
function showSectGoal(){if(!sectOnly())return;const ok=sectFame>=500&&disciples.length>=10&&Object.values(facilities).every(x=>x>=3);modal(ok?'천하제일문파 달성!':'천하제일문파 목표',ok?'<p>무당파의 이름이 무림 전역에 울려 퍼집니다.<br>장문인의 업적이 완성되었습니다!</p>':'<p>명성 '+sectFame+'/500<br>제자 '+disciples.length+'/10<br>연무장 '+facilities.training+'/3 · 장경각 '+facilities.library+'/3 · 단약방 '+facilities.alchemy+'/3</p>')}

const FACTION_META={
 '소림파':{desc:'중립과 계율을 중시하는 고승의 문파',trait:'불문 방어술',color:'#dbbd87'},
 '화산파':{desc:'날카로운 검법을 자랑하는 검수들의 문파',trait:'화산매화검',color:'#d6a3b5'},
 '아미파':{desc:'검법과 의술로 이름난 여성 고수들의 문파',trait:'아미검법',color:'#a7d4cb'}
};
function factionStatus(v){return v>=50?'동맹':v>=20?'우호':v<=-35?'적대':v<0?'경계':'중립'}
function factionAction(f,action){if(!sectOnly())return;const rel=factionRelations[f];if(action==='gift'){
 if(sectFunds<55){toast('외교 선물에 필요한 문파 자금 55냥이 부족합니다');return}
 sectFunds-=55;factionRelations[f]=Math.min(100,rel+18);sectFame+=3;toast(f+' 사절단에 선물을 전했습니다 · 관계 +18');
 }else if(action==='treaty'){
 if(rel<50){toast('동맹 협약에는 관계도 50 이상이 필요합니다');return}
 if(sectFunds<80){toast('협약 체결에 필요한 자금 80냥이 부족합니다');return}
 sectFunds-=80;sectFame+=25;sectSupplies+=8;factionRelations[f]=Math.min(100,rel+5);toast(f+'와 협약 체결! 명성 +25 · 보급 +8');
 }else if(action==='war'){
 if(disciples.length<5){toast('세력전에는 제자 5명 이상이 필요합니다');return}
 if(sectSupplies<5){toast('세력전에는 보급품 5개가 필요합니다');return}
 if(rel>15){toast('관계도가 15 이하인 문파에만 도전할 수 있습니다');return}
 const power=disciples.reduce((v,d)=>v+d.level*(1+d.talent*.2),0)+facilities.training*3;
 const enemyPower=18+warWins*4;
 sectSupplies-=5;
 if(power>=enemyPower){warWins++;sectFunds+=140;sectFame+=45;factionRelations[f]=Math.max(-100,rel-18);toast('세력전 승리! 문파 자금 +140 · 명성 +45')}
 else{sectFunds=Math.max(0,sectFunds-35);factionRelations[f]=Math.max(-100,rel-8);toast('세력전 패배! 전투력 '+Math.floor(power)+' / 필요 '+enemyPower)}
 }saveSilent();showDiplomacy();}
function startArena(f){if(!sectOnly())return;if(zone!=='수련장'){toast('무림 대회는 수련장 본산에서만 신청 가능합니다');return}if(player.trial){toast('승급 시험 진행 중에는 참가할 수 없습니다');return}if(sectFunds<40){toast('참가비로 문파 자금 40냥이 필요합니다');return}if(factionRelations[f]<=-65){toast('관계가 너무 악화되어 대련이 거부되었습니다');return}
 sectFunds-=40;arenaFaction=f;player.trial=true;trialBoss=true;enemies=[];spawnEnemy(960,true);const e=enemies[0];e.kind=f+' 대표 검수';e.hp=e.maxhp=400+leagueWins*95;e.aggro=1100;e.attackCD=.5;resume();toast(f+' 대표 검수 등장! J/K로 대련하세요');saveSilent();}
function showDiplomacy(){if(!sectOnly())return;
 let t='<p>문파 자금 <b>'+sectFunds+'</b>냥 · 명성 <b>'+sectFame+'</b> · 보급 <b>'+sectSupplies+'</b><br>무림 대회 우승 '+leagueWins+'회 · 세력전 승리 '+warWins+'회</p><p>문파에 선물을 보내 관계도를 높이거나, 우호 동맹을 체결하세요. 세력전은 제자 전투력으로 결과가 결정됩니다.</p>';
 for(const f of Object.keys(FACTION_META)){const m=FACTION_META[f];t+='<div class="factionLine"><b>'+f+'</b> <span>관계도 '+factionRelations[f]+' · '+factionStatus(factionRelations[f])+'</span><div style="color:#bfc9c8;font-size:12px">'+m.desc+'</div><div class="factionBtns"><button data-f="'+f+'" data-a="gift">사절단 파견 (55냥)</button><button data-f="'+f+'" data-a="treaty">동맹 협약 (관계 50)</button><button data-f="'+f+'" data-a="arena">대표 대련 (40냥)</button><button data-f="'+f+'" data-a="war">세력전 (보급 5)</button></div></div>'}
 modal('무림 외교 · 정파 세력',t);
 document.querySelectorAll('.factionBtns button').forEach(b=>b.onclick=()=>{const f=b.dataset.f,a=b.dataset.a;if(a==='arena')startArena(f);else factionAction(f,a)})
}

function showBag(){const wc=70+(weapon*65),ac=55+(armor*50);modal('장비 · 가방','<p>은전 '+gold+'냥 · 회복약 '+potions+'개 · 약초 '+herbs+' · 철광석 '+ore+'</p><div class="itemLine">검: '+(weapon?'정련 '+weapon+'단계':'목검')+' <button id="upgradeW">강화 ('+wc+'냥/철광석 1)</button></div><div class="itemLine">도복: '+(armor?'정련 '+armor+'단계':'수련 도복')+' <button id="upgradeA">강화 ('+ac+'냥/철광석 1)</button></div><div class="itemLine">회복약: '+potions+'개 <button id="drink">사용 (기혈 +65)</button></div><div class="itemLine">상점 <button id="buy">회복약 구매 (20냥)</button></div>');$('upgradeW').onclick=()=>{if(gold<wc||ore<1){toast('은전 또는 철광석이 부족합니다');return}gold-=wc;ore--;weapon++;resume();toast('검 강화 성공! 공격력 상승');saveSilent()};$('upgradeA').onclick=()=>{if(gold<ac||ore<1){toast('은전 또는 철광석이 부족합니다');return}gold-=ac;ore--;armor++;resume();toast('도복 강화 성공! 받는 피해 감소');saveSilent()};$('drink').onclick=()=>{usePotion();showBag()};$('buy').onclick=()=>{if(zone!=='청운진'){toast('회복약은 청운진에서만 구매할 수 있습니다');return}if(gold<20){toast('은전이 부족합니다');return}gold-=20;potions++;resume();toast('회복약을 구매했습니다');saveSilent()}}
$('partyBtn').onclick=showCompanions;$('storyBtn').onclick=showStory;$('allianceBtn').onclick=showDiplomacy;$('mapBtn').onclick=showMap;$('questBtn').onclick=showQuest;$('skillBtn').onclick=showSkills;$('comboBtn').onclick=showComboEditor;$('treeBtn').onclick=showCultivation;$('innerBtn').onclick=showInnerArts;$('breakBtn').onclick=showBreakthrough;$('bagBtn').onclick=showBag;$('sectBtn').onclick=showSect;$('saveBtn').onclick=save;window.addEventListener('error',function(e){const el=document.getElementById('mobileStatus');if(el&&state==='menu')el.textContent='게임 초기화 오류: '+(e.message||'알 수 없는 오류')});
function safeStart(loadGame){try{start(loadGame);if(state!=='play'&&loadGame===false)throw new Error('게임 상태 전환 실패')}catch(err){console.error('게임 시작 오류',err);const el=$('mobileStatus');if(el)el.textContent='시작 중 오류: '+String(err&&err.message||err)+' · Safari 또는 Chrome에서 열어주세요.';}}
function bindStart(button,loadGame){let touched=0;button.addEventListener('touchend',function(e){e.preventDefault();touched=Date.now();safeStart(loadGame)},{passive:false});button.addEventListener('click',function(e){if(Date.now()-touched<650)return;safeStart(loadGame)});}
bindStart($('startBtn'),false);bindStart($('loadBtn'),true);$('libraryBtn').onclick=()=>{if(state==='play')showLibrary()};setInterval(()=>{if(state==='play')saveSilent()},20000);
$('exportBtn').onclick=()=>{try{const raw=safeGet(SAVE_KEY);if(!raw||!validateSave(JSON.parse(raw))){toast('유효한 저장 기록이 없습니다. P로 먼저 저장하세요');return}const blob=new Blob([raw],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='wudang-save-backup.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('백업 파일을 내보냈습니다')}catch(e){toast('백업 내보내기에 실패했습니다')}};
$('importBtn').onclick=()=>$('importFile').click();
$('importFile').addEventListener('change',async e=>{const file=e.target.files?.[0];if(!file)return;try{if(file.size>1024*1024)throw Error('too large');const raw=await file.text();if(!validateSave(JSON.parse(raw)))throw Error('invalid');const previous=safeGet(SAVE_KEY);if(previous)safeSet(BACKUP_KEY,previous);if(!safeSet(SAVE_KEY,raw))throw Error('write');toast('백업 복구 완료 · 새로고침 후 저장 불러오기를 선택하세요')}catch(err){toast('백업 형식이 잘못되었거나 저장할 수 없습니다')}finally{e.target.value=''}});
})();
