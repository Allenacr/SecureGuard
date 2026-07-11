import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../config/theme.dart';
import '../models/incident.dart';
import '../services/alarm_service.dart';
import '../services/database_service.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import '../widgets/countdown_timer.dart';

class AlertScreen extends StatefulWidget {
  final String incidentId;

  const AlertScreen({super.key, required this.incidentId});

  @override
  State<AlertScreen> createState() => _AlertScreenState();
}

class _AlertScreenState extends State<AlertScreen> {
  Incident? _incident;
  bool _isLoading = true;
  bool _isSending = false;
  bool _responded = false;
  String? _error;
  int _remainingSeconds = 60;
  int _totalTimeout = 60;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _loadIncident();
  }

  Future<void> _loadIncident() async {
    try {
      final incident = await DatabaseService.getIncident(widget.incidentId);
      if (mounted) {
        setState(() {
          _incident = incident;
          _isLoading = false;
        });

        if (incident != null && incident.isPending) {
          _startTimer();
        } else {
          setState(() => _responded = true);
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  void _startTimer() {
    // Fetch actual timeout from DB settings (Fix #10: not hardcoded)
    _totalTimeout = 60; // default fallback
    DatabaseService.getSettings().then((settings) {
      if (settings != null && mounted) {
        setState(() {
          _totalTimeout = settings.alertTimeoutSeconds;
        });
      }
    }).catchError((_) {});

    // Use UTC to avoid clock skew between PC and phone (Fix #4)
    final nowUtc = DateTime.now().toUtc();
    final createdAtUtc = _incident!.createdAt.toUtc();
    final elapsedSeconds = nowUtc.difference(createdAtUtc).inSeconds;
    
    _remainingSeconds = _totalTimeout - elapsedSeconds;

    // Clamp to at least 5 seconds so the user has a chance to respond
    if (_remainingSeconds < 5) {
      _remainingSeconds = 5;
    }

    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) {
        setState(() {
          _remainingSeconds--;
          if (_remainingSeconds <= 0) {
            _autoDeny();
          }
        });
      }
    });
  }

  Future<void> _respond(String decision) async {
    if (_isSending || _responded) return;

    setState(() => _isSending = true);

    try {
      // Stop the native alarm (ringtone + vibration + wake lock)
      await AlarmService.stop();

      // Also cancel any local notification sound loops
      await FlutterLocalNotificationsPlugin().cancelAll();
      
      await DatabaseService.respondToIncident(widget.incidentId, decision);
      _timer?.cancel();

      if (mounted) {
        setState(() {
          _isSending = false;
          _responded = true;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              decision == 'allow'
                  ? '✅ Access allowed — security questions shown'
                  : '🚫 Access denied — intruder photo captured',
            ),
            backgroundColor: decision == 'allow'
                ? AppTheme.accentGreen
                : AppTheme.accentRed,
          ),
        );

        // Pop back after delay
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) Navigator.pop(context);
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isSending = false;
          _error = 'Failed to send response. Tap to retry.';
        });
      }
    }
  }

  void _autoDeny() {
    _timer?.cancel();
    _respond('deny');
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null && _incident == null) {
      return Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 64, color: AppTheme.accentRed),
              const SizedBox(height: 16),
              Text('Error loading alert', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Text(_error!, style: const TextStyle(color: AppTheme.textSecondary)),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: _loadIncident,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    final incident = _incident!;
    final isUrgent = _remainingSeconds <= 10;

    return Scaffold(
      backgroundColor: isUrgent
          ? AppTheme.accentRed.withValues(alpha: 0.05)
          : Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const Spacer(),

              // Alert Icon
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: isUrgent
                        ? [AppTheme.accentRed, const Color(0xFFFF6B6B)]
                        : [AppTheme.accentAmber, const Color(0xFFFFD93D)],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: (isUrgent ? AppTheme.accentRed : AppTheme.accentAmber)
                          .withValues(alpha: 0.3),
                      blurRadius: 24,
                      spreadRadius: 4,
                    ),
                  ],
                ),
                child: Icon(
                  Icons.warning_amber_rounded,
                  size: 56,
                  color: Colors.white,
                ),
              ).animate(onPlay: (c) => c.repeat())
                  .shimmer(duration: 2000.ms, color: Colors.white24),

              const SizedBox(height: 32),

              // Alert Title
              Text(
                '⚠️ File Access Detected',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                textAlign: TextAlign.center,
              ).animate().fadeIn(duration: 400.ms),

              const SizedBox(height: 12),

              // File name
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                decoration: BoxDecoration(
                  color: AppTheme.accentRed.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.accentRed.withValues(alpha: 0.3)),
                ),
                child: Text(
                  incident.fileName,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.accentRed,
                  ),
                  textAlign: TextAlign.center,
                ),
              ).animate().fadeIn(delay: 100.ms, duration: 400.ms),

              const SizedBox(height: 32),

              // Countdown Timer
              if (!_responded)
                CountdownTimer(
                  totalSeconds: _totalTimeout,
                  remainingSeconds: _remainingSeconds,
                  isUrgent: isUrgent,
                ).animate().fadeIn(delay: 200.ms, duration: 400.ms),

              if (_responded)
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppTheme.accentGreen.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.check_circle, color: AppTheme.accentGreen),
                      const SizedBox(width: 8),
                      const Text(
                        'Response sent',
                        style: TextStyle(
                          color: AppTheme.accentGreen,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ).animate().fadeIn().scale(),

              const Spacer(),

              // Action Buttons
              if (!_responded) ...[
                // Allow Button
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton.icon(
                    onPressed: _isSending ? null : () => _respond('allow'),
                    icon: _isSending
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Icon(Icons.check_circle_outline, size: 24),
                    label: Text(_isSending ? 'Sending...' : 'Allow Access'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.accentGreen,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                      textStyle: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ).animate().fadeIn(delay: 300.ms, duration: 400.ms)
                    .slideY(begin: 0.2, end: 0),

                const SizedBox(height: 12),

                // Deny Button
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton.icon(
                    onPressed: _isSending ? null : () => _respond('deny'),
                    icon: const Icon(Icons.block_rounded, size: 24),
                    label: const Text('Deny Access'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.accentRed,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                      textStyle: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ).animate().fadeIn(delay: 400.ms, duration: 400.ms)
                    .slideY(begin: 0.2, end: 0),
              ],

              // Error retry
              if (_error != null && !_responded) ...[
                const SizedBox(height: 12),
                TextButton.icon(
                  onPressed: () {
                    setState(() => _error = null);
                  },
                  icon: const Icon(Icons.refresh, color: AppTheme.accentRed),
                  label: Text(_error!, style: const TextStyle(color: AppTheme.accentRed, fontSize: 12)),
                ),
              ],

              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    // Safety fallback: stop alarm if screen is disposed without responding
    AlarmService.stop();
    super.dispose();
  }
}
