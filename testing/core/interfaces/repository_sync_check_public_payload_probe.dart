import 'package:trackstate/data/providers/trackstate_provider.dart';

abstract interface class RepositorySyncCheckPublicPayloadProbe {
  Map<String, Object?> serialize(RepositorySyncCheck syncCheck);
}
