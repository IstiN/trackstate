import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/main.dart' as app_main;
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('main bootstraps the TrackState app', (tester) async {
    app_main.main();
    await tester.pump();

    expect(find.byType(TrackStateApp), findsOneWidget);
  });
}
