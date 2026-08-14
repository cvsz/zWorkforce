const $ = (id) => document.getElementById(id);
const state = { key: sessionStorage.getItem('zwf:key') || '', tenant: sessionStorage.getItem('zwf:tenant') || 'default', agents: [] };
$('apiKey').value = state.key; $('tenantId').value = state.tenant;
function esc(value){return String(value ?? '').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function fmt(value,d=2){const n=Number(value||0);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):'—';}
function age(iso){if(!iso)return '—';const s=Math.max(0,(Date.now()-Date.parse(iso))/1000);if(s<60)return `${Math.round(s)}s ago`;if(s<3600)return `${Math.round(s/60)}m ago`;if(s<86400)return `${Math.round(s/3600)}h ago`;return new Date(iso).toLocaleDateString();}
function banner(message=''){const el=$('errorBanner');el.textContent=message;el.classList.toggle('hidden',!message);}
async function api(path, options={}){const headers={'Accept':'application/json',...(options.headers||{})};if(state.key)headers['Authorization']=`Bearer ${state.key}`;if(state.tenant)headers['X-Tenant-ID']=state.tenant;if(options.body && typeof options.body!=='string'){headers['Content-Type']='application/json';options.body=JSON.stringify(options.body);}const res=await fetch(path,{...options,headers});const text=await res.text();let data={};try{data=text?JSON.parse(text):{};}catch{data={error:{message:text||res.statusText}};}if(!res.ok)throw new Error(data?.error?.message||`HTTP ${res.status}`);return data;}
async function health(){try{await api('/health');$('healthDot').className='dot ok';$('healthText').textContent='Runtime healthy';}catch{$('healthDot').className='dot bad';$('healthText').textContent='Runtime unavailable';}}
async function refresh(){banner('');await health();if(!state.key){await refreshZarvisVoiceHealth();return;}try{const [o,a,t,p,r,m]=await Promise.all([api('/api/v1/overview'),api('/api/v1/agents'),api('/api/v1/tasks?limit=50'),api('/api/v1/providers'),api('/api/v1/recommendations'),api('/api/v1/memories?limit=10')]);state.agents=a.items||[];renderOverview(o);renderAgents(state.agents);renderTasks(t.items||[]);renderProviders(p.items||[],o.provider_mix||[]);renderMix(o.model_mix||[]);renderRecommendations(r.items||[]);renderMemories(m.items||[]);populateAgents();}catch(err){banner(err.message);}await refreshZarvisVoiceHealth();}
function renderOverview(o){$('mActive').textContent=fmt(o.active_tasks,0);$('mTasks').textContent=fmt(o.tasks_24h,0);$('mSuccess').textContent=`${fmt(o.success_rate)}% runtime success`;$('mOutcome').textContent=`${fmt(o.outcome_pass_rate)}%`;$('mCredits').textContent=fmt(o.credits_24h,4);$('mCostSuccess').textContent=`${fmt(o.cost_per_success,4)} / successful outcome`;$('mP95').textContent=`${fmt(o.p95_duration_seconds,1)}s`;$('mQueue').textContent=`${fmt(o.avg_queue_seconds,1)}s avg queue`;$('mDead').textContent=fmt(o.dead_letter_tasks,0);}
function populateAgents(){const select=$('agentSelect');const current=select.value;select.innerHTML=state.agents.filter(a=>a.enabled).map(a=>`<option value="${esc(a.id)}">${esc(a.name)} · ${esc(a.department)}</option>`).join('');if([...select.options].some(o=>o.value===current))select.value=current;}
function renderAgents(items){$('agentCards').innerHTML=items.map(a=>`<div class="agent"><h3>${esc(a.name)}</h3><p>${esc(a.description)}</p><div class="agent-meta"><span>${esc(a.department)}</span><span>${esc(a.default_tier)}</span><span>${esc(a.max_iterations)} turns</span><span>${esc((a.allowed_tools||[]).length)} tools</span><span>${esc(a.required_approvals)} approvals</span></div></div>`).join('')||'<p>No agents.</p>';}
function renderTasks(items){$('taskCount').textContent=items.length;$('taskRows').innerHTML=items.map(t=>{let actions='';if(t.status==='waiting_approval')actions=`<button data-action="approve" data-id="${esc(t.id)}">Approve</button><button class="ghost" data-action="reject" data-id="${esc(t.id)}">Reject</button>`;else if(['queued','running'].includes(t.status))actions=`<button class="ghost" data-action="cancel" data-id="${esc(t.id)}">Cancel</button>`;else if(['failed','dead_letter'].includes(t.status))actions=`<button data-action="retry" data-id="${esc(t.id)}">Retry</button>`;return `<tr><td><span class="status ${esc(t.status)}">${esc(t.status)}</span></td><td>${esc(t.agent_id)}</td><td>${esc(t.tier)}<br><small>${esc(t.provider_name||'—')} / ${esc(t.model||'—')}</small></td><td>${fmt(t.cost_credits,5)}</td><td>${esc(t.outcome_status||'—')} ${t.outcome_score!=null?`(${fmt(t.outcome_score,2)})`:''}</td><td>${age(t.created_at)}</td><td><div class="actions">${actions}</div></td></tr>`;}).join('')||'<tr><td colspan="7">No tasks yet.</td></tr>';document.querySelectorAll('[data-action]').forEach(btn=>btn.addEventListener('click',()=>taskAction(btn.dataset.id,btn.dataset.action)));}
function renderMix(items){const total=items.reduce((s,x)=>s+Number(x.cost||0),0)||items.reduce((s,x)=>s+Number(x.turns||0),0)||1;$('mixList').innerHTML=items.map(x=>{const v=Number(x.cost||0)||Number(x.turns||0);const pct=Math.max(2,Math.round(v/total*100));return `<div class="bar-row"><strong>${esc(x.tier)}</strong><progress class="bar-progress" max="100" value="${pct}">${pct}%</progress><span>${fmt(x.cost,4)} cr</span></div>`;}).join('')||'<p>No usage yet.</p>';}
function renderProviders(items,mix){const turns=Object.fromEntries(mix.map(x=>[x.provider_name,x.turns]));$('providerHealth').innerHTML=items.map(p=>`<div class="provider"><div><strong>${esc(p.name)}</strong><small> · ${esc(p.kind)}</small></div><span class="status ${p.available?'succeeded':'failed'}">${p.available?'healthy':'circuit open'}</span></div>`).join('');$('providerList').innerHTML=items.map(p=>`<div class="provider"><div><strong>${esc(p.name)}</strong><small> priority ${esc(p.priority)}</small></div><span>${fmt(turns[p.name]||0,0)} turns</span></div>`).join('')||'<p>No provider data.</p>';}
function renderRecommendations(items){$('recommendations').innerHTML=items.map(r=>`<div class="rec"><strong>${esc(r.agent_id)} · ${esc(r.action)}</strong><p>${esc(r.from)} → ${esc(r.to)} · confidence ${esc(r.confidence)} · ${esc(JSON.stringify(r.evidence))}</p></div>`).join('')||'<div class="rec"><strong>No rightsizing signal yet</strong><p>Recommendations appear after enough evaluated task history exists.</p></div>';}
function renderMemories(items){$('memoryList').innerHTML=items.map(m=>`<div class="memory"><strong>${esc(m.title)}</strong><p>${esc((m.content||'').slice(0,220))}</p></div>`).join('')||'<p>No matching memory.</p>';}
async function taskAction(id,action){try{await api(`/api/v1/tasks/${id}/${action}`,{method:'POST',body:{comment:`Dashboard ${action}`}});await refresh();}catch(err){banner(err.message);}}
$('connectBtn').addEventListener('click',()=>{void stopZarvisVoiceTransport();state.key=$('apiKey').value.trim();state.tenant=$('tenantId').value.trim()||'default';sessionStorage.setItem('zwf:key',state.key);sessionStorage.setItem('zwf:tenant',state.tenant);refresh();});
$('refreshBtn').addEventListener('click',refresh);
$('prometaInstallBtn').addEventListener('click',async()=>{try{const btn=$('prometaInstallBtn');btn.disabled=true;$('prometaStatus').textContent='Installing ProMeta baseline...';const data=await api('/api/v1/prometa/install',{method:'POST',body:{}});$('prometaStatus').textContent=`Installed ${data.agents} agents, ${data.skills} skills, ${data.agent_templates} templates and ${data.workflows} workflows.`;await refresh();}catch(err){banner(err.message);$('prometaStatus').textContent='ProMeta install failed.';}finally{$('prometaInstallBtn').disabled=false;}});
$('dispatchForm').addEventListener('submit',async(e)=>{e.preventDefault();try{const body={agent_id:$('agentSelect').value,prompt:$('prompt').value,mutating:$('mutating').checked,priority:Number($('priority').value||0)};if($('tierSelect').value)body.tier_override=$('tierSelect').value;await api('/api/v1/tasks',{method:'POST',headers:{'Idempotency-Key':crypto.randomUUID()},body});$('prompt').value='';await refresh();}catch(err){banner(err.message);}});
$('memoryForm').addEventListener('submit',async(e)=>{e.preventDefault();try{const q=encodeURIComponent($('memoryQuery').value.trim());const data=await api(`/api/v1/memories?limit=20${q?`&q=${q}`:''}`);renderMemories(data.items||[]);}catch(err){banner(err.message);}});

// Z.A.R.V.I.S. realtime voice -------------------------------------------------
const ZARVIS_SAMPLE_RATE = 16000;
const ZARVIS_SILENCE_FRAMES = 6;
let zarvisAvailable = false;
let zarvisSocket = null;
let zarvisSessionConfigured = false;
let zarvisAudioContext = null;
let zarvisMediaStream = null;
let zarvisCaptureNode = null;
let zarvisMediaSource = null;
let zarvisPttActive = false;
let zarvisPttGeneration = 0;
let zarvisTransportPromise = null;
let zarvisPlayhead = 0;
let zarvisActiveSources = new Set();
let zarvisTranscriptBuffer = '';
let zarvisReplyBuffer = '';

function setZarvisState(next, message){
  const card=$('zarvisCard');
  card.dataset.voiceState=next;
  $('zarvisState').textContent=message;
  const pressed=zarvisPttActive;
  $('zarvisPtt').setAttribute('aria-pressed',pressed?'true':'false');
  $('zarvisPttLabel').textContent=pressed?'Release to send':'Hold to talk';
  $('zarvisApproval').classList.toggle('hidden',next!=='approval_required');
}

function setZarvisLevel(level){
  $('zarvisCard').style.setProperty('--zarvis-level',String(Math.max(0,Math.min(1,level||0))));
}

function bytesToBase64(bytes){let binary='';const chunkSize=0x8000;for(let i=0;i<bytes.length;i+=chunkSize)binary+=String.fromCharCode(...bytes.subarray(i,i+chunkSize));return btoa(binary);}
function base64ToBytes(value){const binary=atob(value);const bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i+=1)bytes[i]=binary.charCodeAt(i);return bytes;}
function resampleToPcm16(input,inputRate,outputRate){if(!input.length)return new Uint8Array();const ratio=inputRate/outputRate;const outputLength=Math.max(1,Math.floor(input.length/ratio));const output=new ArrayBuffer(outputLength*2);const view=new DataView(output);for(let i=0;i<outputLength;i+=1){const position=i*ratio;const left=Math.floor(position);const right=Math.min(input.length-1,left+1);const fraction=position-left;const sample=input[left]*(1-fraction)+input[right]*fraction;const clamped=Math.max(-1,Math.min(1,sample));view.setInt16(i*2,clamped<0?clamped*0x8000:clamped*0x7fff,true);}return new Uint8Array(output);}
function pcm16ToFloat32(bytes){const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);const samples=new Float32Array(Math.floor(bytes.byteLength/2));for(let i=0;i<samples.length;i+=1){const value=view.getInt16(i*2,true);samples[i]=value<0?value/0x8000:value/0x7fff;}return samples;}
function rms(samples){if(!samples.length)return 0;let total=0;for(const value of samples)total+=value*value;return Math.min(1,Math.sqrt(total/samples.length)*4);}

function stopZarvisPlayback(){
  for(const source of zarvisActiveSources){try{source.stop();}catch{}}
  zarvisActiveSources=new Set();
  zarvisPlayhead=zarvisAudioContext?.currentTime||0;
}

async function queueZarvisAudio(base64Audio){
  if(!zarvisAudioContext||!base64Audio)return;
  if(zarvisAudioContext.state==='suspended')await zarvisAudioContext.resume();
  const samples=pcm16ToFloat32(base64ToBytes(base64Audio));
  if(!samples.length)return;
  const buffer=zarvisAudioContext.createBuffer(1,samples.length,ZARVIS_SAMPLE_RATE);
  buffer.copyToChannel(samples,0);
  const source=zarvisAudioContext.createBufferSource();
  source.buffer=buffer;source.connect(zarvisAudioContext.destination);
  const startAt=Math.max(zarvisAudioContext.currentTime+.02,zarvisPlayhead);
  source.start(startAt);zarvisPlayhead=startAt+buffer.duration;zarvisActiveSources.add(source);
  source.addEventListener('ended',()=>zarvisActiveSources.delete(source),{once:true});
}

function sendZarvisEvent(payload){if(zarvisSocket?.readyState===WebSocket.OPEN)zarvisSocket.send(JSON.stringify(payload));}
function cancelZarvisResponse(){sendZarvisEvent({type:'response.cancel'});stopZarvisPlayback();if(['speaking','thinking'].includes($('zarvisCard').dataset.voiceState))setZarvisState('ready','Response interrupted — hold to talk');}

function sendZarvisSilenceBurst(){
  if(zarvisSocket?.readyState!==WebSocket.OPEN||!zarvisSessionConfigured)return;
  const silence=bytesToBase64(new Uint8Array(2048*2));
  for(let i=0;i<ZARVIS_SILENCE_FRAMES;i+=1)sendZarvisEvent({type:'input_audio_buffer.append',audio:silence});
}

function handleZarvisRealtimeEvent(event){
  let payload;try{payload=JSON.parse(event.data);}catch{return;}
  switch(payload.type){
    case 'session.created':
      sendZarvisEvent({type:'session.update',session:{type:'realtime',instructions:'You are Z.A.R.V.I.S., a concise and helpful AI workforce voice assistant. Reply in the user language. Never claim that spoken text approves a mutating action.'}});
      zarvisSessionConfigured=true;
      if(!zarvisPttActive)setZarvisState('ready','Voice ready — hold to talk');
      break;
    case 'input_audio_buffer.speech_started':
      zarvisTranscriptBuffer='';zarvisReplyBuffer='';stopZarvisPlayback();setZarvisState('listening','Listening…');break;
    case 'input_audio_buffer.speech_stopped':
      setZarvisState('transcribing','Transcribing…');break;
    case 'conversation.item.input_audio_transcription.delta':
      if(payload.delta){zarvisTranscriptBuffer+=payload.delta;$('zarvisTranscript').textContent=zarvisTranscriptBuffer;}break;
    case 'conversation.item.input_audio_transcription.completed':
      zarvisTranscriptBuffer=payload.transcript||payload.text||zarvisTranscriptBuffer;$('zarvisTranscript').textContent=zarvisTranscriptBuffer||'—';setZarvisState('thinking','Z.A.R.V.I.S. is thinking…');break;
    case 'response.audio.delta':
    case 'response.output_audio.delta':
      setZarvisState('speaking','Z.A.R.V.I.S. is speaking…');$('zarvisCancel').disabled=false;void queueZarvisAudio(payload.delta);break;
    case 'response.audio_transcript.delta':
    case 'response.output_audio_transcript.delta':
      if(payload.delta){zarvisReplyBuffer+=payload.delta;$('zarvisReply').textContent=zarvisReplyBuffer;}break;
    case 'response.audio_transcript.done':
    case 'response.output_audio_transcript.done':
      zarvisReplyBuffer=payload.transcript||payload.text||zarvisReplyBuffer;$('zarvisReply').textContent=zarvisReplyBuffer||$('zarvisReply').textContent;break;
    case 'approval.required':
    case 'zarvis.approval_required':
      setZarvisState('approval_required','Approval required — review in the task panel');break;
    case 'response.done':
      $('zarvisCancel').disabled=true;if(!zarvisPttActive)setZarvisState('ready','Voice ready — hold to talk');break;
    case 'error':
      setZarvisState('error',payload.error?.message||'Voice session error');break;
    default:break;
  }
}

async function ensureZarvisAudioContext(){
  if(zarvisAudioContext&&zarvisAudioContext.state!=='closed')return;
  const AudioContextCtor=globalThis.AudioContext||globalThis.webkitAudioContext;
  if(!AudioContextCtor)throw new Error('Web Audio is not supported in this browser');
  zarvisAudioContext=new AudioContextCtor({latencyHint:'interactive'});
  await zarvisAudioContext.audioWorklet.addModule('/zarvis-voice-worklet.js');
}

async function ensureZarvisTransport(){
  if(zarvisSocket?.readyState===WebSocket.OPEN)return;
  if(zarvisTransportPromise)return zarvisTransportPromise;
  zarvisTransportPromise=(async()=>{
    setZarvisState('arming','Requesting secure voice ticket…');
    await ensureZarvisAudioContext();
    const session=await api('/api/v1/zarvis/voice/session',{method:'POST',body:{}});
    $('zarvisRuntime').textContent=session.model||'voice';
    await new Promise((resolve,reject)=>{
      const socket=new WebSocket(session.websocket_url,[`zticket.${session.ticket}`]);
      zarvisSocket=socket;zarvisSessionConfigured=false;
      let settled=false;
      const fail=()=>{if(!settled){settled=true;reject(new Error('Unable to connect to the voice gateway'));}};
      socket.addEventListener('open',()=>{if(!settled){settled=true;resolve();}},{once:true});
      socket.addEventListener('error',fail,{once:true});
      socket.addEventListener('message',handleZarvisRealtimeEvent);
      socket.addEventListener('close',()=>{zarvisSessionConfigured=false;stopZarvisPlayback();void stopZarvisMicrophone();zarvisSocket=null;if(zarvisAvailable)setZarvisState('disconnected','Voice disconnected — hold to reconnect');},{once:true});
    });
  })();
  try{await zarvisTransportPromise;}finally{zarvisTransportPromise=null;}
}

async function startZarvisMicrophone(){
  if(zarvisMediaStream)return;
  if(!navigator.mediaDevices?.getUserMedia)throw new Error('Microphone capture is not supported in this browser');
  await ensureZarvisAudioContext();
  if(zarvisAudioContext.state==='suspended')await zarvisAudioContext.resume();
  const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1}});
  zarvisMediaStream=stream;
  zarvisMediaSource=zarvisAudioContext.createMediaStreamSource(stream);
  zarvisCaptureNode=new AudioWorkletNode(zarvisAudioContext,'zworkforce-voice-capture');
  zarvisCaptureNode.port.onmessage=({data})=>{
    if(!zarvisPttActive||!zarvisSessionConfigured||zarvisSocket?.readyState!==WebSocket.OPEN)return;
    setZarvisLevel(rms(data));
    const bytes=resampleToPcm16(data,zarvisAudioContext.sampleRate,ZARVIS_SAMPLE_RATE);
    if(bytes.length)sendZarvisEvent({type:'input_audio_buffer.append',audio:bytesToBase64(bytes)});
  };
  zarvisMediaSource.connect(zarvisCaptureNode);
  const silent=zarvisAudioContext.createGain();silent.gain.value=0;zarvisCaptureNode.connect(silent).connect(zarvisAudioContext.destination);
}

async function stopZarvisMicrophone(){
  setZarvisLevel(0);
  try{zarvisCaptureNode?.disconnect();}catch{}
  try{zarvisMediaSource?.disconnect();}catch{}
  zarvisCaptureNode=null;zarvisMediaSource=null;
  for(const track of zarvisMediaStream?.getTracks()||[])track.stop();
  zarvisMediaStream=null;
}

async function beginZarvisPtt(){
  if(zarvisPttActive||!zarvisAvailable||!state.key)return;
  const generation=++zarvisPttGeneration;
  zarvisPttActive=true;$('zarvisPtt').setAttribute('aria-pressed','true');$('zarvisPttLabel').textContent='Release to send';
  try{
    await ensureZarvisTransport();
    if(!zarvisPttActive||generation!==zarvisPttGeneration)return;
    cancelZarvisResponse();
    await startZarvisMicrophone();
    if(!zarvisPttActive||generation!==zarvisPttGeneration){await stopZarvisMicrophone();return;}
    setZarvisState('listening','Listening… release to send');
  }catch(error){if(generation!==zarvisPttGeneration)return;zarvisPttActive=false;zarvisPttGeneration+=1;await stopZarvisMicrophone();setZarvisState('error',error instanceof Error?error.message:'Unable to start voice');$('zarvisPtt').setAttribute('aria-pressed','false');$('zarvisPttLabel').textContent='Hold to talk';}
}

async function endZarvisPtt(){
  if(!zarvisPttActive)return;
  zarvisPttActive=false;zarvisPttGeneration+=1;$('zarvisPtt').setAttribute('aria-pressed','false');$('zarvisPttLabel').textContent='Hold to talk';
  sendZarvisSilenceBurst();
  await stopZarvisMicrophone();
  if(zarvisSessionConfigured)setZarvisState('transcribing','Transcribing…');
  else setZarvisState('ready','Voice ready — hold to talk');
}

async function stopZarvisVoiceTransport(){
  zarvisPttActive=false;zarvisPttGeneration+=1;zarvisSessionConfigured=false;zarvisTransportPromise=null;
  await stopZarvisMicrophone();stopZarvisPlayback();
  if(zarvisSocket&&zarvisSocket.readyState<WebSocket.CLOSING)zarvisSocket.close(1000,'dashboard_stop');
  zarvisSocket=null;
  if(zarvisAudioContext&&zarvisAudioContext.state!=='closed')await zarvisAudioContext.close();
  zarvisAudioContext=null;zarvisPlayhead=0;
}

async function refreshZarvisVoiceHealth(){
  const ptt=$('zarvisPtt');
  if(!state.key){zarvisAvailable=false;ptt.disabled=true;$('zarvisRuntime').textContent='offline';setZarvisState('idle','Connect to enable voice');return;}
  try{
    const voice=await api('/api/v1/zarvis/voice');
    zarvisAvailable=Boolean(voice.enabled&&voice.configured);
    ptt.disabled=!zarvisAvailable;
    $('zarvisRuntime').textContent=voice.model||'offline';
    if(zarvisAvailable&&zarvisSocket?.readyState!==WebSocket.OPEN)setZarvisState('ready','Voice available — hold to talk');
    else if(!zarvisAvailable)setZarvisState('idle','Voice is disabled or not configured');
  }catch(error){zarvisAvailable=false;ptt.disabled=true;$('zarvisRuntime').textContent='unavailable';setZarvisState('error',error instanceof Error?error.message:'Voice unavailable');}
}

function zarvisEditableTarget(target){return target instanceof Element&&Boolean(target.closest('input,textarea,select,button,a,[contenteditable="true"]'));}
const zarvisPtt=$('zarvisPtt');
zarvisPtt.addEventListener('pointerdown',event=>{if(zarvisPtt.disabled)return;event.preventDefault();try{zarvisPtt.setPointerCapture(event.pointerId);}catch{}void beginZarvisPtt();});
zarvisPtt.addEventListener('pointerup',event=>{event.preventDefault();void endZarvisPtt();});
zarvisPtt.addEventListener('pointercancel',()=>void endZarvisPtt());
zarvisPtt.addEventListener('click',event=>{if(event.detail!==0||zarvisPtt.disabled)return;if(zarvisPttActive)void endZarvisPtt();else void beginZarvisPtt();});
$('zarvisCancel').addEventListener('click',cancelZarvisResponse);
window.addEventListener('keydown',event=>{if(event.code==='Escape'){cancelZarvisResponse();return;}if(event.code==='Space'&&!event.repeat&&!zarvisEditableTarget(event.target)){event.preventDefault();void beginZarvisPtt();}});
window.addEventListener('keyup',event=>{if(event.code==='Space'&&!zarvisEditableTarget(event.target)){event.preventDefault();void endZarvisPtt();}});
window.addEventListener('beforeunload',()=>{void stopZarvisVoiceTransport();});

health();if(state.key)refresh();else void refreshZarvisVoiceHealth();
