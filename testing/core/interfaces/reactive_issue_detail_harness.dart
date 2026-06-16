abstract interface class ReactiveIssueDetailHarness {
  Future<void> launch();

  Future<void> synchronizeSessionToReadOnly();

  void dispose();
}
