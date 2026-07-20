import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../config/theme.dart';
import '../providers/auth_provider.dart';
import '../providers/incidents_provider.dart';
import '../providers/protection_provider.dart';
import '../providers/settings_provider.dart';
import '../services/notification_service.dart';
import '../widgets/shield_status.dart';
import '../widgets/incident_card.dart';
import '../widgets/panic_button.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Timer? _heartbeatTimer;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    final incidents = context.read<IncidentsProvider>();
    final protection = context.read<ProtectionProvider>();
    final settings = context.read<SettingsProvider>();

    incidents.loadRecentIncidents();
    incidents.setupRealtimeSubscription();
    protection.loadProtectionStatus();
    protection.checkPcStatus();
    settings.loadSettings();

    // Set up notification handler
    NotificationService.onAlertReceived = (incidentId) {
      if (mounted) {
        Navigator.pushNamed(context, '/alert', arguments: {'incident_id': incidentId});
      }
    };

    // Periodic PC status check
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      protection.checkPcStatus();
    });
  }

  Future<void> _refresh() async {
    final incidents = context.read<IncidentsProvider>();
    final protection = context.read<ProtectionProvider>();
    await incidents.loadRecentIncidents();
    await protection.checkPcStatus();
    await protection.loadProtectionStatus();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.shield_rounded, color: AppTheme.primaryBlue, size: 24),
            const SizedBox(width: 8),
            const Text('SecureGuard'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.history_rounded),
            tooltip: 'History',
            onPressed: () => Navigator.pushNamed(context, '/history'),
          ),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert_rounded),
            onSelected: (value) {
              switch (value) {
                case 'statistics':
                  Navigator.pushNamed(context, '/statistics');
                  break;
                case 'timeline':
                  Navigator.pushNamed(context, '/timeline');
                  break;
                case 'notifications':
                  Navigator.pushNamed(context, '/notification-history');
                  break;
                case 'files':
                  Navigator.pushNamed(context, '/protected-files');
                  break;
                case 'settings':
                  Navigator.pushNamed(context, '/settings');
                  break;
                case 'logout':
                  _logout();
                  break;
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'statistics', child: ListTile(leading: Icon(Icons.bar_chart_rounded), title: Text('Statistics'), dense: true, contentPadding: EdgeInsets.zero)),
              const PopupMenuItem(value: 'timeline', child: ListTile(leading: Icon(Icons.timeline_rounded), title: Text('Timeline'), dense: true, contentPadding: EdgeInsets.zero)),
              const PopupMenuItem(value: 'notifications', child: ListTile(leading: Icon(Icons.notifications_rounded), title: Text('Notifications'), dense: true, contentPadding: EdgeInsets.zero)),
              const PopupMenuItem(value: 'files', child: ListTile(leading: Icon(Icons.folder_rounded), title: Text('Protected Files'), dense: true, contentPadding: EdgeInsets.zero)),
              const PopupMenuItem(value: 'settings', child: ListTile(leading: Icon(Icons.settings_rounded), title: Text('Settings'), dense: true, contentPadding: EdgeInsets.zero)),
              const PopupMenuDivider(),
              const PopupMenuItem(value: 'logout', child: ListTile(leading: Icon(Icons.logout_rounded, color: AppTheme.accentRed), title: Text('Logout', style: TextStyle(color: AppTheme.accentRed)), dense: true, contentPadding: EdgeInsets.zero)),
            ],
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Protection Status Card
              Consumer<ProtectionProvider>(
                builder: (context, protection, child) {
                  return ShieldStatus(
                    isEnabled: protection.protectionEnabled,
                    isPcOnline: protection.isPcOnline,
                    onToggle: (value) => protection.toggleProtection(value),
                  );
                },
              ).animate().fadeIn(duration: 500.ms).slideY(begin: 0.1, end: 0),

              const SizedBox(height: 16),

              // Panic Button (Feature 15)
              Consumer<ProtectionProvider>(
                builder: (context, protection, child) {
                  if (!protection.protectionEnabled) return const SizedBox();
                  return const PanicButton();
                },
              ).animate().fadeIn(delay: 100.ms, duration: 500.ms),

              const SizedBox(height: 24),

              // Recent Alerts
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Recent Alerts',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  TextButton(
                    onPressed: () => Navigator.pushNamed(context, '/history'),
                    child: const Text('View All'),
                  ),
                ],
              ),

              const SizedBox(height: 8),

              Consumer<IncidentsProvider>(
                builder: (context, incidents, child) {
                  if (incidents.recentIncidents.isEmpty) {
                    return Container(
                      padding: const EdgeInsets.all(32),
                      decoration: BoxDecoration(
                        color: Theme.of(context).cardTheme.color,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: Theme.of(context).dividerColor,
                        ),
                      ),
                      child: Center(
                        child: Column(
                          children: [
                            Icon(
                              Icons.check_circle_outline_rounded,
                              size: 48,
                              color: AppTheme.accentGreen.withValues(alpha: 0.5),
                            ),
                            const SizedBox(height: 12),
                            const Text(
                              'No recent alerts',
                              style: TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 14,
                              ),
                            ),
                            const SizedBox(height: 4),
                            const Text(
                              'Your files are safe',
                              style: TextStyle(
                                color: AppTheme.textMuted,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ).animate().fadeIn(delay: 200.ms, duration: 500.ms);
                  }

                  return Column(
                    children: incidents.recentIncidents.asMap().entries.map((entry) {
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: IncidentCard(
                          incident: entry.value,
                          onTap: () => Navigator.pushNamed(context, '/history'),
                        ),
                      ).animate()
                          .fadeIn(delay: (200 + entry.key * 100).ms, duration: 400.ms)
                          .slideX(begin: 0.05, end: 0);
                    }).toList(),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _logout() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Logout'),
        content: const Text('Are you sure you want to logout?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              context.read<AuthProvider>().logout();
              Navigator.pushReplacementNamed(context, '/login');
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accentRed),
            child: const Text('Logout'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _heartbeatTimer?.cancel();
    super.dispose();
  }
}
