class Incident {
  final String id;
  final String userId;
  final String filePath;
  final String fileName;
  final String action;         // PENDING, ALLOWED, DENIED, AUTO_DENIED, BLOCKED
  final String? ownerDecision; // allow, deny, null
  final String? photoUrl;
  final String? photoPath;
  final String? pcName;
  final DateTime createdAt;
  final DateTime? respondedAt;
  final bool autoDenied;
  final bool? answersCorrect;

  Incident({
    required this.id,
    required this.userId,
    required this.filePath,
    required this.fileName,
    required this.action,
    this.ownerDecision,
    this.photoUrl,
    this.photoPath,
    this.pcName,
    required this.createdAt,
    this.respondedAt,
    this.autoDenied = false,
    this.answersCorrect,
  });

  factory Incident.fromJson(Map<String, dynamic> json) {
    return Incident(
      id: json['id'] ?? '',
      userId: json['user_id'] ?? '',
      filePath: json['file_path'] ?? '',
      fileName: json['file_name'] ?? '',
      action: json['action'] ?? 'PENDING',
      ownerDecision: json['owner_decision'],
      photoUrl: json['photo_url'],
      photoPath: json['photo_path'],
      pcName: json['pc_name'],
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toIso8601String()),
      respondedAt: json['responded_at'] != null ? DateTime.parse(json['responded_at']) : null,
      autoDenied: json['auto_denied'] ?? false,
      answersCorrect: json['answers_correct'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'file_path': filePath,
      'file_name': fileName,
      'action': action,
      'owner_decision': ownerDecision,
      'photo_url': photoUrl,
      'photo_path': photoPath,
      'pc_name': pcName,
      'created_at': createdAt.toIso8601String(),
      'responded_at': respondedAt?.toIso8601String(),
      'auto_denied': autoDenied,
      'answers_correct': answersCorrect,
    };
  }

  bool get isPending => action == 'PENDING';
  bool get isAllowed => action == 'ALLOWED';
  bool get isDenied => action == 'DENIED' || action == 'AUTO_DENIED';
  bool get isBlocked => action == 'BLOCKED';
  bool get hasPhoto => photoUrl != null && photoUrl!.isNotEmpty;
}
