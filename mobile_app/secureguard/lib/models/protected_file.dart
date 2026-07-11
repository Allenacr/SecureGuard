class ProtectedFile {
  final String id;
  final String userId;
  final String path;
  final String fileName;
  final String fileType; // 'file' or 'folder'
  final bool isBlocked;
  final bool isActive;
  final DateTime? blockedAt;
  final int attempts;
  final DateTime createdAt;

  ProtectedFile({
    required this.id,
    required this.userId,
    required this.path,
    required this.fileName,
    required this.fileType,
    this.isBlocked = false,
    this.isActive = true,
    this.blockedAt,
    this.attempts = 0,
    required this.createdAt,
  });

  factory ProtectedFile.fromJson(Map<String, dynamic> json) {
    return ProtectedFile(
      id: json['id'] ?? '',
      userId: json['user_id'] ?? '',
      path: json['path'] ?? '',
      fileName: json['file_name'] ?? '',
      fileType: json['file_type'] ?? 'file',
      isBlocked: json['is_blocked'] ?? false,
      isActive: json['is_active'] ?? true,
      blockedAt: json['blocked_at'] != null ? DateTime.parse(json['blocked_at']) : null,
      attempts: json['attempts'] ?? 0,
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toIso8601String()),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'path': path,
      'file_name': fileName,
      'file_type': fileType,
      'is_blocked': isBlocked,
      'is_active': isActive,
      'blocked_at': blockedAt?.toIso8601String(),
      'attempts': attempts,
    };
  }

  bool get isFolder => fileType == 'folder';
}
