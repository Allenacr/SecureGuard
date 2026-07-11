package com.secureguard.secureguard

import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterFragmentActivity() {

    private val ALARM_CHANNEL = "com.secureguard/alarm"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, ALARM_CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "startAlarm" -> {
                        AlarmService.start(this)
                        result.success(true)
                    }
                    "stopAlarm" -> {
                        AlarmService.stop(this)
                        result.success(true)
                    }
                    else -> result.notImplemented()
                }
            }
    }
}
