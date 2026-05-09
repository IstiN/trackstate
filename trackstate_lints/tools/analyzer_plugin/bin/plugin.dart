import 'dart:isolate';

import 'package:analyzer/file_system/physical_file_system.dart';
import 'package:analyzer_plugin/starter.dart';
import 'package:trackstate_lints/trackstate_lints.dart';

void main(List<String> args, SendPort sendPort) {
  ServerPluginStarter(
    TrackStateLintsPlugin(resourceProvider: PhysicalResourceProvider.INSTANCE),
  ).start(sendPort);
}
