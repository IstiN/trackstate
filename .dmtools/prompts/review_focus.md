# Review Focus

- Check repository and workflow compatibility first.
- Verify config paths, workflow inputs, and shared agent references.
- Flag changes that expand scope beyond the requested repository work.
- Prioritize correctness, security, and backward compatibility over style.
- BLOCKING: any `Process.run` or `dart:io` usage not gated on `!kIsWeb`
- BLOCKING: any deferred/unawaited async that changes state without `notifyListeners()`
- BLOCKING: workspace state change that reuses `previousViewModel.repository` instead of fresh state
- BLOCKING: unrelated file changes not justified by the ticket (scope creep)
