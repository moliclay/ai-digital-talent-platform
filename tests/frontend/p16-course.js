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
  if (!click('新建课程')) return 'no-create-button';
  await wait(500);
  setInput('#course-name', '临时课程QA');
  setInput('#course-category', '工程');
  setInput('#course-hours', '1');
  await wait(200);
  if (!click('保存')) return 'no-save';
  await wait(1800);
  return document.body.innerText.includes('临时课程QA') ? 'created' : 'not-created';
})()
