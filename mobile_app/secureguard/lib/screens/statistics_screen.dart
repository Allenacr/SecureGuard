import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:fl_chart/fl_chart.dart';

import '../config/theme.dart';
import '../providers/incidents_provider.dart';
import '../widgets/stat_card.dart';

class StatisticsScreen extends StatefulWidget {
  const StatisticsScreen({super.key});

  @override
  State<StatisticsScreen> createState() => _StatisticsScreenState();
}

class _StatisticsScreenState extends State<StatisticsScreen> {
  @override
  void initState() {
    super.initState();
    context.read<IncidentsProvider>().loadStatistics();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Statistics')),
      body: Consumer<IncidentsProvider>(
        builder: (context, provider, _) {
          if (provider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          final stats = provider.statistics;
          if (stats.isEmpty) {
            return const Center(child: Text('No data available'));
          }

          return RefreshIndicator(
            onRefresh: () => provider.loadStatistics(),
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Summary Cards
                  Row(
                    children: [
                      Expanded(
                        child: StatCard(
                          title: 'Total',
                          value: '${stats['total_incidents'] ?? 0}',
                          icon: Icons.analytics_rounded,
                          color: AppTheme.primaryBlue,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: StatCard(
                          title: 'Allowed',
                          value: '${stats['total_allowed'] ?? 0}',
                          icon: Icons.check_circle_rounded,
                          color: AppTheme.accentGreen,
                        ),
                      ),
                    ],
                  ).animate().fadeIn(duration: 400.ms),

                  const SizedBox(height: 12),

                  Row(
                    children: [
                      Expanded(
                        child: StatCard(
                          title: 'Denied',
                          value: '${stats['total_denied'] ?? 0}',
                          icon: Icons.block_rounded,
                          color: AppTheme.accentRed,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: StatCard(
                          title: 'Success Rate',
                          value: '${(stats['success_rate'] as double? ?? 0).toStringAsFixed(1)}%',
                          icon: Icons.trending_up_rounded,
                          color: AppTheme.accentPurple,
                        ),
                      ),
                    ],
                  ).animate().fadeIn(delay: 100.ms, duration: 400.ms),

                  const SizedBox(height: 24),

                  // Pie Chart
                  _buildPieChart(stats).animate().fadeIn(delay: 200.ms, duration: 500.ms),

                  const SizedBox(height: 24),

                  // Info Cards
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          _infoRow('📂 Most Targeted File', stats['most_targeted_file'] ?? 'N/A'),
                          const Divider(),
                          _infoRow('📅 Most Active Day', stats['most_active_day'] ?? 'N/A'),
                          const Divider(),
                          _infoRow('🔒 Blocked Files', '${stats['total_blocked'] ?? 0}'),
                        ],
                      ),
                    ),
                  ).animate().fadeIn(delay: 300.ms, duration: 500.ms),

                  const SizedBox(height: 24),

                  // Hourly Distribution Bar Chart
                  _buildHourlyChart(stats).animate().fadeIn(delay: 400.ms, duration: 500.ms),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildPieChart(Map<String, dynamic> stats) {
    final allowed = (stats['total_allowed'] as int?) ?? 0;
    final denied = (stats['total_denied'] as int?) ?? 0;
    final blocked = (stats['total_blocked'] as int?) ?? 0;
    final total = allowed + denied + blocked;

    if (total == 0) return const SizedBox();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Text('Incident Breakdown', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 20),
            SizedBox(
              height: 180,
              child: PieChart(
                PieChartData(
                  sectionsSpace: 3,
                  centerSpaceRadius: 40,
                  sections: [
                    PieChartSectionData(
                      value: allowed.toDouble(),
                      color: AppTheme.accentGreen,
                      title: '$allowed',
                      titleStyle: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                      radius: 50,
                    ),
                    PieChartSectionData(
                      value: denied.toDouble(),
                      color: AppTheme.accentRed,
                      title: '$denied',
                      titleStyle: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                      radius: 50,
                    ),
                    if (blocked > 0)
                      PieChartSectionData(
                        value: blocked.toDouble(),
                        color: AppTheme.accentAmber,
                        title: '$blocked',
                        titleStyle: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                        radius: 50,
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _legendDot(AppTheme.accentGreen, 'Allowed'),
                const SizedBox(width: 16),
                _legendDot(AppTheme.accentRed, 'Denied'),
                const SizedBox(width: 16),
                _legendDot(AppTheme.accentAmber, 'Blocked'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHourlyChart(Map<String, dynamic> stats) {
    final hourly = (stats['hourly_distribution'] as List?)?.cast<int>() ?? List.filled(24, 0);
    final maxVal = hourly.reduce((a, b) => a > b ? a : b).toDouble();

    if (maxVal == 0) return const SizedBox();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Hourly Activity', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 20),
            SizedBox(
              height: 180,
              child: BarChart(
                BarChartData(
                  maxY: maxVal + 1,
                  barTouchData: BarTouchData(enabled: true),
                  titlesData: FlTitlesData(
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          if (value.toInt() % 6 == 0) {
                            return Text('${value.toInt()}h', style: const TextStyle(fontSize: 10, color: AppTheme.textMuted));
                          }
                          return const SizedBox();
                        },
                      ),
                    ),
                    leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  borderData: FlBorderData(show: false),
                  gridData: const FlGridData(show: false),
                  barGroups: hourly.asMap().entries.map((e) {
                    return BarChartGroupData(
                      x: e.key,
                      barRods: [
                        BarChartRodData(
                          toY: e.value.toDouble(),
                          width: 8,
                          borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                          gradient: const LinearGradient(
                            colors: [AppTheme.primaryBlue, AppTheme.accentPurple],
                            begin: Alignment.bottomCenter,
                            end: Alignment.topCenter,
                          ),
                        ),
                      ],
                    );
                  }).toList(),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _legendDot(Color color, String label) {
    return Row(
      children: [
        Container(width: 10, height: 10, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
      ],
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 14)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        ],
      ),
    );
  }
}
