import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/trip.dart';
import '../models/entry.dart';
import '../services/local_storage_service.dart';

final localStorageProvider =
    Provider<LocalStorageService>((_) => LocalStorageService());

final tripsProvider =
    AsyncNotifierProvider<TripsNotifier, List<Trip>>(TripsNotifier.new);

class TripsNotifier extends AsyncNotifier<List<Trip>> {
  LocalStorageService get _storage => ref.read(localStorageProvider);

  @override
  Future<List<Trip>> build() => _storage.listTrips();

  Future<void> loadTrips() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => _storage.listTrips());
  }

  static String _slugify(String text) => text
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');

  Future<Trip> createTrip(String title) async {
    final id = _slugify(title);
    final trip = Trip(id: id, title: title);
    await _storage.saveTrip(trip);
    await loadTrips();
    return trip;
  }

  Future<void> updateTrip(Trip trip) async {
    await _storage.saveTrip(trip);
    await loadTrips();
  }

  Future<void> deleteTrip(String tripId) async {
    await _storage.deleteTrip(tripId);
    await loadTrips();
  }

  Future<Entry> createEntry(String tripId, Entry entry) async {
    await _storage.saveEntry(tripId, entry);
    await loadTrips();
    return entry;
  }

  Future<void> updateEntry(String tripId, Entry entry) async {
    await _storage.saveEntry(tripId, entry);
    await loadTrips();
  }

  Future<void> deleteEntry(String tripId, String entryId) async {
    await _storage.deleteEntry(tripId, entryId);
    await loadTrips();
  }
}
