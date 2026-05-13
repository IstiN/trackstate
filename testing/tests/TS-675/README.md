# TS-675

Verifies that `trackstate read ticket --key TS-2` aggregates mixed inward and
outward issue links into the canonical top-level `links` array without
overwriting either relationship.

The test:

1. seeds a disposable local-git TrackState repository
2. creates Issue A, Issue B, and Issue C
3. creates a symmetric inward link with `trackstate ticket link --type "relates to"`
4. creates an outward link with `trackstate ticket link --type blocks`
5. runs the exact ticket step `trackstate read ticket --key TS-2`
6. verifies the response contains exactly these top-level link entries:
   `{"type":"relates to","target":"TS-1","direction":"inward"}`
   `{"type":"blocks","target":"TS-3","direction":"outward"}`

Run with:

```bash
python -m unittest testing.tests.TS-675.test_ts_675
```
