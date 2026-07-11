class NotificationItem {
  final String id;
  final String userId;
  final String? incidentId;
  final String title;
  final String body;
  final DateTime sentAt;
  final bool read;
  final String notificationType; // alert, repeat, system

  NotificationItem({
    required this.id,
    required this.userId,
    this.incidentId,
    required this.title,
    required this.body,
    required this.sentAt,
    this.read = false,
    this.notificationType = 'alert',
  });

  factory NotificationItem.fromJson(Map<String, dynamic> json) {
    return NotificationItem(
      id: json['id'] ?? '',
      userId: json['user_id'] ?? '',
      incidentId: json['incident_id'],
      title: json['title'] ?? '',
      body: json['body'] ?? '',
      sentAt: DateTime.parse(json['sent_at'] ?? DateTime.now().toIso8601String()),
      read: json['read'] ?? false,
      notificationType: json['notification_type'] ?? 'alert',
    );
  }
}
