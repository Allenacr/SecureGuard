import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';

/// Authentication service handling Supabase auth, biometrics, and lockout.
class AuthService {
  static final _supabase = Supabase.instance.client;
  static const _secureStorage = FlutterSecureStorage();
  static final _localAuth = LocalAuthentication();

  // Feature 14: Login attempt tracking (persisted)
  static int _loginAttempts = 0;
  static DateTime? _lockedUntil;
  static const int _maxAttempts = 3;
  static const Duration _lockDuration = Duration(minutes: 30);
  static bool _lockStateLoaded = false;

  /// Load persisted lockout state from secure storage
  static Future<void> _loadLockState() async {
    if (_lockStateLoaded) return;
    _lockStateLoaded = true;
    try {
      final attemptsStr = await _secureStorage.read(key: 'login_attempts');
      final lockedStr = await _secureStorage.read(key: 'locked_until');
      if (attemptsStr != null) {
        _loginAttempts = int.tryParse(attemptsStr) ?? 0;
      }
      if (lockedStr != null) {
        final lockedTime = DateTime.tryParse(lockedStr);
        if (lockedTime != null && DateTime.now().isBefore(lockedTime)) {
          _lockedUntil = lockedTime;
        } else {
          // Lockout expired, clean up
          await _secureStorage.delete(key: 'locked_until');
          await _secureStorage.delete(key: 'login_attempts');
        }
      }
    } catch (e) {
      debugPrint('Error loading lock state: $e');
    }
  }

  /// Persist lockout state
  static Future<void> _saveLockState() async {
    try {
      await _secureStorage.write(key: 'login_attempts', value: _loginAttempts.toString());
      if (_lockedUntil != null) {
        await _secureStorage.write(key: 'locked_until', value: _lockedUntil!.toIso8601String());
      } else {
        await _secureStorage.delete(key: 'locked_until');
      }
    } catch (e) {
      debugPrint('Error saving lock state: $e');
    }
  }

  /// Sign in with email and password
  static Future<AuthResponse> signIn(String email, String password) async {
    // Load persisted lockout state
    await _loadLockState();

    // Check lockout (Feature 14)
    if (_lockedUntil != null && DateTime.now().isBefore(_lockedUntil!)) {
      final remaining = _lockedUntil!.difference(DateTime.now()).inMinutes;
      throw Exception('Account locked. Try again in $remaining minutes.');
    }

    try {
      final response = await _supabase.auth.signInWithPassword(
        email: email,
        password: password,
      );

      // Reset attempts on success
      _loginAttempts = 0;
      _lockedUntil = null;
      await _saveLockState();

      // Store credentials for biometric re-auth (Feature 13)
      await _secureStorage.write(key: 'email', value: email);
      await _secureStorage.write(key: 'password', value: password);
      await _secureStorage.write(key: 'biometric_enabled', value: 'true');

      return response;
    } on AuthException catch (e) {
      _loginAttempts++;

      // Feature 14: Lock after max attempts
      if (_loginAttempts >= _maxAttempts) {
        _lockedUntil = DateTime.now().add(_lockDuration);
        _loginAttempts = 0;
        await _saveLockState();
        throw Exception(
          'Too many failed attempts. Account locked for ${_lockDuration.inMinutes} minutes.',
        );
      }

      await _saveLockState();

      // Specific error messages
      if (e.message.contains('Invalid login credentials')) {
        throw Exception(
          'Wrong email or password. ${_maxAttempts - _loginAttempts} attempts remaining.',
        );
      } else if (e.message.contains('Email not confirmed')) {
        throw Exception('Please confirm your email address first.');
      } else {
        throw Exception(e.message);
      }
    } catch (e) {
      if (e.toString().contains('SocketException') ||
          e.toString().contains('network')) {
        throw Exception('No internet connection. Please check your network.');
      }
      rethrow;
    }
  }

  /// Sign out
  static Future<void> signOut() async {
    await _supabase.auth.signOut();
  }

  /// Get current user
  static User? get currentUser => _supabase.auth.currentUser;

  /// Check if user is logged in
  static bool get isLoggedIn => currentUser != null;

  /// Feature 13: Biometric authentication
  static Future<bool> authenticateWithBiometrics() async {
    try {
      final canAuth = await _localAuth.canCheckBiometrics;
      final isDeviceSupported = await _localAuth.isDeviceSupported();

      if (!canAuth || !isDeviceSupported) return false;

      final didAuth = await _localAuth.authenticate(
        localizedReason: 'Authenticate to access SecureGuard',
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: false,
        ),
      );

      if (didAuth) {
        // Re-authenticate with Supabase using stored credentials
        final email = await _secureStorage.read(key: 'email');
        final password = await _secureStorage.read(key: 'password');

        if (email != null && password != null) {
          await _supabase.auth.signInWithPassword(
            email: email,
            password: password,
          );
          return true;
        }
      }
      return false;
    } catch (e) {
      debugPrint('Biometric auth error: $e');
      return false;
    }
  }

  /// Check if biometrics are available
  static Future<bool> isBiometricAvailable() async {
    try {
      final canAuth = await _localAuth.canCheckBiometrics;
      final isSupported = await _localAuth.isDeviceSupported();
      return canAuth && isSupported;
    } catch (e) {
      return false;
    }
  }

  /// Check if biometric login was previously set up
  static Future<bool> hasBiometricCredentials() async {
    final email = await _secureStorage.read(key: 'email');
    final password = await _secureStorage.read(key: 'password');
    final enabled = await _secureStorage.read(key: 'biometric_enabled');
    return email != null && password != null && enabled == 'true';
  }

  /// Feature 19: App lock state
  static Future<bool> requiresAppLock() async {
    return await hasBiometricCredentials() && await isBiometricAvailable();
  }

  /// Get lockout remaining time
  static Duration? getLockoutRemaining() {
    if (_lockedUntil != null && DateTime.now().isBefore(_lockedUntil!)) {
      return _lockedUntil!.difference(DateTime.now());
    }
    return null;
  }
}
