import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/github_service.dart';

class AuthState {
  final String? token;
  final String? repoOwner;
  final String? repoName;
  final String? tripsPath;

  const AuthState({
    this.token,
    this.repoOwner,
    this.repoName,
    this.tripsPath,
  });

  bool get isLoggedIn =>
      token != null && repoOwner != null && repoName != null;
  bool get isConfigured => isLoggedIn && tripsPath != null;

  AuthState copyWith({
    String? token,
    String? repoOwner,
    String? repoName,
    String? tripsPath,
    bool clearTripsPath = false,
  }) =>
      AuthState(
        token: token ?? this.token,
        repoOwner: repoOwner ?? this.repoOwner,
        repoName: repoName ?? this.repoName,
        tripsPath: clearTripsPath ? null : (tripsPath ?? this.tripsPath),
      );
}

final authProvider =
    AsyncNotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);

class AuthNotifier extends AsyncNotifier<AuthState> {
  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'github_token';
  static const _ownerKey = 'repo_owner';
  static const _repoKey = 'repo_name';
  static const _pathKey = 'trips_path';

  @override
  Future<AuthState> build() async {
    final token = await _storage.read(key: _tokenKey);
    final prefs = await SharedPreferences.getInstance();
    return AuthState(
      token: token,
      repoOwner: prefs.getString(_ownerKey),
      repoName: prefs.getString(_repoKey),
      tripsPath: prefs.getString(_pathKey),
    );
  }

  Future<void> login(String token, String repoUrl) async {
    state = const AsyncLoading();
    try {
      final (owner, repo) = _parseRepoUrl(repoUrl);
      final github =
          GitHubService(token: token, repoOwner: owner, repoName: repo);
      if (!await github.validateToken()) {
        throw Exception('Invalid token or repository not accessible');
      }
      await _storage.write(key: _tokenKey, value: token);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_ownerKey, owner);
      await prefs.setString(_repoKey, repo);
      state = AsyncData(AuthState(token: token, repoOwner: owner, repoName: repo));
    } catch (e, st) {
      state = AsyncError(e, st);
      rethrow;
    }
  }

  Future<void> setTripsPath(String path) async {
    final current = state.valueOrNull;
    if (current == null) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_pathKey, path);
    state = AsyncData(current.copyWith(tripsPath: path));
  }

  Future<void> logout() async {
    await _storage.delete(key: _tokenKey);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_ownerKey);
    await prefs.remove(_repoKey);
    await prefs.remove(_pathKey);
    state = const AsyncData(AuthState());
  }

  static (String owner, String repo) _parseRepoUrl(String url) {
    final uri = Uri.tryParse(url);
    if (uri != null && uri.host == 'github.com') {
      final segs = uri.pathSegments.where((s) => s.isNotEmpty).toList();
      if (segs.length < 2) throw Exception('Invalid GitHub URL');
      return (segs[0], segs[1].replaceAll('.git', ''));
    }
    // owner/repo shorthand
    final parts = url.split('/').where((s) => s.isNotEmpty).toList();
    if (parts.length < 2) {
      throw Exception('Invalid repository format — use https://github.com/owner/repo');
    }
    return (parts[parts.length - 2], parts.last.replaceAll('.git', ''));
  }
}
