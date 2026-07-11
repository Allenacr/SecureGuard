import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:fl_chart/fl_chart.dart';

import '../config/theme.dart';
import '../providers/incidents_provider.dart';

class TimelineScreen extends StatefulWidget {
  const TimelineScreen({super.key});

  @override
  State<TimelineScreen> createState() => _TimelineScreenState();
}

class _TimelineScreenState extends State<TimelineScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    context.read<IncidentsProvider>().loadStatistics();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Timeline'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'By Hour'),
            Tab(text: 'By Day'),
            Tab(text: 'By Week'),
          ],
          indicatorColor: AppTheme.primaryBlue,
          labelColor: AppTheme.primaryBlue,
          unselectedLabelColor: AppTheme.textMuted,
        ),
      ),
      body: Consumer<IncidentsProvider>(
        builder: (context, provider, _) {
          if (provider.isLoading) return const Center(child: CircularProgressIndicator());

          final stats = provider.statistics;
          if (stats.isEmpty) return const Center(child: Text('No data available'));

          return TabBarView(
            controller: _tabController,
            children: [
              _buildHourlyView(stats),
              _buildDailyView(stats),
              _buildWeeklyView(stats),
            ],
          );
        },
      ),
    );
  }

  Widget _buildHourlyView(Map<String, dynamic> stats) {
    final hourly = (stats['hourly_distribution'] as List?)?.cast<int>() ?? List.filled(24, 0);
    final maxVal = hourly.reduce((a, b) => a > b ? a : b).toDouble();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Incidents by Hour of Day', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          const Text('Shows when access attempts are most frequent', style: TextStyle(color: AppTheme.textMuted, fontSize: 13)),
          const SizedBox(height: 24),
          SizedBox(
            height: 250,
            child: BarChart(
              BarChartData(
                maxY: maxVal > 0 ? maxVal + 1 : 5,
                barTouchData: BarTouchData(
                  touchTooltipData: BarTouchTooltipData(
                    getTooltipItem: (group, groupIndex, rod, rodIndex) {
                      return BarTooltipItem('${rod.toY.toInt()} incidents\nat ${group.x}:00', const TextStyle(color: Colors.white, fontSize: 12));
                    },
                  ),
                ),
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, meta) {
                        if (value.toInt() % 3 == 0) {
                          return Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text('${value.toInt()}', style: const TextStyle(fontSize: 10, color: AppTheme.textMuted)),
                          );
                        }
                        return const SizedBox();
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 30,
                      getTitlesWidget: (value, meta) {
                        return Text('${value.toInt()}', style: const TextStyle(fontSize: 10, color: AppTheme.textMuted));
                      },
                    ),
                  ),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: false),
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: 1,
                  getDrawingHorizontalLine: (value) => FlLine(color: AppTheme.borderLight, strokeWidth: 0.5),
                ),
                barGroups: hourly.asMap().entries.map((e) {
                  final isHighest = e.value == maxVal && maxVal > 0;
                  return BarChartGroupData(
                    x: e.key,
                    barRods: [
                      BarChartRodData(
                        toY: e.value.toDouble(),
                        width: 10,
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                        color: isHighest ? AppTheme.accentRed : AppTheme.primaryBlue,
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),
          ).animate().fadeIn(duration: 500.ms),
        ],
      ),
    );
  }

  Widget _buildDailyView(Map<String, dynamic> stats) {
    // Build daily data from incidents
    final incidents = context.read<IncidentsProvider>().incidents;
    Map<String, int> daily = {};
    for (var i in incidents) {
      final day = '${i.createdAt.month}/${i.createdAt.day}';
      daily[day] = (daily[day] ?? 0) + 1;
    }

    final entries = daily.entries.toList()..sort((a, b) => a.key.compareTo(b.key));
    final last7 = entries.length > 7 ? entries.sublist(entries.length - 7) : entries;

    if (last7.isEmpty) {
      return const Center(child: Text('No daily data available'));
    }

    final maxVal = last7.map((e) => e.value).reduce((a, b) => a > b ? a : b).toDouble();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Daily Incident Trend', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 24),
          SizedBox(
            height: 250,
            child: LineChart(
              LineChartData(
                maxY: maxVal + 1,
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, meta) {
                        if (value.toInt() < last7.length) {
                          return Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(last7[value.toInt()].key, style: const TextStyle(fontSize: 10, color: AppTheme.textMuted)),
                          );
                        }
                        return const SizedBox();
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 30, getTitlesWidget: (v, m) => Text('${v.toInt()}', style: const TextStyle(fontSize: 10, color: AppTheme.textMuted)))),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: false),
                gridData: const FlGridData(show: true, drawVerticalLine: false),
                lineBarsData: [
                  LineChartBarData(
                    spots: last7.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value.value.toDouble())).toList(),
                    isCurved: true,
                    color: AppTheme.primaryBlue,
                    barWidth: 3,
                    dotData: FlDotData(show: true, getDotPainter: (spot, percent, bar, index) => FlDotCirclePainter(radius: 4, color: AppTheme.primaryBlue, strokeWidth: 2, strokeColor: Colors.white)),
                    belowBarData: BarAreaData(show: true, color: AppTheme.primaryBlue.withValues(alpha: 0.1)),
                  ),
                ],
              ),
            ),
          ).animate().fadeIn(duration: 500.ms),
        ],
      ),
    );
  }

  Widget _buildWeeklyView(Map<String, dynamic> stats) {
    final weekly = (stats['weekly_distribution'] as List?)?.cast<int>() ?? List.filled(7, 0);
    final days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    final maxVal = weekly.reduce((a, b) => a > b ? a : b).toDouble();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Weekly Pattern', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 24),
          SizedBox(
            height: 250,
            child: BarChart(
              BarChartData(
                maxY: maxVal > 0 ? maxVal + 1 : 5,
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, meta) {
                        if (value.toInt() < 7) {
                          return Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(days[value.toInt()], style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
                          );
                        }
                        return const SizedBox();
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 30, getTitlesWidget: (v, m) => Text('${v.toInt()}', style: const TextStyle(fontSize: 10, color: AppTheme.textMuted)))),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: false),
                gridData: const FlGridData(show: true, drawVerticalLine: false),
                barGroups: weekly.asMap().entries.map((e) {
                  return BarChartGroupData(
                    x: e.key,
                    barRods: [
                      BarChartRodData(
                        toY: e.value.toDouble(),
                        width: 28,
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
                        gradient: const LinearGradient(colors: [AppTheme.primaryBlue, AppTheme.accentPurple], begin: Alignment.bottomCenter, end: Alignment.topCenter),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),
          ).animate().fadeIn(duration: 500.ms),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }
}
