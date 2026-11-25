(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const click = (label) => {
    const button = [...document.querySelectorAll('button')].find((el) => el.textContent.trim() === label);
    if (button) button.click();
    return Boolean(button);
  };
  const setInput = (selector, value) => {
    const input = document.querySelector(selector);
    if (!input) return false;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  };
  if (!click('记录进度')) return 'no-record-button';
  await wait(500);
  setInput('#task-minutes', '200');
  setInput('#task-progress', '100');
  await wait(200);
  if (!click('保存')) return 'no-save';
  await wait(1600);
  if (!click('完成')) return 'no-complete';
  await wait(1800);
  return document.body.innerText.includes('3/3') ? 'completed' : 'maybe-blocked';
})()
