async function installTs953NetworkTimeoutSimulation(page) {
  page.setDefaultNavigationTimeout(15000);
  await page.route('**/*', async (route) => {
    if (route.request().isNavigationRequest()) {
      await new Promise(() => {});
      return;
    }
    await route.continue();
  });
}

module.exports = {
  installTs953NetworkTimeoutSimulation,
};
