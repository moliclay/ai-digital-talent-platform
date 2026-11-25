(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const setValue = (el, value) => {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  };

  const name = document.querySelector("#candidate");
  if (name) setValue(name, "张伟");
  await sleep(150);

  const labels = [...document.querySelectorAll("label")];
  for (const text of ["PyTorch", "先确认对方担心的具体风险点"]) {
    for (const label of labels) {
      const input = label.querySelector("input");
      if (input && !input.checked && label.textContent.includes(text)) label.click();
    }
  }
  await sleep(300);

  const submit = [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "交卷");
  if (submit) submit.click();
  await sleep(900);

  return {
    dialog: document.querySelector("[role=dialog]")?.innerText ?? "",
  };
})()
