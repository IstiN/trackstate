from __future__ import annotations

from yaml import SafeLoader


class WorkflowSafeLoader(SafeLoader):
    """PyYAML loader that preserves workflow keys such as 'on:' as strings.

    GitHub Actions workflow YAML uses keys like ``on:`` that PyYAML's
    default ``SafeLoader`` interprets as booleans. This loader strips the
    bool implicit resolver so those keys remain plain strings.
    """

    pass


WorkflowSafeLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:bool"]
    for key, resolvers in SafeLoader.yaml_implicit_resolvers.items()
}
