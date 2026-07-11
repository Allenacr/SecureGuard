import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../config/theme.dart';
import '../providers/protection_provider.dart';
import '../models/protected_file.dart';

class ProtectedFilesScreen extends StatefulWidget {
  const ProtectedFilesScreen({super.key});

  @override
  State<ProtectedFilesScreen> createState() => _ProtectedFilesScreenState();
}

class _ProtectedFilesScreenState extends State<ProtectedFilesScreen> {
  @override
  void initState() {
    super.initState();
    context.read<ProtectionProvider>().loadProtectedFiles();
  }

  void _showAddFileDialog() {
    final pathCtrl = TextEditingController();
    final nameCtrl = TextEditingController();
    String fileType = 'file';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDState) => AlertDialog(
          title: const Text('Add Protected Path'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(children: [
                ChoiceChip(label: const Text('File'), selected: fileType == 'file', onSelected: (_) => setDState(() => fileType = 'file')),
                const SizedBox(width: 8),
                ChoiceChip(label: const Text('Folder'), selected: fileType == 'folder', onSelected: (_) => setDState(() => fileType = 'folder')),
              ]),
              const SizedBox(height: 16),
              TextField(controller: pathCtrl, decoration: const InputDecoration(hintText: 'Full path', labelText: 'Path')),
              const SizedBox(height: 12),
              TextField(controller: nameCtrl, decoration: const InputDecoration(hintText: 'Display name', labelText: 'Name')),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            ElevatedButton(
              onPressed: () async {
                if (pathCtrl.text.isEmpty) return;
                Navigator.pop(ctx);
                final name = nameCtrl.text.isEmpty ? pathCtrl.text.split('\\').last : nameCtrl.text;
                await context.read<ProtectionProvider>().addProtectedFile(pathCtrl.text, name, fileType);
              },
              child: const Text('Add'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Protected Files'), actions: [
        IconButton(icon: const Icon(Icons.refresh), onPressed: () => context.read<ProtectionProvider>().loadProtectedFiles()),
      ]),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showAddFileDialog, icon: const Icon(Icons.add), label: const Text('Add'), backgroundColor: AppTheme.primaryBlue, foregroundColor: Colors.white,
      ),
      body: Consumer<ProtectionProvider>(
        builder: (context, provider, _) {
          if (provider.isLoading) return const Center(child: CircularProgressIndicator());
          if (provider.files.isEmpty) return const Center(child: Text('No protected files'));
          return RefreshIndicator(
            onRefresh: () => provider.loadProtectedFiles(),
            child: ListView.builder(
              padding: const EdgeInsets.all(16), itemCount: provider.files.length,
              itemBuilder: (context, i) {
                final f = provider.files[i];
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: Icon(f.isFolder ? Icons.folder : Icons.insert_drive_file, color: f.isFolder ? AppTheme.accentPurple : AppTheme.primaryBlue),
                    title: Text(f.fileName, style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(f.path, style: const TextStyle(fontSize: 11, color: AppTheme.textMuted), maxLines: 1, overflow: TextOverflow.ellipsis),
                      if (f.isBlocked) const Text('BLOCKED', style: TextStyle(color: AppTheme.accentRed, fontSize: 10, fontWeight: FontWeight.bold)),
                    ]),
                    trailing: PopupMenuButton<String>(
                      onSelected: (a) {
                        if (a == 'block') provider.toggleBlockFile(f.id, true);
                        if (a == 'unblock') provider.toggleBlockFile(f.id, false);
                        if (a == 'remove') provider.removeProtectedFile(f.id);
                      },
                      itemBuilder: (c) => [
                        if (!f.isBlocked) const PopupMenuItem(value: 'block', child: Text('Block')),
                        if (f.isBlocked) const PopupMenuItem(value: 'unblock', child: Text('Unblock')),
                        const PopupMenuItem(value: 'remove', child: Text('Remove', style: TextStyle(color: AppTheme.accentRed))),
                      ],
                    ),
                  ),
                ).animate().fadeIn(delay: (i * 50).ms, duration: 300.ms);
              },
            ),
          );
        },
      ),
    );
  }
}
