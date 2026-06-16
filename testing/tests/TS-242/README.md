# TS-242: Delete multiple issues concurrently — active search index is updated without stale references

## Objective
Verify that concurrent delete operations successfully remove all corresponding entries from the active issue index, ensuring search integrity.

## Test Type
API / Integration Test using Flutter Test framework

## Test Flow
1. **Setup**: Create a local Git repository fixture with three issues:
   - TRACK-4 (delete target)
   - TRACK-5 (delete target)
   - TRACK-3 (surviving issue)

2. **Precondition Checks**:
   - Verify that `.trackstate/index/issues.json` exists
   - Verify that both TRACK-4 and TRACK-5 are present in the active index
   - Verify that repository search returns all three issues
   - Verify the repository is clean (git status)

3. **Step 1 - Concurrent Delete**:
   - Trigger concurrent `repository.deleteIssue()` calls for TRACK-4 and TRACK-5
   - Verify that delete operations return tombstone results for each deleted issue

4. **Step 2 - Post-Delete Verification**:
   - Inspect `.trackstate/index/issues.json` file
   - Verify that TRACK-4 and TRACK-5 are NO LONGER in the active index
   - Verify that TRACK-3 (surviving issue) remains in the active index
   - Verify the repository remains clean

5. **Repository Reload Verification**:
   - Reload the repository to verify index consistency
   - Verify that repository search returns only TRACK-3
   - Verify that the active index entries match search results (index is strictly tied to Git tree)

## Expected Result
- Concurrent deletes remove all entries from the active issue index
- The active index no longer contains references to TRACK-4 or TRACK-5
- The search index is strictly tied to the existence of issues in the underlying Git tree
- Repository remains clean and consistent throughout the workflow
