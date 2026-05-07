import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

abstract interface class IssueDeletionPort {
  Future<TrackerSnapshot> loadSnapshot();

  Future<RepositoryPermission> getPermission();

  Future<String> resolveWriteBranch();

  Future<List<RepositoryTreeEntry>> listTree({required String ref});

  Future<RepositoryTextFile> readTextFile(String path, {required String ref});

  Future<RepositoryWriteResult> writeTextFile(RepositoryWriteRequest request);
}
