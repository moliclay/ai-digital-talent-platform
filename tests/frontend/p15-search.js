(async () => {
  const input = document.querySelector('#semantic-q');
  if (!input) return 'no-input';
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(input, '做过 RAG 的算法工程师');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  await new Promise((r) => setTimeout(r, 120));
  const form = input.closest('form');
  form.requestSubmit();
  await new Promise((r) => setTimeout(r, 2200));
  return document.body.innerText.includes('程磊') ? 'searched' : 'no-result';
})()
