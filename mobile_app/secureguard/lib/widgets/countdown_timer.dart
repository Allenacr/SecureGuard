import 'package:flutter/material.dart';
import '../config/theme.dart';

class CountdownTimer extends StatelessWidget {
  final int totalSeconds;
  final int remainingSeconds;
  final bool isUrgent;

  const CountdownTimer({
    super.key,
    required this.totalSeconds,
    required this.remainingSeconds,
    required this.isUrgent,
  });

  @override
  Widget build(BuildContext context) {
    final progress = remainingSeconds / totalSeconds;
    final color = isUrgent ? AppTheme.accentRed : AppTheme.primaryBlue;

    return Column(
      children: [
        SizedBox(
          width: 120, height: 120,
          child: Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 120, height: 120,
                child: CircularProgressIndicator(
                  value: progress,
                  strokeWidth: 8,
                  backgroundColor: color.withValues(alpha: 0.15),
                  valueColor: AlwaysStoppedAnimation<Color>(color),
                  strokeCap: StrokeCap.round,
                ),
              ),
              Text(
                '$remainingSeconds',
                style: TextStyle(
                  fontSize: 36, fontWeight: FontWeight.bold, color: color,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'seconds remaining',
          style: TextStyle(color: color.withValues(alpha: 0.7), fontSize: 13),
        ),
        if (isUrgent) ...[
          const SizedBox(height: 4),
          Text(
            '⚠️ Auto-deny imminent!',
            style: TextStyle(color: AppTheme.accentRed, fontWeight: FontWeight.bold, fontSize: 12),
          ),
        ],
      ],
    );
  }
}
