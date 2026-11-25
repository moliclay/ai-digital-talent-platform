JSON.stringify([...document.querySelectorAll('button')].slice(0, 30).map((b) => ({t:(b.innerText||'').trim().slice(0,12), c:String(b.className).slice(0,50)})))
