(async () => {
  const input = document.querySelector('#semantic-q');
  if (!input) return 'no-input';
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(input, '做过 RAG 的算法工程师');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  await new Promise((r) => setTimeout(r, 120));
  input.closest('form')?.requestSubmit();
  await new Promise((r) => setTimeout(r, 2200));
  const button = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '程磊');
  if (!button) return 'missing-name';
  button.click();
  await new Promise((r) => setTimeout(r, 800));
  return JSON.stringify({ search: location.search, modal: document.body.innerText.includes('程磊 · 简历') });
})()
