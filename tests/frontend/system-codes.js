(() => [...document.querySelectorAll('code')].map(c=>{const s=getComputedStyle(c);return {text:c.innerText,bg:s.backgroundColor,color:s.color};}))()
