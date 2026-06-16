import 'package:trackstate/domain/models/trackstate_models.dart';

abstract interface class IssueResolutionRepository {
  Future<TrackerSnapshot> loadSnapshot();
}
