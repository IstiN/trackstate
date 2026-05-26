# Rework Focus

- Address requested findings directly.
- Keep fixes inside the repository scope defined for the ticket.
- Do not rewrite unrelated workflow or agent behavior.
- Preserve public config names and existing runtime contracts.
- If reviewer flagged a web-platform gap: add `kIsWeb` gate AND browser fallback, not just a comment.
- If reviewer flagged missing notification: add `notifyListeners()` in ALL completion/error branches of the deferred operation.
- If reviewer flagged scope creep: REMOVE the unrelated changes entirely — do not justify them, just remove.
