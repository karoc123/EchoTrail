/// Minimal parser/serializer for EchoTrail's TOML-style front matter.
///
/// Format:
/// ```
/// +++
/// key = 'string value'
/// date_key = 2026-03-31
/// int_key = 9
/// float_key = 52.52
/// +++
///
/// Markdown body...
/// ```
class TomlService {
  /// Parse a file that may start with `+++` front matter.
  /// Returns a record with the parsed [meta] map and the [body] text.
  static ({Map<String, dynamic> meta, String body}) parseFrontMatter(
      String content) {
    final trimmed = content.trim();
    if (!trimmed.startsWith('+++')) {
      return (meta: {}, body: content);
    }

    final firstEnd = trimmed.indexOf('+++', 3);
    if (firstEnd == -1) {
      return (meta: {}, body: content);
    }

    final frontMatter = trimmed.substring(3, firstEnd).trim();
    final body = trimmed.substring(firstEnd + 3).trim();

    final meta = <String, dynamic>{};
    for (final line in frontMatter.split('\n')) {
      final trimmedLine = line.trim();
      if (trimmedLine.isEmpty) continue;

      final eqIdx = trimmedLine.indexOf('=');
      if (eqIdx == -1) continue;

      final key = trimmedLine.substring(0, eqIdx).trim();
      final rawValue = trimmedLine.substring(eqIdx + 1).trim();

      meta[key] = _parseValue(key, rawValue);
    }

    return (meta: meta, body: body);
  }

  static dynamic _parseValue(String key, String raw) {
    // Single-quoted string
    if (raw.startsWith("'") && raw.endsWith("'") && raw.length >= 2) {
      return raw.substring(1, raw.length - 1);
    }
    // Double-quoted string
    if (raw.startsWith('"') && raw.endsWith('"') && raw.length >= 2) {
      return raw.substring(1, raw.length - 1);
    }
    // Boolean
    if (raw == 'true') return true;
    if (raw == 'false') return false;
    // Bare date (YYYY-MM-DD) — returned as string
    if (RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(raw)) return raw;
    // Integer
    final intVal = int.tryParse(raw);
    if (intVal != null) return intVal;
    // Double
    final doubleVal = double.tryParse(raw);
    if (doubleVal != null) return doubleVal;
    // Fallback: raw string
    return raw;
  }

  /// Build a file string from [meta] and a Markdown [body].
  static String buildFileContent(Map<String, dynamic> meta, String body) {
    final buf = StringBuffer();
    buf.writeln('+++');
    for (final e in meta.entries) {
      buf.writeln('${e.key} = ${_serializeValue(e.key, e.value)}');
    }
    buf.writeln('+++');
    if (body.isNotEmpty) {
      buf.writeln();
      buf.write(body);
    }
    return buf.toString();
  }

  static String _serializeValue(String key, dynamic value) {
    if (value == null) return "''";
    if (value is bool) return value.toString();
    if (value is int) return value.toString();
    if (value is double) return value.toString();
    if (value is String) {
      // Bare date format for date keys or date-shaped values
      if (key == 'date' || RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(value)) {
        return value;
      }
      return "'$value'";
    }
    return "'${value.toString()}'";
  }
}
