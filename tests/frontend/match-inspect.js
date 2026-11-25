(() => {
 const f=[...document.querySelectorAll('[class*="filterActive"]')][0]; const fs=f?getComputedStyle(f):null;
 const track=[...document.querySelectorAll('[class*="track"]')].find(el=>el.closest('td'));
 const fill=track?.querySelector('[class*="fill"]');
 const ts=track?getComputedStyle(track):null; const fls=fill?getComputedStyle(fill):null;
 return JSON.stringify({filter:fs?{bg:fs.backgroundColor,color:fs.color,outline:fs.outlineColor}:null, track:ts?{bg:ts.backgroundColor}:null, fill:fls?{bg:fls.backgroundColor,bgi:fls.backgroundImage}:null});
})()
