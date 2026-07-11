import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// Dart wrapper around the native Android AlarmService.
/// Uses a MethodChannel to start/stop the alarm that wakes the phone
/// and rings like a phone call.
class AlarmService {
  static const _channel = MethodChannel('com.secureguard/alarm');

  /// Start the alarm — wakes screen, rings at max volume, vibrates.
  static Future<void> start() async {
    try {
      await _channel.invokeMethod('startAlarm');
      debugPrint('AlarmService: alarm started');
    } catch (e) {
      debugPrint('AlarmService: failed to start alarm — $e');
    }
  }

  /// Stop the alarm — silences ringtone, stops vibration, releases wake lock.
  static Future<void> stop() async {
    try {
      await _channel.invokeMethod('stopAlarm');
      debugPrint('AlarmService: alarm stopped');
    } catch (e) {
      debugPrint('AlarmService: failed to stop alarm — $e');
    }
  }
}
