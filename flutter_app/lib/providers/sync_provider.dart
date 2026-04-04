import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/github_service.dart';
import '../services/local_storage_service.dart';
import 'auth_provider.dart';
import 'trips_provider.dart';

class SyncState {
  final bool isSyncing;
  final String? lastSyncTime;
  final int pendingChanges;
  final String? error;
  final String? statusMessage;

  const SyncState({
    this.isSyncing = false,
    this.lastSyncTime,
    this.pendingChanges = 0,
    this.error,
    this.statusMessage,
  });

  SyncState copyWith({
    bool? isSyncing,
    String? lastSyncTime,
    int? pendingChanges,
    String? error,
    String? statusMessage,
    bool clearError = false,
    bool clearStatus = false,
  }) =>
      SyncState(
        isSyncing: isSyncing ?? this.isSyncing,
        lastSyncTime: lastSyncTime ?? this.lastSyncTime,
        pendingChanges: pendingChanges ?? this.pendingChanges,
        error: clearError ? null : (error ?? this.error),
        statusMessage:
            clearStatus ? null : (statusMessage ?? this.statusMessage),
      );
}

final syncProvider =
    AsyncNotifierProvider<SyncNotifier, SyncState>(SyncNotifier.new);

class SyncNotifier extends AsyncNotifier<SyncState> {
  LocalStorageService get _storage => ref.read(localStorageProvider);

  @override
  Future<SyncState> build() async {
    final dirty = await _storage.getDirtyPaths();
    return SyncState(pendingChanges: dirty.length);
  }

  GitHubService? _github() {
    final auth = ref.read(authProvider).valueOrNull;
    if (auth == null || !auth.isLoggedIn) return null;
    return GitHubService(
      token: auth.token!,
      repoOwner: auth.repoOwner!,
      repoName: auth.repoName!,
    );
  }

  String? _tripsPath() =>
      ref.read(authProvider).valueOrNull?.tripsPath;

  void _set(SyncState s) => state = AsyncData(s);

  SyncState get _current => state.valueOrNull ?? const SyncState();

  /// Downloads all trips from GitHub to local storage.
  Future<void> downloadFromGitHub() async {
    final github = _github();
    final tripsPath = _tripsPath();
    if (github == null || tripsPath == null) {
      _set(_current.copyWith(error: 'Not logged in or trips path not set'));
      return;
    }

    _set(_current.copyWith(
      isSyncing: true,
      statusMessage: 'Downloading from GitHub…',
      clearError: true,
    ));

    try {
      await github.downloadTripsToLocal(tripsPath, _storage);
      await ref.read(tripsProvider.notifier).loadTrips();
      final dirty = await _storage.getDirtyPaths();
      _set(_current.copyWith(
        isSyncing: false,
        lastSyncTime: DateTime.now().toIso8601String(),
        pendingChanges: dirty.length,
        statusMessage: 'Download complete',
        clearError: true,
      ));
    } catch (e) {
      _set(_current.copyWith(
        isSyncing: false,
        error: e.toString(),
        clearStatus: true,
      ));
    }
  }

  /// Uploads all locally modified files to GitHub.
  Future<void> syncToGitHub() async {
    final github = _github();
    final tripsPath = _tripsPath();
    if (github == null || tripsPath == null) {
      _set(_current.copyWith(error: 'Not logged in or trips path not set'));
      return;
    }

    _set(_current.copyWith(
      isSyncing: true,
      statusMessage: 'Syncing to GitHub…',
      clearError: true,
    ));

    try {
      final dirtyPaths = await _storage.getDirtyPaths();
      for (final relativePath in List<String>.from(dirtyPaths)) {
        final localFile = await _storage.getLocalFile(relativePath);
        if (!await localFile.exists()) {
          await _storage.markSynced(relativePath);
          continue;
        }
        final content = await localFile.readAsString();

        // Map local relative path → repo path.
        // relativePath: "trips/{id}/..." → strip "trips/" and prepend tripsPath
        String repoPath;
        if (relativePath.startsWith('trips/')) {
          final after = relativePath.substring('trips/'.length);
          repoPath = tripsPath.isEmpty ? after : '$tripsPath/$after';
        } else {
          repoPath = tripsPath.isEmpty ? relativePath : '$tripsPath/$relativePath';
        }

        // Force-write: always fetch current remote SHA first.
        final sha = await github.getFileSha(repoPath);
        await github.uploadFile(repoPath, content,
            sha: sha, message: 'Update $repoPath via TraceVoyage app');
        await _storage.markSynced(relativePath);
      }

      final remaining = await _storage.getDirtyPaths();
      _set(_current.copyWith(
        isSyncing: false,
        lastSyncTime: DateTime.now().toIso8601String(),
        pendingChanges: remaining.length,
        statusMessage: 'Sync complete',
        clearError: true,
      ));
    } catch (e) {
      _set(_current.copyWith(
        isSyncing: false,
        error: e.toString(),
        clearStatus: true,
      ));
    }
  }
}
