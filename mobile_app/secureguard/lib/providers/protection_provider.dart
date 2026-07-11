import 'package:flutter/material.dart';
import '../models/protected_file.dart';
import '../services/database_service.dart';

class ProtectionProvider extends ChangeNotifier {
  List<ProtectedFile> _files = [];
  bool _isLoading = false;
  bool _protectionEnabled = true;
  bool _isPcOnline = false;
  String? _error;

  List<ProtectedFile> get files => _files;
  bool get isLoading => _isLoading;
  bool get protectionEnabled => _protectionEnabled;
  bool get isPcOnline => _isPcOnline;
  String? get error => _error;

  Future<void> loadProtectedFiles() async {
    _isLoading = true;
    notifyListeners();

    try {
      _files = await DatabaseService.getProtectedFiles();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> checkPcStatus() async {
    try {
      _isPcOnline = await DatabaseService.isPcOnline();
      notifyListeners();
    } catch (e) {
      _isPcOnline = false;
      notifyListeners();
    }
  }

  Future<void> loadProtectionStatus() async {
    try {
      final settings = await DatabaseService.getSettings();
      if (settings != null) {
        _protectionEnabled = settings.protectionEnabled;
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Error loading protection status: $e');
    }
  }

  Future<bool> toggleProtection(bool enable) async {
    try {
      await DatabaseService.updateSettings({'protection_enabled': enable});
      _protectionEnabled = enable;
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  /// Feature 15: Panic button — disable all protection
  Future<bool> panicDisable() async {
    return toggleProtection(false);
  }

  /// Feature 5: Add file from phone
  Future<bool> addProtectedFile(String path, String fileName, String fileType) async {
    try {
      await DatabaseService.addProtectedFile(path, fileName, fileType);
      await loadProtectedFiles();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  /// Feature 6: Block/unblock from phone
  Future<bool> toggleBlockFile(String id, bool block) async {
    try {
      await DatabaseService.toggleBlockFile(id, block);
      await loadProtectedFiles();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> removeProtectedFile(String id) async {
    try {
      await DatabaseService.removeProtectedFile(id);
      await loadProtectedFiles();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
