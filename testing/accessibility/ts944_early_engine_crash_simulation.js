async function installTs944EarlyEngineCrashSimulation(page) {
  await page.addInitScript(() => {
    const crashMarker = 'TS-944 simulated Flutter engine crash after bootstrap';

    const installCrashHook = () => {
      const flutter = window._flutter;
      const loader = flutter && flutter.loader;
      const load = loader && loader.load;
      if (typeof load !== 'function') {
        return false;
      }
      if (load.__ts944Patched === true) {
        return true;
      }

      const patchedLoad = (...args) => {
        console.error(crashMarker);
        throw new Error(crashMarker);
      };
      patchedLoad.__ts944Patched = true;
      patchedLoad.__ts944Original = load;
      loader.load = patchedLoad;
      return true;
    };

    if (installCrashHook()) {
      return;
    }

    const hookInterval = window.setInterval(() => {
      if (installCrashHook()) {
        window.clearInterval(hookInterval);
      }
    }, 0);

    window.addEventListener(
        'beforeunload',
        () => window.clearInterval(hookInterval),
        { once: true },
    );
  });
}

module.exports = {
  installTs944EarlyEngineCrashSimulation,
};
