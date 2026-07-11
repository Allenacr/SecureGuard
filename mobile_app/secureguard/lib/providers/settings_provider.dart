import 'package:flutter/material.dart';
import '../models/settings.dart';
import '../services/database_service.dart';

class SettingsProvider extends ChangeNotifier {
  AppSettings? _settings;
  bool _isLoading = false;
  String? _error;
  bool _isDarkMode = false;

  AppSettings? get settings => _settings;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isDarkMode => _isDarkMode;

  Future<void> loadSettings() async {
    _isLoading = true;
    notifyListeners();

    try {
      _settings = await DatabaseService.getSettings();
      if (_settings != null) {
        _isDarkMode = _settings!.darkMode;
      }
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> updateSettings(Map<String, dynamic> updates) async {
    try {
      await DatabaseService.updateSettings(updates);
      await loadSettings();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> updateQuestions(List<Map<String, String>> questions) async {
    return updateSettings({'questions': questions});
  }

  Future<bool> updateKeyword(String keyword) async {
    return updateSettings({'secret_keyword': keyword});
  }

  Future<bool> updateTimeout(int seconds) async {
    return updateSettings({'alert_timeout_seconds': seconds});
  }

  void toggleDarkMode() {
    _isDarkMode = !_isDarkMode;
    updateSettings({'dark_mode': _isDarkMode});
    notifyListeners();
  }

  Future<bool> updateNotificationSound(String sound) async {
    return updateSettings({'notification_sound': sound});
  }
}
