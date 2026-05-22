async function installTs944EarlyEngineCrashSimulation(page) {
  await page.route(/main\.dart\.js(?:\?.*)?$/, async (route) => {
    console.error('TS-944 simulated Flutter engine crash after bootstrap');
    await route.abort('failed');
  });
}

module.exports = {
  installTs944EarlyEngineCrashSimulation,
};
