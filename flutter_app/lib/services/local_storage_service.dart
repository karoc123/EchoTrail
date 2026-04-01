import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import '../models/trip.dart';
import '../models/entry.dart';
import 'toml_service.dart';

/// Manages all local file I/O for EchoTrail trip data.
///
/// Data lives in `<documents>/echotrail_data/trips/`.
/// A `.sync_state.json` file tracks which relative paths have unsaved changes.
class LocalStorageService {
  static const _syncStateFile = '.sync_state.json';

  Future<Directory> get _baseDir async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory(p.join(docs.path, 'echotrail_data'));
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  Future<Directory> get _tripsDir async {
    final base = await _baseDir;
    final dir = Directory(p.join(base.path, 'trips'));
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  Future<File> get _syncFile async {
    final base = await _baseDir;
    return File(p.join(base.path, _syncStateFile));
  }

  // ── Dirty tracking ────────────────────────────────────────────────────────

  Future<Set<String>> _loadDirtySet() async {
    final file = await _syncFile;
    if (!await file.exists()) return {};
    try {
      final json =
          jsonDecode(await file.readAsString()) as Map<String, dynamic>;
      return Set<String>.from((json['dirty'] as List?) ?? []);
    } catch (_) {
      return {};
    }
  }

  Future<void> _saveDirtySet(Set<String> dirty) async {
    final file = await _syncFile;
    await file.writeAsString(jsonEncode({'dirty': dirty.toList()}));
  }

  Future<void> _markDirty(String relativePath) async {
    final dirty = await _loadDirtySet();
    dirty.add(relativePath);
    await _saveDirtySet(dirty);
  }

  Future<void> markSynced(String path) async {
    final dirty = await _loadDirtySet();
    dirty.remove(path);
    await _saveDirtySet(dirty);
  }

  Future<List<String>> getDirtyPaths() async =>
      (await _loadDirtySet()).toList();

  // ── Trip operations ───────────────────────────────────────────────────────

  Future<List<Trip>> listTrips() async {
    final dir = await _tripsDir;
    final trips = <Trip>[];
    await for (final entity in dir.list()) {
      if (entity is Directory) {
        final trip = await _loadTripFromDir(entity);
        if (trip != null) trips.add(trip);
      }
    }
    trips.sort((a, b) => a.title.compareTo(b.title));
    return trips;
  }

  Future<Trip?> loadTrip(String tripId) async {
    final dir = await _tripsDir;
    final tripDir = Directory(p.join(dir.path, tripId));
    if (!await tripDir.exists()) return null;
    return _loadTripFromDir(tripDir);
  }

  Future<Trip?> _loadTripFromDir(Directory tripDir) async {
    final tripId = p.basename(tripDir.path);
    final descFile = File(p.join(tripDir.path, 'description.md'));

    String title = tripId;
    String odometerKm = '';
    String descriptionMd = '';

    if (await descFile.exists()) {
      final content = await descFile.readAsString();
      final parsed = TomlService.parseFrontMatter(content);
      title = parsed.meta['title'] as String? ?? tripId;
      odometerKm = parsed.meta['odometer_km'] as String? ?? '';
      descriptionMd = parsed.body;
    }

    final entries = await _loadEntries(tripDir);
    return Trip(
      id: tripId,
      title: title,
      odometerKm: odometerKm,
      descriptionMd: descriptionMd,
      entries: entries,
    );
  }

  Future<List<Entry>> _loadEntries(Directory tripDir) async {
    final entriesDir = Directory(p.join(tripDir.path, 'entries'));
    if (!await entriesDir.exists()) return [];

    final entries = <Entry>[];
    await for (final entity in entriesDir.list()) {
      if (entity is Directory) {
        final entry = await _loadEntryFromDir(entity);
        if (entry != null) entries.add(entry);
      }
    }
    entries.sort((a, b) => a.date.compareTo(b.date));
    return entries;
  }

  Future<Entry?> _loadEntryFromDir(Directory entryDir) async {
    final entryId = p.basename(entryDir.path);
    final textFile = File(p.join(entryDir.path, 'text.md'));
    final mediaFile = File(p.join(entryDir.path, 'media.json'));

    String date = '';
    String country = '';
    String weather = '';
    String temperatureC = '';
    double? lat;
    double? lon;
    String pointName = '';
    String textMd = '';

    if (await textFile.exists()) {
      final content = await textFile.readAsString();
      final parsed = TomlService.parseFrontMatter(content);
      date = parsed.meta['date']?.toString() ?? '';
      country = parsed.meta['country'] as String? ?? '';
      weather = parsed.meta['weather'] as String? ?? '';
      final tempRaw = parsed.meta['temperature_c'];
      temperatureC = tempRaw != null ? tempRaw.toString() : '';
      final latRaw = parsed.meta['lat'];
      if (latRaw is num) lat = latRaw.toDouble();
      final lonRaw = parsed.meta['lon'];
      if (lonRaw is num) lon = lonRaw.toDouble();
      pointName = parsed.meta['point_name'] as String? ?? '';
      textMd = parsed.body;
    }

    final media = <MediaItem>[];
    if (await mediaFile.exists()) {
      try {
        final json =
            jsonDecode(await mediaFile.readAsString()) as Map<String, dynamic>;
        final list = (json['media'] as List<dynamic>?) ?? [];
        for (final item in list) {
          media.add(MediaItem.fromJson(item as Map<String, dynamic>));
        }
      } catch (_) {}
    }

    return Entry(
      id: entryId,
      date: date,
      country: country,
      weather: weather,
      temperatureC: temperatureC,
      lat: lat,
      lon: lon,
      pointName: pointName,
      textMd: textMd,
      media: media,
    );
  }

  Future<void> saveTrip(Trip trip) async {
    final dir = await _tripsDir;
    final tripDir = Directory(p.join(dir.path, trip.id));
    if (!await tripDir.exists()) await tripDir.create(recursive: true);

    final meta = <String, dynamic>{
      'title': trip.title,
      if (trip.odometerKm.isNotEmpty) 'odometer_km': trip.odometerKm,
    };
    final content = TomlService.buildFileContent(meta, trip.descriptionMd);
    await File(p.join(tripDir.path, 'description.md')).writeAsString(content);
    await _markDirty('trips/${trip.id}/description.md');
  }

  Future<void> saveEntry(String tripId, Entry entry) async {
    final dir = await _tripsDir;
    final entryDir =
        Directory(p.join(dir.path, tripId, 'entries', entry.id));
    if (!await entryDir.exists()) await entryDir.create(recursive: true);

    final meta = <String, dynamic>{};
    if (entry.date.isNotEmpty) meta['date'] = entry.date;
    if (entry.country.isNotEmpty) meta['country'] = entry.country;
    if (entry.weather.isNotEmpty) meta['weather'] = entry.weather;
    if (entry.temperatureC.isNotEmpty) {
      final temp = int.tryParse(entry.temperatureC) ??
          double.tryParse(entry.temperatureC);
      if (temp != null) meta['temperature_c'] = temp;
    }
    if (entry.lat != null) meta['lat'] = entry.lat;
    if (entry.lon != null) meta['lon'] = entry.lon;
    if (entry.pointName.isNotEmpty) meta['point_name'] = entry.pointName;

    final textContent = TomlService.buildFileContent(meta, entry.textMd);
    await File(p.join(entryDir.path, 'text.md')).writeAsString(textContent);

    final mediaContent =
        jsonEncode({'media': entry.media.map((m) => m.toJson()).toList()});
    await File(p.join(entryDir.path, 'media.json')).writeAsString(mediaContent);

    await _markDirty('trips/$tripId/entries/${entry.id}/text.md');
    await _markDirty('trips/$tripId/entries/${entry.id}/media.json');
  }

  Future<void> deleteEntry(String tripId, String entryId) async {
    final dir = await _tripsDir;
    final entryDir =
        Directory(p.join(dir.path, tripId, 'entries', entryId));
    if (await entryDir.exists()) await entryDir.delete(recursive: true);
  }

  Future<void> deleteTrip(String tripId) async {
    final dir = await _tripsDir;
    final tripDir = Directory(p.join(dir.path, tripId));
    if (await tripDir.exists()) await tripDir.delete(recursive: true);
  }

  Future<void> clearAllData() async {
    final base = await _baseDir;
    if (await base.exists()) await base.delete(recursive: true);
  }

  /// Returns a [File] handle for a path relative to the base data directory.
  Future<File> getLocalFile(String relativePath) async {
    final base = await _baseDir;
    return File(p.join(base.path, relativePath));
  }
}
