import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/l10n/generated/app_localizations.dart';

class DirtyLocalIssueSavePage {
  const DirtyLocalIssueSavePage(this.tester);

  final WidgetTester tester;

  Future<void> open({
    required String initialDescription,
    required Future<void> Function(String description) onSave,
  }) async {
    await tester.pumpWidget(
      _DirtyLocalIssueSaveHarness(
        initialDescription: initialDescription,
        onSave: onSave,
      ),
    );
    await _pumpFrames();
  }

  Future<void> enterDescription(String description) async {
    await tester.enterText(find.byType(TextField), description);
    await _pumpFrames();
  }

  Future<void> save() async {
    final button = tester.widget<ElevatedButton>(
      find.widgetWithText(ElevatedButton, 'Save'),
    );
    await tester.runAsync(() async {
      button.onPressed?.call();
      await Future<void>.delayed(const Duration(milliseconds: 50));
    });
    await _pumpFrames();
  }

  Finder errorBannerContaining(String text) => find.textContaining(text);

  Future<void> _pumpFrames() async {
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump(const Duration(milliseconds: 200));
  }
}

class _DirtyLocalIssueSaveHarness extends StatefulWidget {
  const _DirtyLocalIssueSaveHarness({
    required this.initialDescription,
    required this.onSave,
  });

  final String initialDescription;
  final Future<void> Function(String description) onSave;

  @override
  State<_DirtyLocalIssueSaveHarness> createState() =>
      _DirtyLocalIssueSaveHarnessState();
}

class _DirtyLocalIssueSaveHarnessState
    extends State<_DirtyLocalIssueSaveHarness> {
  late final TextEditingController _controller;
  String? _message;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialDescription);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() {
      _isSaving = true;
      _message = null;
    });

    try {
      await widget.onSave(_controller.text);
      setState(() {
        _message = 'Saved';
      });
    } on Object catch (error) {
      setState(() {
        _message = 'Save failed: $error';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: Builder(
        builder: (context) {
          final l10n = AppLocalizations.of(context)!;
          return Scaffold(
            body: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: _controller,
                    maxLines: 6,
                    decoration: InputDecoration(labelText: l10n.description),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: _isSaving ? null : _save,
                    child: const Text('Save'),
                  ),
                  if (_message != null) ...[
                    const SizedBox(height: 16),
                    Text(_message!),
                  ],
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
