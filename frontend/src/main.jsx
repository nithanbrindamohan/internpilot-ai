import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Search, RefreshCw, BriefcaseBusiness, FileText, ExternalLink, Sparkles, LogOut, UserRound, Upload, ShieldCheck} from 'lucide-react';
import './style.css';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const TOKEN_KEY = 'internpilot_session';

function App() {
  const [token,setToken] = useState(localStorage.getItem(TOKEN_KEY) || '');
  const [user,setUser] = useState(null);
  const [mode,setMode] = useState('login');
  const [auth,setAuth] = useState({full_name:'',email:'',password:'',invite_code:'',program:'',graduation_year:''});
  const [profile,setProfile] = useState({full_name:'',university:'',program:'',graduation_year:'',location:'Toronto, Ontario',work_authorization:'',skills:[]});
  const [skillsText,setSkillsText] = useState('');
  const [resume,setResume] = useState(null);
  const [jobs,setJobs] = useState([]), [apps,setApps] = useState([]);
  const [sourceStatus,setSourceStatus] = useState(null);
  const [query,setQuery] = useState(''), [minScore,setMinScore] = useState(0);
  const [region,setRegion] = useState('gta'), [discipline,setDiscipline] = useState('all');
  const [workMode,setWorkMode] = useState('all'), [term,setTerm] = useState('all');
  const [city,setCity] = useState('all');
  const [loading,setLoading] = useState(false), [notice,setNotice] = useState('');
  const [selected,setSelected] = useState(null), [letter,setLetter] = useState('');
  const [busy,setBusy] = useState(false), [aiResult,setAiResult] = useState(null);
  const [bulkJobs,setBulkJobs] = useState([]);
  const [bulkApps,setBulkApps] = useState([]);
  const [handoffs,setHandoffs] = useState([]);
  const [confirmReviewed,setConfirmReviewed] = useState(false);
  const [reviewPacket,setReviewPacket] = useState(null);
  const [reviewAnswers,setReviewAnswers] = useState({});
  const [reviewLetter,setReviewLetter] = useState('');
  const headers = (extra={}) => ({...extra, ...(token ? {Authorization:`Bearer ${token}`} : {})});

  async function request(path, options={}) {
    const response = await fetch(`${API}${path}`, {...options, headers:headers(options.headers || {})});
    const data = await response.json().catch(()=>({detail:'The server returned an unreadable response.'}));
    if (response.status === 401) { logout(); throw new Error(data.detail || 'Please sign in again.'); }
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status}).`);
    return data;
  }
  function logout() {
    localStorage.removeItem(TOKEN_KEY); setToken(''); setUser(null); setJobs([]); setApps([]); setBulkJobs([]); setBulkApps([]); setHandoffs([]);
    setNotice('You have been signed out.');
  }
  async function loadDashboard() {
    const [j,a,p,s] = await Promise.all([
      request(`/api/jobs?${new URLSearchParams({q:query,min_score:String(minScore),region,discipline,work_mode:workMode,term,city}).toString()}`),
      request('/api/applications'), request('/api/profile'), request('/api/discover/status')
    ]);
    setJobs(j); setApps(a); setUser(p); setSourceStatus(s);
    setProfile(p); setSkillsText((p.skills || []).join(', '));
  }
  useEffect(()=>{ if(token) loadDashboard().catch(e=>setNotice(e.message)); },[token,query,minScore,region,discipline,workMode,term,city]);

  async function submitAuth(e) {
    e.preventDefault(); setBusy(true); setNotice('');
    try {
      const path = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
      const payload = mode === 'register' ? auth : {email:auth.email,password:auth.password};
      const data = await request(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      localStorage.setItem(TOKEN_KEY,data.access_token); setToken(data.access_token); setUser(data.user);
      setNotice('Welcome to InternPilot AI.');
    } catch(e) {setNotice(e.message);}
    finally {setBusy(false);}
  }
  async function saveProfile(e) {
    e.preventDefault(); setBusy(true);
    try {
      const data = await request('/api/profile',{method:'PUT',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({...profile,skills:skillsText.split(',').map(x=>x.trim()).filter(Boolean)})});
      setUser(data); setProfile(data); setSkillsText(data.skills.join(', ')); setNotice('Your profile was saved.');
    } catch(e) {setNotice(e.message);}
    finally {setBusy(false);}
  }
  async function uploadResume(e) {
    e.preventDefault(); if(!resume) return setNotice('Choose a resume file first.');
    const form = new FormData(); form.append('file',resume); setBusy(true);
    try { const d=await request('/api/profile/resume',{method:'POST',body:form}); setNotice(`${d.message} (${d.characters} characters extracted)`); setResume(null); await loadDashboard(); }
    catch(e){setNotice(e.message);} finally{setBusy(false);}
  }
  async function discover() {
    setLoading(true); setNotice('');
    try { const d=await request('/api/discover',{method:'POST'}); if(d.status==='already_running'){setNotice(d.message);return;} setNotice(`${d.message} Found ${d.found} postings; ${d.relevant} relevant. ${d.successful_sources}/${d.configured_sources} sources healthy.`+(d.errors?.length?` First errors: ${d.errors.slice(0,3).join('; ')}`:'')); await loadDashboard(); }
    catch(e){setNotice(e.message);} finally{setLoading(false);}
  }
  async function draft(id) {
    setNotice('Generating your personalized cover letter…');
    try { const d=await request(`/api/jobs/${id}/cover-letter`,{method:'POST'}); setLetter(d.cover_letter); setNotice('Draft generated. Review every statement before using it.'); }
    catch(e){setNotice(e.message);}
  }
  async function match(id) {
    setNotice('Comparing this role with your resume and profile…');
    try { const d=await request(`/api/jobs/${id}/ai-match`,{method:'POST'}); setAiResult(d); setNotice('AI match completed.'); }
    catch(e){setNotice(e.message);}
  }
  async function saveDraft() {
    if(!selected) return;
    try { await request('/api/applications',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:selected.id,cover_letter:letter})}); setNotice('Saved to your private application tracker. Nothing was submitted.'); setLetter(''); setSelected(null); await loadDashboard(); }
    catch(e){setNotice(e.message);}
  }
  function toggleJob(id) {
    setBulkJobs(current => current.includes(id) ? current.filter(x=>x!==id)
      : current.length >= 10 ? current : [...current,id]);
  }
  function toggleApp(id) {
    setBulkApps(current => current.includes(id) ? current.filter(x=>x!==id)
      : current.length >= 10 ? current : [...current,id]);
    setConfirmReviewed(false);
  }
  async function prepareBulk() {
    if (!bulkJobs.length) return;
    setBusy(true);
    try {
      const result = await request('/api/applications/bulk', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({job_ids:bulkJobs})
      });
      setNotice(`${result.created.length} drafts created, ${result.already_saved.length} already saved, ${result.unavailable.length} unavailable. No applications submitted.`);
      setBulkJobs([]); await loadDashboard();
    } catch(e) {setNotice(e.message);} finally {setBusy(false);}
  }
  async function approveBulkHandoff() {
    if (!bulkApps.length || !confirmReviewed) return;
    setBusy(true); setHandoffs([]);
    try {
      const result = await request('/api/applications/bulk/handoff', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({application_ids:bulkApps, confirm_reviewed:true})
      });
      setHandoffs(result.applications);
      setNotice(result.message);
      setBulkApps([]);setConfirmReviewed(false);await loadDashboard();
    } catch(e) {setNotice(e.message);} finally {setBusy(false);}
  }
  async function openReview(id) {
    setBusy(true);
    try {
      const packet = await request(`/api/applications/${id}/packet`);
      setReviewPacket(packet);setReviewAnswers(packet.answers || {});
      setReviewLetter(packet.cover_letter || '');
    } catch(e) {setNotice(e.message);} finally {setBusy(false);}
  }
  async function prepareReviewLetter() {
    if(!reviewPacket) return;
    setBusy(true);
    try {
      const entry=apps.find(a=>a.id===reviewPacket.application_id);
      const result=await request(`/api/jobs/${entry.job_id}/cover-letter`,{method:'POST'});
      setReviewLetter(result.cover_letter);setNotice('AI draft prepared. Review every statement and save it.');
    } catch(e){setNotice(e.message);}finally{setBusy(false);}
  }
  async function saveReview() {
    if(!reviewPacket) return;
    setBusy(true);
    try {
      await request(`/api/applications/${reviewPacket.application_id}/content`,{
        method:'PUT',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({cover_letter:reviewLetter,answers:reviewAnswers})
      });
      setReviewPacket({...reviewPacket,cover_letter:reviewLetter,answers:reviewAnswers});
      setNotice('Application packet saved privately. Nothing was submitted.');await loadDashboard();
    } catch(e){setNotice(e.message);}finally{setBusy(false);}
  }
  function exportReview() {
    if(!reviewPacket) return;
    const packet={...reviewPacket,cover_letter:reviewLetter,answers:reviewAnswers,
      warning:'Private applicant data. Review all answers before submitting to an employer.'};
    const file=new Blob([JSON.stringify(packet,null,2)],{type:'application/json'});
    const url=URL.createObjectURL(file);
    const link=document.createElement('a');link.href=url;
    link.download=`internpilot-application-${reviewPacket.application_id}.json`;
    link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  async function changeStatus(id,status) {
    try { await request(`/api/applications/${id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})}); await loadDashboard(); }
    catch(e){setNotice(e.message);}
  }

  if(!token) return <main className="auth-shell">
    <header><div className="brand"><div className="logo"><Sparkles/></div><div><h1>InternPilot AI</h1><p>Your next opportunity starts here</p></div></div><span className="pill">Invite-only access</span></header>
    <section className="auth-card">
      <p className="eyebrow">YOUR CAREER, WITH A HEAD START</p><h2>{mode==='register'?'Create your account':'Welcome back'}</h2>
      <p className="muted">Discover opportunities and prepare applications using your own private profile.</p>
      <form onSubmit={submitAuth} className="stack">
        {mode==='register' && <><label>Invitation code<input required minLength="8" maxLength="64" autoComplete="off" value={auth.invite_code} onChange={e=>setAuth({...auth,invite_code:e.target.value.toUpperCase()})} placeholder="Enter the code you received"/><small className="muted">InternPilot AI is invite-only. Get your personal code directly from the site owner.</small></label><label>Full name<input required minLength="2" value={auth.full_name} onChange={e=>setAuth({...auth,full_name:e.target.value})} placeholder="Your name"/></label><label>Program<input value={auth.program} onChange={e=>setAuth({...auth,program:e.target.value})} placeholder="e.g. Software Engineering"/></label><label>Expected graduation year<input value={auth.graduation_year} onChange={e=>setAuth({...auth,graduation_year:e.target.value})} placeholder="e.g. 2028"/></label></>}
        <label>Email<input type="email" required value={auth.email} onChange={e=>setAuth({...auth,email:e.target.value})} placeholder="you@example.com"/></label>
        <label>Password<input type="password" required minLength={10} value={auth.password} onChange={e=>setAuth({...auth,password:e.target.value})} placeholder="At least 10 characters"/></label>
        <button className="primary wide" disabled={busy}>{busy?'Please wait…':mode==='register'?'Create free account':'Sign in'}</button>
      </form>
      <p className="switch">{mode==='register'?'Already have an account?':'New to InternPilot AI?'} <button onClick={()=>setMode(mode==='register'?'login':'register')}>{mode==='register'?'Sign in':'Create an account'}</button></p>
    </section>
    {notice&&<div className="notice">{notice}</div>}
    <footer>InternPilot AI · Invite-only early access · Keep your account credentials private.</footer>
  </main>;

  return <main>
    <header><div className="brand"><div className="logo"><Sparkles/></div><div><h1>InternPilot AI</h1><p>Your internship command centre</p></div></div><div className="account"><span>{user?.full_name || user?.email}</span><button className="secondary" onClick={logout}><LogOut size={15}/> Sign out</button></div></header>
    <section className="hero"><div><p className="eyebrow">YOUR NEXT OPPORTUNITY STARTS HERE</p><h2>Find the right internship.<br/><em>Spend less time applying.</em></h2><p className="sub">Your own resume-powered opportunity feed, AI matching and application workspace. Open to early-career job seekers from any background.</p></div><button className="primary" onClick={discover} disabled={loading}><RefreshCw size={17} className={loading?'spin':''}/>{loading?'Searching…':'Discover internships'}</button></section>
    {notice&&<div className="notice">{notice}</div>}
    {sourceStatus&&<div className="notice">{sourceStatus.checked_sources===0?`${sourceStatus.configured_sources} employer boards configured; first refresh will run shortly.`:`Job source health: ${sourceStatus.healthy_sources}/${sourceStatus.checked_sources} checked boards healthy - ${sourceStatus.active_jobs} active relevant postings - automatic refresh every 6 hours.`}</div>}
    <section className="stats"><div><strong>{jobs.length}</strong><span>Opportunities</span></div><div><strong>{apps.length}</strong><span>Your applications</span></div><div><strong>{user?.has_resume?'Ready':'Add resume'}</strong><span>Resume profile</span></div></section>
    <section className="panel">
      <div className="section-title"><div><h3><UserRound size={19}/> Your student profile</h3><p>Only your account can access this information.</p></div><ShieldCheck size={22}/></div>
      <form className="profile-grid" onSubmit={saveProfile}>
        <label>Full name<input value={profile.full_name||''} onChange={e=>setProfile({...profile,full_name:e.target.value})} required/></label>
        <label>University / institution<input value={profile.university||''} onChange={e=>setProfile({...profile,university:e.target.value})} placeholder="Your university or institution (optional)"/></label>
        <label>Program<input value={profile.program||''} onChange={e=>setProfile({...profile,program:e.target.value})} placeholder="Your program"/></label>
        <label>Graduation year<input value={profile.graduation_year||''} onChange={e=>setProfile({...profile,graduation_year:e.target.value})} placeholder="e.g. 2028"/></label>
        <label>Location<input value={profile.location||''} onChange={e=>setProfile({...profile,location:e.target.value})}/></label>
        <label>Work authorization<input value={profile.work_authorization||''} onChange={e=>setProfile({...profile,work_authorization:e.target.value})} placeholder="Only if you want to include it"/></label>
        <label className="span-two">Skills (comma separated)<input value={skillsText} onChange={e=>setSkillsText(e.target.value)} placeholder="Python, Java, React, SQL"/></label>
        <button className="primary" disabled={busy}>Save profile</button>
      </form>
      <form className="upload-row" onSubmit={uploadResume}><div><strong><Upload size={16}/> Resume</strong><p>{user?.has_resume?'A resume is saved to your private account.':'Upload PDF, DOCX or TXT (max 5 MB).'}</p></div><input type="file" accept=".pdf,.docx,.txt" onChange={e=>setResume(e.target.files?.[0]||null)}/><button className="secondary" disabled={busy||!resume}>Upload resume</button></form>
    </section>
    <section className="toolbar"><div><h3><BriefcaseBusiness size={19}/> Opportunity feed</h3><p>Match scores are calculated against your profile.</p></div><div className="filters"><label className="search"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search title, company, location"/></label><select value={minScore} onChange={e=>setMinScore(Number(e.target.value))}><option value="0">All matches</option><option value="50">50%+ match</option><option value="70">70%+ match</option><option value="85">85%+ match</option></select></div></section>
    <section className="panel geo-filters" aria-label="Internship filters">
      <div><h3>Find internships near you</h3><p className="muted small">Toronto/GTA is selected by default. Filter by engineering field, where you would work, and the term listed in the posting. "Not specified" means the employer did not clearly state a start term.</p></div>
      <div className="geo-filter-grid">
        <label>Location <select aria-label="Location filter" value={region} onChange={e=>setRegion(e.target.value)}>
          <option value="gta">Toronto &amp; GTA</option><option value="all">All locations</option>
          <option value="waterloo">Waterloo / Kitchener / Guelph</option>
          <option value="ontario_other">Other Ontario</option><option value="remote_canada">Remote Canada (no GTA city listed)</option>
          <option value="canada_other">Other Canada</option><option value="unknown">Unknown location</option>
        </select></label>
        <label>GTA city <select aria-label="GTA city filter" value={city} onChange={e=>{setCity(e.target.value); if(e.target.value!=='all')setRegion('gta')}}>
          <option value="all">All GTA cities</option>
          {['Toronto','North York','Scarborough','Etobicoke','Vaughan','Richmond Hill','Markham','Mississauga','Brampton','Oakville','Burlington','Oshawa','Pickering','Ajax','Whitby','Milton'].map(name=><option key={name} value={name.toLowerCase()}>{name}</option>)}
        </select></label>
        <label>Engineering field <select aria-label="Engineering field filter" value={discipline} onChange={e=>setDiscipline(e.target.value)}>
          <option value="all">All fields</option><option value="software">Software / Computing</option>
          <option value="mechanical">Mechanical / Manufacturing</option><option value="electrical">Electrical / Hardware</option>
          <option value="civil">Civil / Structural</option><option value="mechatronics">Mechatronics / Robotics</option>
          <option value="data_ai">Data / AI</option><option value="chemical">Chemical / Materials</option>
          <option value="aerospace">Aerospace</option><option value="general">General Engineering</option>
          <option value="other">Other</option>
        </select></label>
        <label>Work arrangement <select aria-label="Work arrangement filter" value={workMode} onChange={e=>setWorkMode(e.target.value)}>
          <option value="all">Any arrangement</option><option value="onsite">On-site</option><option value="hybrid">Hybrid</option>
          <option value="remote">Remote</option><option value="unspecified">Not specified</option>
        </select></label>
        <label>Start term <select aria-label="Start term filter" value={term} onChange={e=>setTerm(e.target.value)}>
          <option value="all">Any or unknown term</option>
          {['2027','2028','2029','2030'].flatMap(year=>['winter','spring','summer','fall'].map(season=><option key={`${season}-${year}`} value={`${season}-${year}`}>{season.charAt(0).toUpperCase()+season.slice(1)} {year}</option>))}
        </select></label>
      </div>
      <div className="geo-filter-actions"><span>{jobs.length} matching opportunities</span><button className="secondary" onClick={()=>{setQuery('');setMinScore(0);setRegion('all');setCity('all');setDiscipline('all');setWorkMode('all');setTerm('all')}}>Clear filters</button></div>
    </section>
    <section className="bulk-panel"><div><strong>Bulk application preparation</strong><p>Select up to 10 internships below. This creates private drafts; no employer receives any application yet.</p></div><button className="primary" disabled={!bulkJobs.length||busy} onClick={prepareBulk}>Prepare {bulkJobs.length} selected</button></section>
    <section className="joblist">{jobs.length===0?<div className="empty"><BriefcaseBusiness size={30}/><h3>No matching internships</h3><p>Try clearing filters, changing the location to All locations, or choosing Discover internships to refresh employer boards. A new employer board may be unavailable or temporarily have no internships.</p></div>:jobs.map(j=><article className="job" key={j.id}><label className="bulk-check"><input type="checkbox" checked={bulkJobs.includes(j.id)} disabled={!bulkJobs.includes(j.id)&&bulkJobs.length>=10} onChange={()=>toggleJob(j.id)}/> Select for bulk preparation</label><div className="jobtop"><div><h4>{j.title}</h4><p>{j.company} · {j.location||'Location not listed'}</p><p className="job-metadata">{j.discipline?.replace('_',' / ')||'Engineering'} · {j.work_mode==='unspecified'?'Arrangement not specified':j.work_mode} · Start: {j.start_label||'Not specified'}</p></div><span className="score">{j.match_score}% match</span></div>{j.match_explanation&&<p className="muted">{j.match_explanation}</p>}<div className="jobbottom"><span className="source">{j.source}</span><div><a href={j.url} target="_blank" rel="noreferrer">View posting <ExternalLink size={13}/></a><button className="secondary" onClick={()=>{setSelected(j);setLetter('');setAiResult(null)}}><FileText size={14}/> Prepare application</button></div></div></article>)}</section>
    <section className="toolbar apphead"><div><h3><FileText size={19}/> Your application tracker</h3><p>Private to your account. Employer-site handoffs are not submitted applications.</p></div></section>
    <section className="bulk-panel"><div><strong>Review and approve employer-site handoffs</strong><p>Select up to 10 saved drafts below. Check each employer’s application questions and required documents. This feature opens employer posting links; it does not submit them for you.</p><label className="bulk-check"><input type="checkbox" checked={confirmReviewed} onChange={e=>setConfirmReviewed(e.target.checked)}/> I reviewed my selected applications and understand they are not submitted yet.</label></div><button className="primary" disabled={!bulkApps.length||!confirmReviewed||busy} onClick={approveBulkHandoff}>Approve {bulkApps.length} handoffs</button></section>
    {handoffs.length>0&&<section className="panel"><h3>Employer posting pages — application action needed</h3><p className="muted">Open each employer posting and follow its Apply instructions to finish the form. Only mark an application as submitted once the employer confirms receipt.</p><div className="handoff-list">{handoffs.map(h=><div key={h.application_id}><span>{h.company} — {h.title}</span><a href={h.apply_url} target="_blank" rel="noopener noreferrer">Open employer posting <ExternalLink size={14}/></a></div>)}</div></section>}
    <section className="joblist">{apps.length===0?<p className="muted">Your saved application drafts will appear here.</p>:apps.map(a=><article className="job compact" key={a.id}><label className="bulk-check"><input type="checkbox" checked={bulkApps.includes(a.id)} disabled={['submitted','rejected','withdrawn'].includes(a.status)||(!bulkApps.includes(a.id)&&bulkApps.length>=10)} onChange={()=>toggleApp(a.id)}/> Review for handoff</label><div><h4>{a.title}</h4><p>{a.company} · {a.status}</p><p className="muted small">{a.submission_state === "user_reported_submitted" ? "Submission reported by you; not verified by employer" : a.submission_state === "needs_manual_submission" ? "Awaiting submission on employer site" : "Not submitted"}</p></div><select value={a.status} onChange={e=>changeStatus(a.id,e.target.value)}><option value="draft">Draft</option><option value="ready_for_review">Ready for review</option><option value="submitted">I submitted this</option><option value="rejected">Rejected</option><option value="withdrawn">Withdrawn</option></select><button className="secondary" onClick={()=>openReview(a.id)}>Review &amp; prepare</button><a href={a.url} target="_blank" rel="noreferrer">Posting <ExternalLink size={13}/></a></article>)}</section>
    {reviewPacket&&<div className="overlay"><div className="modal review-modal" role="dialog" aria-label="Application review">
      <button className="close" onClick={()=>setReviewPacket(null)} aria-label="Close review">×</button>
      <p className="eyebrow">REVIEW BEFORE SUBMITTING</p>
      <h2>{reviewPacket.title}</h2><p>{reviewPacket.company} · {reviewPacket.location || 'Location not provided'}</p>
      <p className="muted small">The information below is private to your account. Nothing has been submitted. The employer may ask additional questions.</p>
      <h3>Applicant details</h3><p>{reviewPacket.candidate.full_name} · {reviewPacket.candidate.email}</p>
      <p>{reviewPacket.candidate.university} · {reviewPacket.candidate.program} · Graduation: {reviewPacket.candidate.graduation_year || 'Not provided'}</p>
      <p>Resume: {reviewPacket.candidate.resume_filename || 'No resume uploaded'}</p>
      <button className="secondary" disabled={busy} onClick={prepareReviewLetter}>Generate tailored cover letter</button>
      <label className="field">Cover letter — edit and verify<textarea rows="9" value={reviewLetter} onChange={e=>setReviewLetter(e.target.value)}/></label>
      <h3>Common application answers (optional)</h3>
      <p className="muted small">Do not guess legal eligibility or availability. Leave fields blank if unsure.</p>
      {['Phone','LinkedIn','Portfolio / GitHub','Available start date','Why this company?'].map(k=><label key={k} className="field">{k}<input value={reviewAnswers[k]||''} onChange={e=>setReviewAnswers({...reviewAnswers,[k]:e.target.value})}/></label>)}
      <div className="review-actions"><button className="primary" disabled={busy} onClick={saveReview}>Save reviewed packet</button>
      <button className="secondary" onClick={exportReview}>Download application packet</button>
      <a className="secondary" href={reviewPacket.apply_url} target="_blank" rel="noopener noreferrer">Open employer application</a></div>
      <p className="muted small">Optional autofill helper instructions are in APPLY_ASSIST_README.md. Resume attachment and employer-specific questions require checking on the actual form. You must click Submit yourself.</p>
    </div></div>}
    {selected&&<div className="overlay"><div className="modal"><button className="close" onClick={()=>setSelected(null)}>×</button><p className="eyebrow">YOUR APPLICATION WORKSPACE</p><h2>{selected.title}</h2><p>{selected.company} · {selected.location}</p><div className="modalactions"><button className="secondary" onClick={()=>match(selected.id)}><Sparkles size={15}/> AI match</button><button className="secondary" onClick={()=>draft(selected.id)}><FileText size={15}/> Generate cover letter</button></div>{aiResult&&<div className="ai-result"><strong>AI fit score: {aiResult.score}%</strong><p>{aiResult.explanation}</p><p><b>Matched:</b> {aiResult.matched_skills?.join(', ')||'Not specified'}</p><p><b>Skills to develop:</b> {aiResult.missing_skills?.join(', ')||'Not specified'}</p></div>}<label className="field">Cover letter draft<textarea value={letter} onChange={e=>setLetter(e.target.value)} placeholder="Generate a draft or write/edit your own…"/></label><p className="muted small">Review and correct all details. Your final application submission remains your decision.</p><button className="primary wide" onClick={saveDraft}>Save to my applications</button></div></div>}
    <footer>InternPilot AI · Free invite-only early access · Your resume and applications are private to your account.</footer>
  </main>;
}
createRoot(document.getElementById('root')).render(<App/>);
