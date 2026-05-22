const fs = require('node:fs');

const requiredEngineStateTokens = [
  'Flutter engine initialization:',
  'Semantics tree discovery:',
  'Accessibility runtime surface ready:',
];

function findMissingEngineStateTokens(logText) {
  return requiredEngineStateTokens.filter((token) => !logText.includes(token));
}

function validateAccessibilityLog(logText) {
  const missingTokens = findMissingEngineStateTokens(logText);
  if (missingTokens.length > 0) {
    throw new Error(
        'log-validation failed because mandatory engine state tokens were not '
        + `found in the output. Missing tokens: ${missingTokens.join(', ')}.`,
    );
  }
}

function readAccessibilityLog(logPath) {
  return fs.readFileSync(logPath, 'utf8');
}

function main(argv = process.argv.slice(2)) {
  const [logPath] = argv;
  if (!logPath) {
    throw new Error(
        'log-validation requires the accessibility log path as the first argument.',
    );
  }

  const logText = readAccessibilityLog(logPath);
  validateAccessibilityLog(logText);
  console.log(
      'log-validation passed: mandatory engine state tokens were found in the output.',
  );
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(message);
    process.exit(1);
  }
}

module.exports = {
  findMissingEngineStateTokens,
  main,
  readAccessibilityLog,
  requiredEngineStateTokens,
  validateAccessibilityLog,
};
