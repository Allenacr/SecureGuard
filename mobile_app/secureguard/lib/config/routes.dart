import 'package:flutter/material.dart';
import '../screens/login_screen.dart';
import '../screens/home_screen.dart';
import '../screens/alert_screen.dart';
import '../screens/history_screen.dart';
import '../screens/statistics_screen.dart';
import '../screens/timeline_screen.dart';
import '../screens/notification_history_screen.dart';
import '../screens/protected_files_screen.dart';
import '../screens/settings_screen.dart';

class AppRoutes {
  static const String login = '/login';
  static const String home = '/home';
  static const String alert = '/alert';
  static const String history = '/history';
  static const String statistics = '/statistics';
  static const String timeline = '/timeline';
  static const String notificationHistory = '/notification-history';
  static const String protectedFiles = '/protected-files';
  static const String settings = '/settings';

  static Route<dynamic> generateRoute(RouteSettings routeSettings) {
    switch (routeSettings.name) {
      case login:
        return _fadeRoute(const LoginScreen(), routeSettings);
      case home:
        return _fadeRoute(const HomeScreen(), routeSettings);
      case alert:
        final args = routeSettings.arguments as Map<String, dynamic>?;
        return _slideRoute(
          AlertScreen(incidentId: args?['incident_id'] ?? ''),
          routeSettings,
        );
      case history:
        return _slideRoute(const HistoryScreen(), routeSettings);
      case statistics:
        return _slideRoute(const StatisticsScreen(), routeSettings);
      case timeline:
        return _slideRoute(const TimelineScreen(), routeSettings);
      case notificationHistory:
        return _slideRoute(const NotificationHistoryScreen(), routeSettings);
      case protectedFiles:
        return _slideRoute(const ProtectedFilesScreen(), routeSettings);
      case settings:
        return _slideRoute(const SettingsScreen(), routeSettings);
      default:
        return _fadeRoute(const LoginScreen(), routeSettings);
    }
  }

  static PageRouteBuilder _fadeRoute(Widget page, RouteSettings settings) {
    return PageRouteBuilder(
      settings: settings,
      pageBuilder: (context, animation, secondaryAnimation) => page,
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        return FadeTransition(opacity: animation, child: child);
      },
      transitionDuration: const Duration(milliseconds: 300),
    );
  }

  static PageRouteBuilder _slideRoute(Widget page, RouteSettings settings) {
    return PageRouteBuilder(
      settings: settings,
      pageBuilder: (context, animation, secondaryAnimation) => page,
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        const begin = Offset(1.0, 0.0);
        const end = Offset.zero;
        const curve = Curves.easeInOutCubic;
        var tween = Tween(begin: begin, end: end).chain(CurveTween(curve: curve));
        return SlideTransition(position: animation.drive(tween), child: child);
      },
      transitionDuration: const Duration(milliseconds: 350),
    );
  }
}
