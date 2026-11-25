(async () => {
  await document.fonts.ready;
  const title = document.querySelector('h1');
  return {
    font: title ? getComputedStyle(title).fontFamily : '',
    jakartaLoaded: document.fonts.check('16px "Plus Jakarta Sans"'),
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  };
})()
