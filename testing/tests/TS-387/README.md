# TS-387

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-387 -p 'test_*.py' -v
```

## Required configuration

This test compiles a temporary TrackState CLI binary from the current checkout, seeds a disposable local repository with `TS-22` plus two source files, and runs the exact ticket command:

```bash
trackstate attachment upload --issue TS-22 --file file1.png --file file2.png --target local
```

## Expected passing output

```text
OK
```
