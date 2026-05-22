async function holdTs962CancellationWindow() {
  console.log('TS-962 cancellation hold started');
  await new Promise((resolve) => setTimeout(resolve, 45000));
  console.log('TS-962 cancellation hold completed');
}

module.exports = {
  holdTs962CancellationWindow,
};
