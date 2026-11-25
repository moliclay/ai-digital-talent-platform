(async () => {
  const token = localStorage.getItem('token');
  let me;
  try { const r=await fetch('/api/auth/me',{headers: token?{Authorization:`Bearer ${token}`}:{}}); me={status:r.status, body:(await r.text()).slice(0,80)}; } catch(e) { me={err:String(e)}; }
  return JSON.stringify({href:location.href, token:token?token.slice(0,12):null, ls:Object.keys(localStorage), me, text:document.body.innerText.slice(0,120)});
})()
