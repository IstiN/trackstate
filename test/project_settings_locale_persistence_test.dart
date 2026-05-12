import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../testing/tests/TS-467/support/ts467_locale_resolution_fixture.dart';

void main() {
  test(
    'saving project settings persists localized status labels to the repository snapshot',
    () async {
      final fixture = await Ts467LocaleResolutionFixture.create();

      try {
        final repository = LocalTrackStateRepository(
          repositoryPath: fixture.repositoryPath,
        );
        final snapshot = await repository.loadSnapshot();
        final settings = snapshot.project.settingsCatalog.copyWith(
          statusDefinitions: [
            for (final status in snapshot.project.statusDefinitions)
              if (status.id == 'in-progress')
                status.copyWith(
                  localizedLabels: {
                    ...status.localizedLabels,
                    Ts467LocaleResolutionFixture.viewerLocale: 'WIP',
                  },
                )
              else
                status,
          ],
        );

        final updatedSnapshot = await (repository as ProjectSettingsRepository)
            .saveProjectSettings(settings);

        expect(
          updatedSnapshot.project.statusLabel(
            'in-progress',
            locale: Ts467LocaleResolutionFixture.viewerLocale,
          ),
          'WIP',
        );
        expect(
          (await repository.loadSnapshot()).project.statusLabel(
            'in-progress',
            locale: Ts467LocaleResolutionFixture.viewerLocale,
          ),
          'WIP',
        );
      } finally {
        await fixture.dispose();
      }
    },
  );
}
