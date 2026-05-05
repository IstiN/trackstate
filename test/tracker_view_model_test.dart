import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

void main() {
  test('view model loads snapshot and default search results', () async {
    final viewModel = TrackerViewModel(
      repository: const DemoTrackStateRepository(),
    );

    await viewModel.load();

    expect(viewModel.project?.key, 'TRACK');
    expect(viewModel.selectedIssue?.key, 'TRACK-12');
    expect(viewModel.searchResults, isNotEmpty);
  });

  test('view model changes sections and toggles theme', () async {
    final viewModel = TrackerViewModel(
      repository: const DemoTrackStateRepository(),
    );
    await viewModel.load();

    viewModel.selectSection(TrackerSection.board);
    viewModel.toggleTheme();

    expect(viewModel.section, TrackerSection.board);
    expect(viewModel.themePreference, ThemePreference.dark);
  });
}
