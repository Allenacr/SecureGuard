import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:secureguard/main.dart';

void main() {
  testWidgets('app boots without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const SecureGuardApp());
    await tester.pumpAndSettle();

    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
