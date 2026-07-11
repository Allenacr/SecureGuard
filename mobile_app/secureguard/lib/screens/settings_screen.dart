import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../config/theme.dart';
import '../providers/settings_provider.dart';
import '../services/database_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final List<TextEditingController> _qControllers = [];
  final List<TextEditingController> _aControllers = [];
  final _keywordController = TextEditingController();
  double _timeoutValue = 60;
  bool _keywordVisible = false;
  String _selectedSound = 'default';

  @override
  void initState() {
    super.initState();
    for (int i = 0; i < 5; i++) {
      _qControllers.add(TextEditingController());
      _aControllers.add(TextEditingController());
    }
    _loadSettingsData();
  }

  Future<void> _loadSettingsData() async {
    final sp = context.read<SettingsProvider>();
    await sp.loadSettings();
    final s = sp.settings;
    if (s != null) {
      setState(() {
        _keywordController.text = s.secretKeyword;
        _timeoutValue = s.alertTimeoutSeconds.toDouble();
        _selectedSound = s.notificationSound;
        for (int i = 0; i < 5 && i < s.questions.length; i++) {
          _qControllers[i].text = s.questions[i]['question'] ?? '';
          _aControllers[i].text = s.questions[i]['answer'] ?? '';
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: Consumer<SettingsProvider>(
        builder: (context, sp, _) {
          if (sp.isLoading) return const Center(child: CircularProgressIndicator());
          return SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Dark Mode
                _sectionTitle('Appearance'),
                Card(child: SwitchListTile(
                  title: const Text('Dark Mode'),
                  subtitle: const Text('Toggle dark theme'),
                  secondary: const Icon(Icons.dark_mode_rounded),
                  value: sp.isDarkMode,
                  onChanged: (_) => sp.toggleDarkMode(),
                )).animate().fadeIn(duration: 300.ms),

                const SizedBox(height: 24),

                // Security Questions (Feature 10)
                _sectionTitle('Security Questions'),
                const SizedBox(height: 8),
                ...List.generate(5, (i) => _questionField(i)),
                const SizedBox(height: 8),
                ElevatedButton.icon(
                  onPressed: () => _saveQuestions(sp),
                  icon: const Icon(Icons.save_rounded, size: 18),
                  label: const Text('Save Questions'),
                ).animate().fadeIn(delay: 300.ms, duration: 300.ms),

                const SizedBox(height: 24),

                // Secret Keyword (Feature 11)
                _sectionTitle('Secret Keyword'),
                const SizedBox(height: 8),
                Row(children: [
                  Expanded(child: TextField(
                    controller: _keywordController,
                    obscureText: !_keywordVisible,
                    decoration: InputDecoration(
                      hintText: 'Enter keyword',
                      suffixIcon: IconButton(
                        icon: Icon(_keywordVisible ? Icons.visibility_off : Icons.visibility),
                        onPressed: () => setState(() => _keywordVisible = !_keywordVisible),
                      ),
                    ),
                  )),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () => _saveKeyword(sp),
                    child: const Text('Save'),
                  ),
                ]).animate().fadeIn(delay: 400.ms, duration: 300.ms),

                const SizedBox(height: 24),

                // Alert Timeout (Feature 12)
                _sectionTitle('Alert Timeout'),
                const SizedBox(height: 8),
                Card(child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(children: [
                    Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                      const Text('Auto-deny after:'),
                      Text('${_timeoutValue.toInt()} seconds', style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primaryBlue)),
                    ]),
                    Slider(
                      value: _timeoutValue, min: 15, max: 300, divisions: 19,
                      label: '${_timeoutValue.toInt()}s',
                      onChanged: (v) => setState(() => _timeoutValue = v),
                      onChangeEnd: (v) => sp.updateTimeout(v.toInt()),
                    ),
                  ]),
                )).animate().fadeIn(delay: 500.ms, duration: 300.ms),

                const SizedBox(height: 24),

                // Notification Sound (Feature 20)
                _sectionTitle('Notification Sound'),
                const SizedBox(height: 8),
                Card(child: Column(children: [
                  for (final sound in ['default', 'siren', 'alarm', 'beep'])
                    RadioListTile<String>(
                      title: Text(sound[0].toUpperCase() + sound.substring(1)),
                      value: sound, groupValue: _selectedSound,
                      onChanged: (v) {
                        setState(() => _selectedSound = v!);
                        sp.updateNotificationSound(v!);
                      },
                    ),
                ])).animate().fadeIn(delay: 600.ms, duration: 300.ms),

                const SizedBox(height: 24),

                // Owner Accounts (Feature 16)
                _sectionTitle('Owner Accounts'),
                const SizedBox(height: 8),
                ElevatedButton.icon(
                  onPressed: _showAddOwnerDialog,
                  icon: const Icon(Icons.person_add_rounded, size: 18),
                  label: const Text('Add Owner'),
                  style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accentPurple),
                ).animate().fadeIn(delay: 700.ms, duration: 300.ms),

                const SizedBox(height: 48),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _sectionTitle(String text) {
    return Text(text, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold));
  }

  Widget _questionField(int i) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: AppTheme.primaryBlue, borderRadius: BorderRadius.circular(6)),
              child: Text('Q${i + 1}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
            ),
            const SizedBox(width: 8),
            Expanded(child: TextField(
              controller: _qControllers[i],
              decoration: const InputDecoration(hintText: 'Question', border: InputBorder.none, isDense: true),
              style: const TextStyle(fontSize: 14),
            )),
          ]),
          const Divider(),
          TextField(
            controller: _aControllers[i],
            decoration: const InputDecoration(hintText: 'Answer', prefixText: 'Ans: ', border: InputBorder.none, isDense: true),
            style: const TextStyle(fontSize: 14),
          ),
        ]),
      )),
    ).animate().fadeIn(delay: (200 + i * 50).ms, duration: 300.ms);
  }

  void _saveQuestions(SettingsProvider sp) {
    final questions = List.generate(5, (i) => {'question': _qControllers[i].text, 'answer': _aControllers[i].text});
    sp.updateQuestions(questions).then((ok) {
      if (ok && mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Questions saved!')));
    });
  }

  void _saveKeyword(SettingsProvider sp) {
    if (_keywordController.text.length < 3) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Keyword must be at least 3 characters')));
      return;
    }
    sp.updateKeyword(_keywordController.text).then((ok) {
      if (ok && mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Keyword saved!')));
    });
  }

  void _showAddOwnerDialog() {
    final emailCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add Owner'),
        content: TextField(controller: emailCtrl, decoration: const InputDecoration(hintText: 'Owner email', labelText: 'Email')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              if (emailCtrl.text.isEmpty) return;
              Navigator.pop(ctx);
              try {
                await DatabaseService.addOwnerAccount(emailCtrl.text.trim());
                if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Owner added!')));
              } catch (e) {
                if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
              }
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    for (final c in _qControllers) c.dispose();
    for (final c in _aControllers) c.dispose();
    _keywordController.dispose();
    super.dispose();
  }
}
