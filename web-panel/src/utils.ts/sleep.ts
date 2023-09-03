export const sleep = (durationMs = 1000) =>
  new Promise((resolve) => setTimeout(resolve, durationMs));
