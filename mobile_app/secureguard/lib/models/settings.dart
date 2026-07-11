class AppSettings {
  final String id;
  final String userId;
  final bool protectionEnabled;
  final String secretKeyword;
  final int alertTimeoutSeconds;
  final int maxAttempts;
  final List<Map<String, String>> questions;
  final String notificationSound;
  final bool darkMode;

  AppSettings({
    required this.id,
    required this.userId,
    this.protectionEnabled = true,
    this.secretKeyword = 'opensecureguard',
    this.alertTimeoutSeconds = 60,
    this.maxAttempts = 3,
    this.questions = const [],
    this.notificationSound = 'default',
    this.darkMode = false,
  });

  factory AppSettings.fromJson(Map<String, dynamic> json) {
    List<Map<String, String>> parseQuestions(dynamic q) {
      if (q is List) {
        return q.map((item) {
          if (item is Map) {
            return {
              'question': (item['question'] ?? '').toString(),
              'answer': (item['answer'] ?? '').toString(),
            };
          }
          return <String, String>{};
        }).toList();
      }
      return [];
    }

    return AppSettings(
      id: json['id'] ?? '',
      userId: json['user_id'] ?? '',
      protectionEnabled: json['protection_enabled'] ?? true,
      secretKeyword: json['secret_keyword'] ?? 'opensecureguard',
      alertTimeoutSeconds: json['alert_timeout_seconds'] ?? 60,
      maxAttempts: json['max_attempts'] ?? 3,
      questions: parseQuestions(json['questions']),
      notificationSound: json['notification_sound'] ?? 'default',
      darkMode: json['dark_mode'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'protection_enabled': protectionEnabled,
      'secret_keyword': secretKeyword,
      'alert_timeout_seconds': alertTimeoutSeconds,
      'max_attempts': maxAttempts,
      'questions': questions,
      'notification_sound': notificationSound,
      'dark_mode': darkMode,
    };
  }

  AppSettings copyWith({
    bool? protectionEnabled,
    String? secretKeyword,
    int? alertTimeoutSeconds,
    int? maxAttempts,
    List<Map<String, String>>? questions,
    String? notificationSound,
    bool? darkMode,
  }) {
    return AppSettings(
      id: id,
      userId: userId,
      protectionEnabled: protectionEnabled ?? this.protectionEnabled,
      secretKeyword: secretKeyword ?? this.secretKeyword,
      alertTimeoutSeconds: alertTimeoutSeconds ?? this.alertTimeoutSeconds,
      maxAttempts: maxAttempts ?? this.maxAttempts,
      questions: questions ?? this.questions,
      notificationSound: notificationSound ?? this.notificationSound,
      darkMode: darkMode ?? this.darkMode,
    );
  }
}
