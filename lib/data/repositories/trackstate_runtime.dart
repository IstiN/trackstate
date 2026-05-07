enum TrackStateRuntime { github, localGit }

TrackStateRuntime parseTrackStateRuntime(String value) {
  return switch (value.trim().toLowerCase()) {
    'github' || 'hosted' => TrackStateRuntime.github,
    'local' || 'local-git' || 'git' => TrackStateRuntime.localGit,
    _ => throw ArgumentError.value(
      value,
      'value',
      'Unsupported TrackState runtime. Use github or local-git.',
    ),
  };
}

const configuredTrackStateRuntimeName = String.fromEnvironment(
  'TRACKSTATE_RUNTIME',
  defaultValue: 'github',
);
final configuredTrackStateRuntime = parseTrackStateRuntime(
  configuredTrackStateRuntimeName,
);
const configuredLocalRepositoryPath = String.fromEnvironment(
  'TRACKSTATE_LOCAL_REPOSITORY_PATH',
);
