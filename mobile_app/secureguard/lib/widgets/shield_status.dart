import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../config/theme.dart';

class ShieldStatus extends StatelessWidget {
  final bool isEnabled;
  final bool isPcOnline;
  final Function(bool) onToggle;

  const ShieldStatus({
    super.key,
    required this.isEnabled,
    required this.isPcOnline,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: isEnabled
              ? [AppTheme.accentGreen.withValues(alpha: 0.1), AppTheme.accentGreen.withValues(alpha: 0.05)]
              : [AppTheme.accentRed.withValues(alpha: 0.1), AppTheme.accentRed.withValues(alpha: 0.05)],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: (isEnabled ? AppTheme.accentGreen : AppTheme.accentRed).withValues(alpha: 0.2),
        ),
      ),
      child: Column(
        children: [
          // Shield icon
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: (isEnabled ? AppTheme.accentGreen : AppTheme.accentRed).withValues(alpha: 0.15),
            ),
            child: Icon(
              Icons.shield_rounded,
              size: 48,
              color: isEnabled ? AppTheme.accentGreen : AppTheme.accentRed,
            ),
          ).animate(onPlay: (c) => c.repeat(reverse: true))
              .scale(begin: const Offset(1, 1), end: const Offset(1.05, 1.05), duration: 2000.ms),
          const SizedBox(height: 12),

          Text(
            isEnabled ? 'Protection Active' : 'Protection Disabled',
            style: TextStyle(
              fontSize: 18, fontWeight: FontWeight.bold,
              color: isEnabled ? AppTheme.accentGreen : AppTheme.accentRed,
            ),
          ),

          const SizedBox(height: 4),

          // PC Status (Feature 8)
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 8, height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isPcOnline ? AppTheme.accentGreen : AppTheme.textMuted,
                ),
              ),
              const SizedBox(width: 6),
              Text(
                isPcOnline ? 'PC Online' : 'PC Offline',
                style: TextStyle(
                  fontSize: 12,
                  color: isPcOnline ? AppTheme.accentGreen : AppTheme.textMuted,
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Toggle
          Switch.adaptive(
            value: isEnabled,
            onChanged: onToggle,
            activeColor: AppTheme.accentGreen,
            inactiveTrackColor: AppTheme.accentRed.withValues(alpha: 0.3),
          ),
        ],
      ),
    );
  }
}
