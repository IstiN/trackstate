from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any

from testing.core.interfaces.web_app_session import WebAppSession, WebAppTimeoutError
from testing.core.utils.polling import poll_until


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
        self._log_name = "github-save-sequence-probe"

    def install(self) -> None:
        if self._supports_playwright_network_recording():
            self._session.start_network_recording(  # type: ignore[attr-defined]
                name=self._log_name,
                url_fragment=f"/repos/{self._repository.lower()}/git/",
            )
            return
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
        if self._supports_playwright_network_recording():
            matched, payload = poll_until(
                probe=lambda: self._payload_from_entries(
                    self.read_log(),
                    stale_write_sha=stale_write_sha,
                ),
                is_satisfied=lambda value: (
                    isinstance(value, dict) and value.get("kind") == "observed"
                ),
                timeout_seconds=max(timeout_ms / 1000, 1),
                interval_seconds=0.25,
            )
            if not matched:
                self._raise_payload_error(payload, stale_write_sha=stale_write_sha)
            assert isinstance(payload, dict)
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
                    .find((entry) => requestMatches(entry, 'GET', '/git/ref/heads/'));
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

        if not isinstance(payload, dict) or str(payload.get("kind")) != "observed":
            self._raise_payload_error(
                payload if isinstance(payload, dict) else None,
                stale_write_sha=stale_write_sha,
            )
        assert isinstance(payload, dict)

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
        if self._supports_playwright_network_recording():
            payload = self._session.read_network_log(name=self._log_name)  # type: ignore[attr-defined]
            return [
                dict(entry)
                for entry in payload
                if isinstance(entry, dict)
            ]
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

    def _supports_playwright_network_recording(self) -> bool:
        return hasattr(self._session, "start_network_recording") and hasattr(
            self._session,
            "read_network_log",
        )

    def _payload_from_entries(
        self,
        raw_entries: list[dict[str, object]],
        *,
        stale_write_sha: str,
    ) -> dict[str, object] | None:
        entries = [
            GitHubNetworkEntry.from_payload(entry)
            for entry in raw_entries
            if isinstance(entry, dict)
        ]
        ref_request = next(
            (
                entry
                for entry in reversed(entries)
                if entry.phase == "request"
                and entry.method == "GET"
                and "/git/ref/heads/" in entry.url
            ),
            None,
        )
        if ref_request is None:
            return None
        ref_response = self._response_for(entries, ref_request)
        if ref_response is None or ref_response.status != 200:
            return None
        try:
            ref_json = json.loads(ref_response.response_text or "{}")
        except json.JSONDecodeError as error:
            return {
                "kind": "invalid-ref-response",
                "entries": raw_entries,
                "refRequest": ref_request.as_dict(),
                "refResponse": ref_response.as_dict(),
                "parseError": str(error),
            }
        ref_object = ref_json.get("object") if isinstance(ref_json, dict) else None
        ref_sha = ref_object.get("sha") if isinstance(ref_object, dict) else None
        if not isinstance(ref_sha, str) or not ref_sha:
            return {
                "kind": "missing-ref-sha",
                "entries": raw_entries,
                "refRequest": ref_request.as_dict(),
                "refResponse": ref_response.as_dict(),
            }
        commit_request = next(
            (
                entry
                for entry in entries
                if entry.phase == "request"
                and entry.method == "GET"
                and f"/git/commits/{ref_sha}" in entry.url
                and entry.order > ref_request.order
            ),
            None,
        )
        if commit_request is None:
            return None
        commit_response = self._response_for(entries, commit_request)
        if commit_response is None or commit_response.status != 200:
            return None
        tree_request = next(
            (
                entry
                for entry in entries
                if entry.phase == "request"
                and entry.method == "POST"
                and "/git/trees" in entry.url
                and entry.order > commit_request.order
            ),
            None,
        )
        if tree_request is None:
            return None
        statuses = [
            entry.status
            for entry in entries
            if entry.phase == "response" and entry.status is not None
        ]
        return {
            "kind": "observed",
            "entries": raw_entries,
            "refRequest": ref_request.as_dict(),
            "refResponse": ref_response.as_dict(),
            "refSha": ref_sha,
            "commitRequest": commit_request.as_dict(),
            "commitResponse": commit_response.as_dict(),
            "treeRequest": tree_request.as_dict(),
            "refWasStale": ref_sha != stale_write_sha,
            "statuses": statuses,
        }

    def _response_for(
        self,
        entries: list[GitHubNetworkEntry],
        request: GitHubNetworkEntry,
    ) -> GitHubNetworkEntry | None:
        return next(
            (
                entry
                for entry in entries
                if entry.phase == "response" and entry.request_id == request.request_id
            ),
            None,
        )

    def _raise_payload_error(
        self,
        payload: dict[str, object] | None,
        *,
        stale_write_sha: str,
    ) -> None:
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
        if kind == "observed" and not bool(payload.get("refWasStale")):
            raise AssertionError(
                "Step 6 failed: the save flow did not prove that the branch ref lookup moved "
                "past the stale stored SHA before the tree update.\n"
                f"Stale write SHA: {stale_write_sha}\n"
                f"Observed payload: {payload}",
            )
        raise AssertionError(
            "Step 6 failed: the hosted save flow did not expose an observable "
            "fetch-before-write sequence.\n"
            f"Observed payload: {payload}",
        )

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
