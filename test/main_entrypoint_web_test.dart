import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/main.dart' as app_main;
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'main entrypoint mounts the TrackState shell instead of the TS-908 probe surface',
    (tester) async {
      app_main.main();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(seconds: 1));

      expect(find.byType(TrackStateApp), findsOneWidget);
      expect(find.text('Sync issue'), findsNothing);
    },
  );
}
