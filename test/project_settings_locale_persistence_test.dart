import 'dart:convert';
import 'dart:io';

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
        final persistedFieldsJson = File(
          '${fixture.repositoryPath}/DEMO/config/fields.json',
        ).readAsStringSync();
        final persistedDefaultLocaleJson =
            jsonDecode(
                  File(
                    '${fixture.repositoryPath}/DEMO/config/i18n/${Ts467LocaleResolutionFixture.defaultLocale}.json',
                  ).readAsStringSync(),
                )
                as Map<String, Object?>;

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
        expect(
          persistedFieldsJson,
          '[{"id":"summary","name":"Summary","type":"string","required":true},{"id":"description","name":"Description","type":"markdown","required":false}]\n',
        );
        expect(persistedDefaultLocaleJson['fields'], isEmpty);
      } finally {
        await fixture.dispose();
      }
    },
  );
}
