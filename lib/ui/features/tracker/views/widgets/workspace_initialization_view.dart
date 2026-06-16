import 'package:flutter/material.dart';

import '../../../../../ui/core/trackstate_theme.dart';
import '../../../../../../l10n/generated/app_localizations.dart';
import '../../view_models/tracker_view_model.dart';

class WorkspaceInitializationView extends StatelessWidget {
  const WorkspaceInitializationView({super.key, required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      backgroundColor: colors.page,
      body: Center(
        child: Semantics(
          label: l10n.appTitle,
          child: CircularProgressIndicator(color: colors.primary),
        ),
      ),
    );
  }
}
