from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from testing.core.interfaces.web_app_session import WebAppSession, WebAppTimeoutError


@dataclass(frozen=True)
class GitHubNetworkEntry:
    phase: str
    transport: str
    request_id: str
    method: str
    url: str
    order: int
    timestamp: str
    status: int | None = None
    body_text: str | None = None
    response_text: str | None = None
    error_text: str | None = None

    @classmethod
    def from_payload(cls, payload: object) -> "GitHubNetworkEntry":
        if not isinstance(payload, dict):
            raise AssertionError(
                "Expected a GitHub network entry payload object while parsing the hosted "
                f"save sequence, got {payload!r}.",
            )
        return cls(
            phase=str(payload.get("phase", "")),
            transport=str(payload.get("transport", "")),
            request_id=str(payload.get("requestId", "")),
            method=str(payload.get("method", "")),
            url=str(payload.get("url", "")),
            order=int(payload.get("order", 0)),
            timestamp=str(payload.get("timestamp", "")),
            status=(
                None
                if payload.get("status") is None
                else int(payload.get("status", 0))
            ),
            body_text=_optional_string(payload.get("bodyText")),
            response_text=_optional_string(payload.get("responseText")),
            error_text=_optional_string(payload.get("errorText")),
        )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GitHubFetchBeforeWriteObservation:
    entries: tuple[GitHubNetworkEntry, ...]
    ref_request: GitHubNetworkEntry
    ref_response: GitHubNetworkEntry
    ref_sha: str
    commit_request: GitHubNetworkEntry
    commit_response: GitHubNetworkEntry
    tree_request: GitHubNetworkEntry
    ref_was_stale: bool
    response_statuses: tuple[int, ...]

    def summary(self) -> str:
        return (
            "Observed GitHub save sequence "
            f"{self.ref_request.method} {self.ref_request.url} -> "
            f"{self.commit_request.method} {self.commit_request.url} -> "
            f"{self.tree_request.method} {self.tree_request.url}. "
            f"Branch ref SHA {self.ref_sha} replaced stale write SHA. "
            f"Response statuses={list(self.response_statuses)}."
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "entries": [entry.as_dict() for entry in self.entries],
            "refRequest": self.ref_request.as_dict(),
            "refResponse": self.ref_response.as_dict(),
            "refSha": self.ref_sha,
            "commitRequest": self.commit_request.as_dict(),
            "commitResponse": self.commit_response.as_dict(),
            "treeRequest": self.tree_request.as_dict(),
            "refWasStale": self.ref_was_stale,
            "statuses": list(self.response_statuses),
        }


class GitHubSaveSequenceProbe:
    def __init__(self, *, session: WebAppSession, repository: str) -> None:
        self._session = session
        self._repository = repository

    def install(self) -> None:
        self._session.evaluate(
            """
            ({ repository }) => {
              const repoFragment = `/repos/${repository}/git/`;
              const toText = async (response) => {
                try {
                  return await response.clone().text();
                } catch (error) {
                  return `[[unreadable response body: ${String(error)}]]`;
                }
              };
              const ensureStore = () => {
                const existing = window.__githubSaveSequenceProbe;
                if (existing && Array.isArray(existing.entries)) {
                  return existing;
                }
                const created = {
                  installed: true,
                  nextId: 1,
                  entries: [],
                };
                window.__githubSaveSequenceProbe = created;
                return created;
              };
              const store = ensureStore();
              const pushEntry = (entry) => {
                store.entries.push({
                  ...entry,
                  order: store.entries.length + 1,
                  timestamp: new Date().toISOString(),
                });
              };
              const trackedUrl = (value) =>
                typeof value === 'string' && value.includes(repoFragment);
              if (
                !window.__githubSaveSequenceProbeFetchWrapped
                && typeof window.fetch === 'function'
              ) {
                const originalFetch = window.fetch.bind(window);
                window.fetch = async (input, init) => {
                  const requestUrl =
                    typeof input === 'string'
                      ? input
                      : (input && typeof input.url === 'string' ? input.url : '');
                  const method = String(
                    (init && init.method)
                      || (typeof input !== 'string' && input && input.method)
                      || 'GET',
                  ).toUpperCase();
                  const requestId = `fetch-${store.nextId++}`;
                  const requestBody =
                    init && typeof init.body === 'string'
                      ? init.body
                      : (init && init.body ? String(init.body) : '');
                  if (trackedUrl(requestUrl)) {
                    pushEntry({
                      phase: 'request',
                      transport: 'fetch',
                      requestId,
                      method,
                      url: requestUrl,
                      bodyText: requestBody,
                    });
                  }
                  try {
                    const response = await originalFetch(input, init);
                    if (trackedUrl(requestUrl)) {
                      pushEntry({
                        phase: 'response',
                        transport: 'fetch',
                        requestId,
                        method,
                        url: requestUrl,
                        status: response.status,
                        responseText: await toText(response),
                      });
                    }
                    return response;
                  } catch (error) {
                    if (trackedUrl(requestUrl)) {
                      pushEntry({
                        phase: 'error',
                        transport: 'fetch',
                        requestId,
                        method,
                        url: requestUrl,
                        errorText: String(error),
                      });
                    }
                    throw error;
                  }
                };
                window.__githubSaveSequenceProbeFetchWrapped = true;
              }

              if (
                !window.__githubSaveSequenceProbeXhrWrapped
                && window.XMLHttpRequest
              ) {
                const originalOpen = window.XMLHttpRequest.prototype.open;
                const originalSend = window.XMLHttpRequest.prototype.send;
                window.XMLHttpRequest.prototype.open = function(method, url, ...rest) {
                  this.__githubSaveSequenceProbe = {
                    method: String(method || 'GET').toUpperCase(),
                    url: String(url || ''),
                    requestId: `xhr-${store.nextId++}`,
                  };
                  return originalOpen.call(this, method, url, ...rest);
                };
                window.XMLHttpRequest.prototype.send = function(body) {
                  const meta = this.__githubSaveSequenceProbe;
                  if (meta && trackedUrl(meta.url)) {
                    pushEntry({
                      phase: 'request',
                      transport: 'xhr',
                      requestId: meta.requestId,
                      method: meta.method,
                      url: meta.url,
                      bodyText:
                        typeof body === 'string' ? body : (body ? String(body) : ''),
                    });
                    this.addEventListener(
                      'loadend',
                      () => {
                        pushEntry({
                          phase: 'response',
                          transport: 'xhr',
                          requestId: meta.requestId,
                          method: meta.method,
                          url: meta.url,
                          status: this.status,
                          responseText:
                            typeof this.responseText === 'string'
                              ? this.responseText
                              : '',
                        });
                      },
                      { once: true },
                    );
                  }
                  return originalSend.call(this, body);
                };
                window.__githubSaveSequenceProbeXhrWrapped = true;
              }

              store.entries.length = 0;
              return {
                installed: true,
                repository,
              };
            }
            """,
            arg={"repository": self._repository},
        )

    def wait_for_fetch_before_write_sequence(
        self,
        *,
        stale_write_sha: str,
        timeout_ms: int = 60_000,
    ) -> GitHubFetchBeforeWriteObservation:
        try:
            payload = self._session.wait_for_function(
                """
                ({ staleWriteSha }) => {
                  const store = window.__githubSaveSequenceProbe;
                  if (!store || !Array.isArray(store.entries)) {
                    return null;
                  }
                  const entries = store.entries.slice();
                  const requestMatches = (entry, method, fragment) =>
                    entry
                    && entry.phase === 'request'
                    && entry.method === method
                    && typeof entry.url === 'string'
                    && entry.url.includes(fragment);
                  const responseFor = (requestEntry) =>
                    entries.find(
                      (entry) =>
                        entry.phase === 'response' && entry.requestId === requestEntry.requestId,
                    ) || null;
                  const refRequest = [...entries]
                    .reverse()
                    .find((entry) => requestMatches(entry, 'GET', '/git/refs/heads/'));
                  if (!refRequest) {
                    return null;
                  }
                  const refResponse = responseFor(refRequest);
                  if (!refResponse || refResponse.status !== 200) {
                    return null;
                  }
                  let refSha = null;
                  try {
                    const refJson = JSON.parse(refResponse.responseText || '{}');
                    refSha =
                      refJson && refJson.object && typeof refJson.object.sha === 'string'
                        ? refJson.object.sha
                        : null;
                  } catch (error) {
                    return {
                      kind: 'invalid-ref-response',
                      entries,
                      refRequest,
                      refResponse,
                      parseError: String(error),
                    };
                  }
                  if (!refSha) {
                    return {
                      kind: 'missing-ref-sha',
                      entries,
                      refRequest,
                      refResponse,
                    };
                  }
                  const commitRequest = entries.find(
                    (entry) =>
                      requestMatches(entry, 'GET', `/git/commits/${refSha}`)
                      && entry.order > refRequest.order,
                  );
                  if (!commitRequest) {
                    return null;
                  }
                  const commitResponse = responseFor(commitRequest);
                  if (!commitResponse || commitResponse.status !== 200) {
                    return null;
                  }
                  const treeRequest = entries.find(
                    (entry) =>
                      requestMatches(entry, 'POST', '/git/trees')
                      && entry.order > commitRequest.order,
                  );
                  if (!treeRequest) {
                    return null;
                  }
                  const refWasStale =
                    typeof staleWriteSha === 'string' && refSha !== staleWriteSha;
                  const statuses = entries
                    .filter((entry) => entry.phase === 'response')
                    .map((entry) => entry.status);
                  return {
                    kind: 'observed',
                    entries,
                    refRequest,
                    refResponse,
                    refSha,
                    commitRequest,
                    commitResponse,
                    treeRequest,
                    refWasStale,
                    statuses,
                  };
                }
                """,
                arg={"staleWriteSha": stale_write_sha},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 6 failed: the hosted save flow never exposed the expected GitHub ref, "
                "commit, and tree request sequence after clicking Save.\n"
                f"Observed network log: {self.read_log()}",
            ) from error

        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 6 failed: the hosted save flow never exposed the expected GitHub ref, "
                "commit, and tree request sequence after clicking Save.\n"
                f"Observed network log: {self.read_log()}",
            )
        kind = str(payload.get("kind"))
        if kind == "invalid-ref-response":
            raise AssertionError(
                "Step 6 failed: the GitHub ref lookup response could not be parsed while "
                "verifying the fetch-before-write sequence.\n"
                f"Observed payload: {payload}",
            )
        if kind == "missing-ref-sha":
            raise AssertionError(
                "Step 6 failed: the GitHub ref lookup response did not expose a branch head "
                "SHA before the tree update.\n"
                f"Observed payload: {payload}",
            )
        if kind != "observed":
            raise AssertionError(
                "Step 6 failed: the hosted save flow did not expose an observable "
                "fetch-before-write sequence.\n"
                f"Observed payload: {payload}",
            )

        observation = self._build_observation(payload)
        if not observation.ref_was_stale:
            raise AssertionError(
                "Step 6 failed: the save flow did not prove that the branch ref lookup moved "
                "past the stale stored SHA before the tree update.\n"
                f"Stale write SHA: {stale_write_sha}\n"
                f"Observed payload: {payload}",
            )
        if any(status == 422 for status in observation.response_statuses):
            raise AssertionError(
                "Step 6 failed: the save network sequence still hit GitHub HTTP 422 during "
                "the stale-base-SHA scenario.\n"
                f"Observed payload: {payload}",
            )
        return observation

    def read_log(self) -> list[dict[str, object]]:
        payload = self._session.evaluate(
            "() => window.__githubSaveSequenceProbe?.entries ?? []",
        )
        if not isinstance(payload, list):
            return []
        entries: list[dict[str, object]] = []
        for entry in payload:
            if isinstance(entry, dict):
                entries.append(dict(entry))
        return entries

    def _build_observation(
        self,
        payload: dict[str, Any],
    ) -> GitHubFetchBeforeWriteObservation:
        raw_entries = payload.get("entries", [])
        entries = tuple(
            GitHubNetworkEntry.from_payload(entry)
            for entry in raw_entries
            if isinstance(entry, dict)
        )
        statuses = payload.get("statuses", [])
        return GitHubFetchBeforeWriteObservation(
            entries=entries,
            ref_request=GitHubNetworkEntry.from_payload(payload.get("refRequest")),
            ref_response=GitHubNetworkEntry.from_payload(payload.get("refResponse")),
            ref_sha=str(payload.get("refSha", "")),
            commit_request=GitHubNetworkEntry.from_payload(payload.get("commitRequest")),
            commit_response=GitHubNetworkEntry.from_payload(payload.get("commitResponse")),
            tree_request=GitHubNetworkEntry.from_payload(payload.get("treeRequest")),
            ref_was_stale=bool(payload.get("refWasStale")),
            response_statuses=tuple(
                int(status)
                for status in statuses
                if isinstance(status, int)
            ),
        )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
