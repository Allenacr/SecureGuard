import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/theme.dart';
import '../providers/protection_provider.dart';

class PanicButton extends StatelessWidget {
  const PanicButton({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: () => _showPanicConfirmation(context),
        icon: const Icon(Icons.warning_amber_rounded, color: AppTheme.accentRed),
        label: const Text('🚨 Emergency Disable', style: TextStyle(color: AppTheme.accentRed, fontWeight: FontWeight.w600)),
        style: OutlinedButton.styleFrom(
          side: const BorderSide(color: AppTheme.accentRed),
          padding: const EdgeInsets.symmetric(vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
    );
  }

  void _showPanicConfirmation(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('⚠️ Emergency Disable'),
        content: const Text('This will immediately turn OFF all file protection. Are you sure?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              context.read<ProtectionProvider>().panicDisable();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('🚨 All protection disabled!'), backgroundColor: AppTheme.accentRed),
              );
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accentRed),
            child: const Text('DISABLE ALL'),
          ),
        ],
      ),
    );
  }
}
