import 'dart:convert';
import 'package:http/http.dart' as http;
import 'local_storage_service.dart';

/// Client for the GitHub Contents REST API.
class GitHubService {
  static const _baseUrl = 'https://api.github.com';

  final String token;
  final String repoOwner;
  final String repoName;
  final http.Client _client;

  GitHubService({
    required this.token,
    required this.repoOwner,
    required this.repoName,
    http.Client? client,
  }) : _client = client ?? http.Client();

  Map<String, String> get _headers => {
        'Authorization': 'token $token',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      };

  /// Lists the contents of [path] in the repository.
  Future<List<Map<String, dynamic>>> getRepoTree(String path) async {
    final encoded =
        path.isEmpty ? '' : Uri.encodeComponent(path).replaceAll('%2F', '/');
    final url = '$_baseUrl/repos/$repoOwner/$repoName/contents/$encoded';
    final response = await _client.get(Uri.parse(url), headers: _headers);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data is List) return data.cast<Map<String, dynamic>>();
    } else if (response.statusCode == 404) {
      return [];
    }
    throw GitHubException(
        'Failed to list "$path": ${response.statusCode} ${response.body}');
  }

  /// Downloads and decodes the text content of a file at [path].
  Future<String> downloadFile(String path) async {
    final encoded = Uri.encodeComponent(path).replaceAll('%2F', '/');
    final url = '$_baseUrl/repos/$repoOwner/$repoName/contents/$encoded';
    final response = await _client.get(Uri.parse(url), headers: _headers);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final b64 = (data['content'] as String).replaceAll('\n', '');
      return utf8.decode(base64.decode(b64));
    }
    throw GitHubException('Failed to download "$path": ${response.statusCode}');
  }

  /// Returns the current SHA of [path] on GitHub, or `null` if it doesn't exist.
  Future<String?> getFileSha(String path) async {
    final encoded = Uri.encodeComponent(path).replaceAll('%2F', '/');
    final url = '$_baseUrl/repos/$repoOwner/$repoName/contents/$encoded';
    final response = await _client.get(Uri.parse(url), headers: _headers);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['sha'] as String?;
    }
    return null;
  }

  /// Creates or updates a file. Provide [sha] when updating an existing file.
  Future<void> uploadFile(
    String path,
    String content, {
    String? sha,
    String? message,
  }) async {
    final encoded = Uri.encodeComponent(path).replaceAll('%2F', '/');
    final url = '$_baseUrl/repos/$repoOwner/$repoName/contents/$encoded';
    final body = <String, dynamic>{
      'message': message ?? 'Update $path',
      'content': base64.encode(utf8.encode(content)),
      if (sha != null) 'sha': sha,
    };
    final response = await _client.put(
      Uri.parse(url),
      headers: _headers,
      body: jsonEncode(body),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw GitHubException(
          'Failed to upload "$path": ${response.statusCode} ${response.body}');
    }
  }

  /// Deletes a file from the repository.
  Future<void> deleteFile(String path, String sha, String message) async {
    final encoded = Uri.encodeComponent(path).replaceAll('%2F', '/');
    final url = '$_baseUrl/repos/$repoOwner/$repoName/contents/$encoded';
    final response = await _client.delete(
      Uri.parse(url),
      headers: _headers,
      body: jsonEncode({'message': message, 'sha': sha}),
    );
    if (response.statusCode != 200) {
      throw GitHubException(
          'Failed to delete "$path": ${response.statusCode}');
    }
  }

  /// Validates the token by checking access to the repository.
  Future<bool> validateToken() async {
    final url = '$_baseUrl/repos/$repoOwner/$repoName';
    final response = await _client.get(Uri.parse(url), headers: _headers);
    return response.statusCode == 200;
  }

  /// Recursively downloads all trips from [tripsPath] to local storage.
  Future<void> downloadTripsToLocal(
    String tripsPath,
    LocalStorageService storage,
  ) async {
    final tripEntries = await getRepoTree(tripsPath);
    for (final tripEntry in tripEntries) {
      if (tripEntry['type'] != 'dir') continue;
      final tripId = tripEntry['name'] as String;
      final tripPath = tripsPath.isEmpty ? tripId : '$tripsPath/$tripId';

      // description.md
      try {
        final content = await downloadFile('$tripPath/description.md');
        final file =
            await storage.getLocalFile('trips/$tripId/description.md');
        await file.parent.create(recursive: true);
        await file.writeAsString(content);
      } catch (_) {}

      // entries
      try {
        final entriesTree = await getRepoTree('$tripPath/entries');
        for (final entryEntry in entriesTree) {
          if (entryEntry['type'] != 'dir') continue;
          final entryId = entryEntry['name'] as String;
          final entryPath = '$tripPath/entries/$entryId';

          try {
            final text = await downloadFile('$entryPath/text.md');
            final f = await storage
                .getLocalFile('trips/$tripId/entries/$entryId/text.md');
            await f.parent.create(recursive: true);
            await f.writeAsString(text);
          } catch (_) {}

          try {
            final media = await downloadFile('$entryPath/media.json');
            final f = await storage
                .getLocalFile('trips/$tripId/entries/$entryId/media.json');
            await f.writeAsString(media);
          } catch (_) {}
        }
      } catch (_) {}
    }
  }
}

class GitHubException implements Exception {
  final String message;
  const GitHubException(this.message);

  @override
  String toString() => 'GitHubException: $message';
}
