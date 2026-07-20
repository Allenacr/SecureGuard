import 'package:flutter/foundation.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'alarm_service.dart';
import 'database_service.dart';

/// Notification service for FCM and local notifications.
/// Features 1, 2, 3: Notification history, custom alarm, repeat notifications.
class NotificationService {
  static final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  static final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  static Function(String incidentId)? onAlertReceived;

  /// Initialize notification service
  static Future<void> initialize() async {
    // Request permissions
    await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      criticalAlert: true,
    );

    // Configure local notifications
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidSettings);

    await _localNotifications.initialize(
      initSettings,
      onDidReceiveNotificationResponse: _onNotificationTap,
    );

    // Create notification channel with custom sound (Feature 2)
    const alertChannel = AndroidNotificationChannel(
      'secureguard_alerts',
      'SecureGuard Alerts',
      description: 'High priority alerts for file access',
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
      enableLights: true,
    );

    await _localNotifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(alertChannel);

    // Get and save FCM token
    final token = await _messaging.getToken();
    if (token != null) {
      debugPrint('FCM Token: $token');
      await DatabaseService.saveDeviceToken(token);
    }

    // Token refresh handler
    _messaging.onTokenRefresh.listen((newToken) {
      debugPrint('FCM Token refreshed: $newToken');
      DatabaseService.saveDeviceToken(newToken);
    });

    // Foreground messages
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

    // Background/terminated - when user taps notification
    FirebaseMessaging.onMessageOpenedApp.listen(_handleMessageOpenedApp);

    // Check initial message (app opened from terminated state via FCM)
    final initialMessage = await _messaging.getInitialMessage();
    if (initialMessage != null) {
      _handleMessageOpenedApp(initialMessage);
    }
    
    // Check initial message (app opened from terminated state via Local Notification)
    final NotificationAppLaunchDetails? launchDetails = 
          await _localNotifications.getNotificationAppLaunchDetails();
    if (launchDetails?.didNotificationLaunchApp ?? false) {
      final payload = launchDetails!.notificationResponse?.payload;
      if (payload != null && payload.isNotEmpty) {
        // Delay slightly giving UI time to render
        Future.delayed(const Duration(milliseconds: 500), () {
            onAlertReceived?.call(payload);
        });
      }
    }
  }

  /// Handle foreground messages
  static void _handleForegroundMessage(RemoteMessage message) {
    debugPrint('Foreground message: ${message.data}');

    final incidentId = message.data['incident_id'] ?? '';

    // Ignore empty incident IDs
    if (incidentId.isEmpty) return;

    // START THE ALARM — wake screen, ring like a phone call, vibrate
    AlarmService.start();

    // Show local notification using data payload since notification block is gone
    _showLocalNotification(
      title: message.data['title'] ?? '🚨 SecureGuard Alert',
      body: message.data['body'] ?? 'Someone is accessing a protected file',
      payload: incidentId,
    );

    // Trigger alert screen
    onAlertReceived?.call(incidentId);
  }

  /// Handle when user taps on notification
  static void _handleMessageOpenedApp(RemoteMessage message) {
    debugPrint('Message opened: ${message.data}');

    final incidentId = message.data['incident_id'] ?? '';
    if (incidentId.isEmpty) return;

    onAlertReceived?.call(incidentId);
  }

  /// Handle notification tap on local notification
  static void _onNotificationTap(NotificationResponse response) {
    final incidentId = response.payload ?? '';
    if (incidentId.isEmpty) return;

    onAlertReceived?.call(incidentId);
  }

  /// Show a local notification
  static Future<void> _showLocalNotification({
    required String title,
    required String body,
    String? payload,
  }) async {
    final details = NotificationDetails(
      android: AndroidNotificationDetails(
        'secureguard_alerts',
        'SecureGuard Alerts',
        channelDescription: 'High priority alerts',
        importance: Importance.max,
        priority: Priority.max,
        playSound: true,
        enableVibration: true,
        fullScreenIntent: true,
        category: AndroidNotificationCategory.alarm,
        additionalFlags: Int32List.fromList(<int>[4]), // FLAG_INSISTENT continuously loops sound!
      ),
    );

    await _localNotifications.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title,
      body,
      details,
      payload: payload,
    );
  }

  /// Get FCM token
  static Future<String?> getToken() => _messaging.getToken();
}
