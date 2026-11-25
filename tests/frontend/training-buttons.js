(() => {
  const buttons = [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(Boolean);
  const dialogs = [...document.querySelectorAll('[role="dialog"]')].map(d => ({text:(d.innerText||'').slice(0,60), cls:d.className}));
  return JSON.stringify({buttons, dialogs, body:(document.body.innerText||'').slice(-220)});
})()
