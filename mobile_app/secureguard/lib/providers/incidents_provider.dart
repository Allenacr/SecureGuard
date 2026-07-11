import 'package:flutter/material.dart';
import '../models/incident.dart';
import '../services/database_service.dart';

class IncidentsProvider extends ChangeNotifier {
  List<Incident> _incidents = [];
  List<Incident> _recentIncidents = [];
  bool _isLoading = false;
  String? _error;
  Map<String, dynamic> _statistics = {};

  List<Incident> get incidents => _incidents;
  List<Incident> get recentIncidents => _recentIncidents;
  bool get isLoading => _isLoading;
  String? get error => _error;
  Map<String, dynamic> get statistics => _statistics;

  Future<void> loadIncidents() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _incidents = await DatabaseService.getIncidents();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> loadRecentIncidents() async {
    try {
      _recentIncidents = await DatabaseService.getCompletedIncidents(limit: 5);
      notifyListeners();
    } catch (e) {
      debugPrint('Error loading recent incidents: $e');
    }
  }

  Future<void> loadStatistics() async {
    _isLoading = true;
    notifyListeners();

    try {
      _statistics = await DatabaseService.getStatistics();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> respondToIncident(String id, String decision) async {
    try {
      await DatabaseService.respondToIncident(id, decision);
      await loadRecentIncidents();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> deleteIncident(String id, String password) async {
    try {
      await DatabaseService.verifyPassword(password);
      await DatabaseService.deleteIncident(id);
      _incidents.removeWhere((i) => i.id == id);
      notifyListeners();
      return true;
    } catch (e) {
      _error = 'Wrong password';
      notifyListeners();
      return false;
    }
  }

  Future<bool> deleteAllIncidents(String password) async {
    try {
      await DatabaseService.verifyPassword(password);
      await DatabaseService.deleteAllIncidents();
      _incidents.clear();
      notifyListeners();
      return true;
    } catch (e) {
      _error = 'Wrong password';
      notifyListeners();
      return false;
    }
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  void setupRealtimeSubscription() {
    DatabaseService.subscribeToIncidents((payload) {
      loadRecentIncidents();
    });
  }
}
