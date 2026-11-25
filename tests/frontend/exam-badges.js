(() => [...document.querySelectorAll('[class*="badge"]')].slice(0,12).map(b=>{const s=getComputedStyle(b);return {text:b.innerText,bg:s.backgroundColor,color:s.color};}))()
