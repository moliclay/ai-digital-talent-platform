(() => JSON.stringify({reduce:matchMedia('(prefers-reduced-motion: reduce)').matches, count:document.getAnimations().length, names:document.getAnimations().map(a=>a.animationName)}))()
