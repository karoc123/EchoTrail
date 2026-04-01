import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/trips_provider.dart';
import '../providers/sync_provider.dart';
import '../providers/auth_provider.dart';
import '../models/trip.dart';

class TripsListScreen extends ConsumerWidget {
  const TripsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tripsAsync = ref.watch(tripsProvider);
    final syncState = ref.watch(syncProvider).valueOrNull;

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Trips'),
        backgroundColor: const Color(0xFF2196F3),
        foregroundColor: Colors.white,
        actions: [
          if (syncState?.isSyncing == true)
            const Padding(
              padding: EdgeInsets.all(14),
              child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white)),
            )
          else
            IconButton(
              icon: const Icon(Icons.sync),
              tooltip: 'Sync to GitHub',
              onPressed: () =>
                  ref.read(syncProvider.notifier).syncToGitHub(),
            ),
          IconButton(
            icon: const Icon(Icons.download),
            tooltip: 'Download from GitHub',
            onPressed: () =>
                ref.read(syncProvider.notifier).downloadFromGitHub(),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Logout',
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
              if (context.mounted) context.go('/login');
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Sync status bar
          Container(
            width: double.infinity,
            color: Colors.grey.shade100,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                Icon(
                  syncState?.error != null
                      ? Icons.error_outline
                      : Icons.cloud_done,
                  size: 16,
                  color: syncState?.error != null ? Colors.red : Colors.green,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    syncState?.error ??
                        (syncState?.lastSyncTime != null
                            ? 'Last sync: ${syncState!.lastSyncTime}'
                            : syncState?.statusMessage ?? 'Not synced yet'),
                    style: TextStyle(
                      fontSize: 12,
                      color: syncState?.error != null
                          ? Colors.red
                          : Colors.grey.shade700,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if ((syncState?.pendingChanges ?? 0) > 0)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.orange,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${syncState!.pendingChanges} pending',
                      style:
                          const TextStyle(color: Colors.white, fontSize: 11),
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: tripsAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('Error: $e'),
                    ElevatedButton(
                      onPressed: () =>
                          ref.read(tripsProvider.notifier).loadTrips(),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
              data: (trips) => RefreshIndicator(
                onRefresh: () =>
                    ref.read(tripsProvider.notifier).loadTrips(),
                child: trips.isEmpty
                    ? const Center(
                        child: Text(
                          'No trips yet.\nTap + to create your first trip!',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.grey),
                        ),
                      )
                    : ListView.builder(
                        itemCount: trips.length,
                        itemBuilder: (_, i) => _TripCard(trip: trips[i]),
                      ),
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateDialog(context, ref),
        backgroundColor: const Color(0xFF2196F3),
        foregroundColor: Colors.white,
        child: const Icon(Icons.add),
      ),
    );
  }

  void _showCreateDialog(BuildContext context, WidgetRef ref) {
    final ctrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('New Trip'),
        content: TextField(
          controller: ctrl,
          decoration: const InputDecoration(
            labelText: 'Trip Title',
            hintText: 'e.g., Europe Adventure 2026',
            border: OutlineInputBorder(),
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              final title = ctrl.text.trim();
              if (title.isEmpty) return;
              Navigator.pop(ctx);
              final trip =
                  await ref.read(tripsProvider.notifier).createTrip(title);
              if (context.mounted) context.push('/trips/${trip.id}');
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }
}

class _TripCard extends StatelessWidget {
  final Trip trip;
  const _TripCard({required this.trip});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: ListTile(
        leading: const Icon(Icons.map, color: Color(0xFF2196F3)),
        title: Row(
          children: [
            Expanded(
                child: Text(trip.title,
                    style: const TextStyle(fontWeight: FontWeight.bold))),
            if (trip.isDirty)
              const Icon(Icons.circle, size: 10, color: Colors.orange),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (trip.startDate.isNotEmpty) Text('Start: ${trip.startDate}'),
            if (trip.countries.isNotEmpty)
              Text('Countries: ${trip.countries.join(", ")}'),
            Text('${trip.entries.length} entries'),
          ],
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push('/trips/${trip.id}'),
        isThreeLine: trip.countries.isNotEmpty,
      ),
    );
  }
}
