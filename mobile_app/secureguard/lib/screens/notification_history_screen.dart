import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:intl/intl.dart';

import '../config/theme.dart';
import '../models/notification_item.dart';
import '../services/database_service.dart';

class NotificationHistoryScreen extends StatefulWidget {
  const NotificationHistoryScreen({super.key});

  @override
  State<NotificationHistoryScreen> createState() => _NotificationHistoryScreenState();
}

class _NotificationHistoryScreenState extends State<NotificationHistoryScreen> {
  List<NotificationItem> _notifications = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      _notifications = await DatabaseService.getNotificationHistory();
      setState(() => _isLoading = false);
    } catch (e) {
      setState(() { _error = e.toString(); _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notification History'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline, size: 48, color: AppTheme.accentRed),
                      const SizedBox(height: 16),
                      ElevatedButton(onPressed: _load, child: const Text('Retry')),
                    ],
                  ),
                )
              : _notifications.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.notifications_none_rounded, size: 64, color: AppTheme.textMuted.withValues(alpha: 0.5)),
                          const SizedBox(height: 16),
                          const Text('No notifications yet', style: TextStyle(color: AppTheme.textSecondary)),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _notifications.length,
                        itemBuilder: (context, index) {
                          final notif = _notifications[index];
                          return _buildNotificationTile(notif, index);
                        },
                      ),
                    ),
    );
  }

  Widget _buildNotificationTile(NotificationItem notif, int index) {
    final timeStr = DateFormat('dd MMM, hh:mm a').format(notif.sentAt.toLocal());
    final isRepeat = notif.notificationType == 'repeat';

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: (isRepeat ? AppTheme.accentAmber : AppTheme.accentRed).withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(
            isRepeat ? Icons.repeat_rounded : Icons.notifications_active_rounded,
            color: isRepeat ? AppTheme.accentAmber : AppTheme.accentRed,
            size: 22,
          ),
        ),
        title: Text(
          notif.title,
          style: TextStyle(
            fontWeight: notif.read ? FontWeight.normal : FontWeight.bold,
            fontSize: 14,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Text(notif.body, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
            const SizedBox(height: 4),
            Text(timeStr, style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
          ],
        ),
        trailing: notif.read
            ? null
            : Container(
                width: 8, height: 8,
                decoration: const BoxDecoration(color: AppTheme.primaryBlue, shape: BoxShape.circle),
              ),
        onTap: () {
          if (!notif.read) {
            DatabaseService.markNotificationRead(notif.id);
            setState(() {}); // Optimistic update
          }
          if (notif.incidentId != null) {
            Navigator.pushNamed(context, '/history');
          }
        },
      ),
    ).animate().fadeIn(delay: (index * 50).ms, duration: 300.ms);
  }
}
