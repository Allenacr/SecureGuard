import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/incident.dart';
import '../models/protected_file.dart';
import '../models/notification_item.dart';
import '../models/settings.dart';

/// Database service for all Supabase queries.
class DatabaseService {
  static final _supabase = Supabase.instance.client;

  static String? get _userId => _supabase.auth.currentUser?.id;

  // ============================================================
  // INCIDENTS
  // ============================================================

  /// Fetch all incidents ordered by newest first
  static Future<List<Incident>> getIncidents() async {
    final data = await _supabase
        .from('incidents')
        .select()
        .eq('user_id', _userId!)
        .order('created_at', ascending: false)
        .limit(100);
    return (data as List).map((e) => Incident.fromJson(e)).toList();
  }

  /// Fetch completed incidents (non-pending)
  static Future<List<Incident>> getCompletedIncidents({int limit = 5}) async {
    final data = await _supabase
        .from('incidents')
        .select()
        .eq('user_id', _userId!)
        .neq('action', 'PENDING')
        .order('created_at', ascending: false)
        .limit(limit);
    return (data as List).map((e) => Incident.fromJson(e)).toList();
  }

  /// Get a single incident
  static Future<Incident?> getIncident(String id) async {
    try {
      final data = await _supabase
          .from('incidents')
          .select()
          .eq('id', id)
          .single();
      return Incident.fromJson(data);
    } catch (e) {
      debugPrint('Error fetching incident: $e');
      return null;
    }
  }

  /// Update incident (owner decision)
  static Future<void> updateIncident(String id, Map<String, dynamic> updates) async {
    await _supabase.from('incidents').update(updates).eq('id', id);
  }

  /// Respond to an incident (allow/deny)
  static Future<void> respondToIncident(String id, String decision) async {
    await _supabase.from('incidents').update({
      'owner_decision': decision,
      'action': decision == 'allow' ? 'ALLOWED' : 'DENIED',
      'responded_at': DateTime.now().toUtc().toIso8601String(),
    }).eq('id', id);
  }

  /// Delete a single incident
  static Future<void> deleteIncident(String id) async {
    await _supabase.from('incidents').delete().eq('id', id);
  }

  /// Delete all incidents
  static Future<void> deleteAllIncidents() async {
    await _supabase.from('incidents').delete().eq('user_id', _userId!);
  }

  /// Subscribe to realtime incidents
  static RealtimeChannel subscribeToIncidents(Function(dynamic) callback) {
    return _supabase
        .channel('incidents_realtime')
        .onPostgresChanges(
          event: PostgresChangeEvent.all,
          schema: 'public',
          table: 'incidents',
          filter: PostgresChangeFilter(
            type: PostgresChangeFilterType.eq,
            column: 'user_id',
            value: _userId!,
          ),
          callback: (payload) => callback(payload),
        )
        .subscribe();
  }

  // ============================================================
  // SETTINGS
  // ============================================================

  /// Get user settings
  static Future<AppSettings?> getSettings() async {
    try {
      final data = await _supabase
          .from('settings')
          .select()
          .eq('user_id', _userId!)
          .single();
      return AppSettings.fromJson(data);
    } catch (e) {
      debugPrint('Error fetching settings: $e');
      return null;
    }
  }

  /// Update settings
  static Future<void> updateSettings(Map<String, dynamic> updates) async {
    await _supabase.from('settings').update(updates).eq('user_id', _userId!);
  }

  // ============================================================
  // PROTECTED FILES (Features 4, 5, 6)
  // ============================================================

  /// Get all protected files
  static Future<List<ProtectedFile>> getProtectedFiles() async {
    final data = await _supabase
        .from('protected_files')
        .select()
        .eq('user_id', _userId!)
        .eq('is_active', true)
        .order('created_at', ascending: false);
    return (data as List).map((e) => ProtectedFile.fromJson(e)).toList();
  }

  /// Add a protected file (Feature 5)
  static Future<void> addProtectedFile(String path, String fileName, String fileType) async {
    await _supabase.from('protected_files').insert({
      'user_id': _userId,
      'path': path,
      'file_name': fileName,
      'file_type': fileType,
      'is_blocked': false,
      'is_active': true,
    });
  }

  /// Remove a protected file
  static Future<void> removeProtectedFile(String id) async {
    await _supabase.from('protected_files').update({
      'is_active': false,
    }).eq('id', id);
  }

  /// Block/unblock a file (Feature 6)
  static Future<void> toggleBlockFile(String id, bool block) async {
    await _supabase.from('protected_files').update({
      'is_blocked': block,
      'blocked_at': block ? DateTime.now().toUtc().toIso8601String() : null,
      if (!block) 'attempts': 0,
    }).eq('id', id);
  }

  // ============================================================
  // NOTIFICATION HISTORY (Feature 1)
  // ============================================================

  static Future<List<NotificationItem>> getNotificationHistory() async {
    final data = await _supabase
        .from('notification_history')
        .select()
        .eq('user_id', _userId!)
        .order('sent_at', ascending: false)
        .limit(100);
    return (data as List).map((e) => NotificationItem.fromJson(e)).toList();
  }

  static Future<void> markNotificationRead(String id) async {
    await _supabase.from('notification_history').update({'read': true}).eq('id', id);
  }

  // ============================================================
  // HEARTBEAT (Feature 8)
  // ============================================================

  static Future<DateTime?> getLastHeartbeat() async {
    try {
      final data = await _supabase
          .from('heartbeat')
          .select('last_ping')
          .eq('user_id', _userId!)
          .single();
      return DateTime.parse(data['last_ping']);
    } catch (e) {
      return null;
    }
  }

  static Future<bool> isPcOnline() async {
    final lastPing = await getLastHeartbeat();
    if (lastPing == null) return false;
    // Consider online if heartbeat within last 60 seconds
    return DateTime.now().toUtc().difference(lastPing).inSeconds < 60;
  }

  // ============================================================
  // DEVICE TOKENS
  // ============================================================

  static Future<void> saveDeviceToken(String token) async {
    try {
      await _supabase.from('device_tokens').upsert({
        'user_id': _userId,
        'fcm_token': token,
        'device_type': 'android',
        'is_active': true,
        'updated_at': DateTime.now().toUtc().toIso8601String(),
      }, onConflict: 'user_id,fcm_token');
    } catch (e) {
      debugPrint('Error saving device token: $e');
    }
  }

  // ============================================================
  // STATISTICS (Feature 7)
  // ============================================================

  static Future<Map<String, dynamic>> getStatistics() async {
    final incidents = await getIncidents();

    int totalIncidents = incidents.length;
    int totalDenied = incidents.where((i) => i.isDenied).length;
    int totalAllowed = incidents.where((i) => i.isAllowed).length;
    int totalBlocked = incidents.where((i) => i.isBlocked).length;

    // Most targeted file
    Map<String, int> fileCounts = {};
    for (var i in incidents) {
      fileCounts[i.fileName] = (fileCounts[i.fileName] ?? 0) + 1;
    }
    String? mostTargeted;
    int maxCount = 0;
    fileCounts.forEach((name, count) {
      if (count > maxCount) {
        maxCount = count;
        mostTargeted = name;
      }
    });

    // Most active day
    Map<String, int> dayCounts = {};
    for (var i in incidents) {
      String day = '${i.createdAt.year}-${i.createdAt.month.toString().padLeft(2, '0')}-${i.createdAt.day.toString().padLeft(2, '0')}';
      dayCounts[day] = (dayCounts[day] ?? 0) + 1;
    }
    String? activeDay;
    int maxDayCount = 0;
    dayCounts.forEach((day, count) {
      if (count > maxDayCount) {
        maxDayCount = count;
        activeDay = day;
      }
    });

    // Success rate (allowed / total)
    double successRate = totalIncidents > 0
        ? (totalAllowed / totalIncidents) * 100
        : 0;

    // Hourly distribution (Feature 9)
    List<int> hourly = List.filled(24, 0);
    for (var i in incidents) {
      hourly[i.createdAt.toLocal().hour]++;
    }

    // Weekly distribution
    List<int> weekly = List.filled(7, 0);
    for (var i in incidents) {
      weekly[i.createdAt.toLocal().weekday - 1]++;
    }

    return {
      'total_incidents': totalIncidents,
      'total_denied': totalDenied,
      'total_allowed': totalAllowed,
      'total_blocked': totalBlocked,
      'most_targeted_file': mostTargeted ?? 'N/A',
      'most_targeted_count': maxCount,
      'most_active_day': activeDay ?? 'N/A',
      'most_active_day_count': maxDayCount,
      'success_rate': successRate,
      'hourly_distribution': hourly,
      'weekly_distribution': weekly,
    };
  }

  // ============================================================
  // OWNER ACCOUNTS (Feature 16)
  // ============================================================

  static Future<List<Map<String, dynamic>>> getOwnerAccounts() async {
    final data = await _supabase
        .from('owner_accounts')
        .select('*, member:member_user_id(email)')
        .eq('primary_user_id', _userId!);
    return List<Map<String, dynamic>>.from(data);
  }

  static Future<void> addOwnerAccount(String memberEmail) async {
    // Look up user by email
    final users = await _supabase
        .from('profiles')
        .select('id')
        .eq('email', memberEmail)
        .limit(1);

    if (users.isEmpty) throw Exception('User not found');

    await _supabase.from('owner_accounts').insert({
      'primary_user_id': _userId,
      'member_user_id': users[0]['id'],
      'role': 'member',
      'can_respond': true,
    });
  }

  static Future<void> removeOwnerAccount(String id) async {
    await _supabase.from('owner_accounts').delete().eq('id', id);
  }

  // ============================================================
  // LOGIN ATTEMPTS (Feature 14)
  // ============================================================

  static Future<void> verifyPassword(String password) async {
    final email = _supabase.auth.currentUser?.email;
    if (email == null) throw Exception('Not logged in');

    await _supabase.auth.signInWithPassword(
      email: email,
      password: password,
    );
  }
}
