(async () => {
  const button = document.querySelector('button[role="switch"]');
  if (!button) return 'missing';
  button.click();
  await new Promise((resolve) => setTimeout(resolve, 1200));
  return JSON.stringify({ search: location.search, rows: document.querySelectorAll('tbody tr').length });
})()
