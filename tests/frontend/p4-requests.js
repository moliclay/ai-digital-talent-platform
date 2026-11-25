(async () => {
  const entries = performance.getEntriesByType('resource')
    .map((entry) => entry.name)
    .filter((name) => name.includes('/api/'))
    .map((name) => new URL(name).pathname);
  return JSON.stringify([...new Set(entries)]);
})()
