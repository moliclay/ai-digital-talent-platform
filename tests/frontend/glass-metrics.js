JSON.stringify({
  path: location.pathname,
  scrollWidth: document.documentElement.scrollWidth,
  innerWidth: window.innerWidth,
  scrollHeight: document.documentElement.scrollHeight,
  innerHeight: window.innerHeight,
  card: document.querySelector('[role="dialog"]') ? 'dialog' : 'page'
})
