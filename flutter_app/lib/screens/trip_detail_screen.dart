import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/trips_provider.dart';
import '../models/trip.dart';
import '../models/entry.dart';

class TripDetailScreen extends ConsumerStatefulWidget {
  final String tripId;
  const TripDetailScreen({super.key, required this.tripId});

  @override
  ConsumerState<TripDetailScreen> createState() => _TripDetailScreenState();
}

class _TripDetailScreenState extends ConsumerState<TripDetailScreen> {
  final _titleCtrl = TextEditingController();
  final _odometerCtrl = TextEditingController();
  final _titleImageCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  bool _draft = false;
  bool _initialized = false;
  Trip? _trip;

  @override
  void dispose() {
    _titleCtrl.dispose();
    _odometerCtrl.dispose();
    _titleImageCtrl.dispose();
    _descCtrl.dispose();
    super.dispose();
  }

  void _initFromTrip(Trip trip) {
    if (_initialized) return;
    _titleCtrl.text = trip.title;
    _odometerCtrl.text = trip.odometerKm;
    _titleImageCtrl.text = trip.titleImage;
    _descCtrl.text = trip.descriptionMd;
    _draft = trip.draft;
    _initialized = true;
  }

  Future<void> _save() async {
    if (_trip == null) return;
    final updated = Trip(
      id: _trip!.id,
      title: _titleCtrl.text.trim(),
      odometerKm: _odometerCtrl.text.trim(),
      titleImage: _titleImageCtrl.text.trim(),
      descriptionMd: _descCtrl.text,
      draft: _draft,
      entries: _trip!.entries,
    );
    await ref.read(tripsProvider.notifier).updateTrip(updated);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Trip saved'), duration: Duration(seconds: 1)),
      );
    }
  }

  Future<void> _deleteEntry(String entryId) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Entry'),
        content: const Text('Are you sure?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red, foregroundColor: Colors.white),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (ok == true) {
      await ref.read(tripsProvider.notifier).deleteEntry(widget.tripId, entryId);
    }
  }

  void _addEntry() {
    final now = DateTime.now();
    final date =
        '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
    context.push('/trips/${widget.tripId}/entries/$date-new-entry');
  }

  @override
  Widget build(BuildContext context) {
    return ref.watch(tripsProvider).when(
      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (e, _) => Scaffold(body: Center(child: Text('Error: $e'))),
      data: (trips) {
        final trip = trips.firstWhere(
          (t) => t.id == widget.tripId,
          orElse: () => Trip(id: widget.tripId, title: ''),
        );
        _initFromTrip(trip);
        _trip = trip;

        return Scaffold(
          appBar: AppBar(
            title: Text(trip.title.isEmpty ? 'Trip' : trip.title),
            backgroundColor: const Color(0xFF2196F3),
            foregroundColor: Colors.white,
            actions: [
              IconButton(
                  icon: const Icon(Icons.save),
                  onPressed: _save,
                  tooltip: 'Save'),
            ],
          ),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Trip Info',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                TextField(
                  controller: _titleCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Title',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _odometerCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Odometer (km)',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _titleImageCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Title image filename (title.*)',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 8),
                SwitchListTile.adaptive(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Draft'),
                  subtitle: const Text('Draft trips are skipped by the generator'),
                  value: _draft,
                  onChanged: (value) => setState(() => _draft = value),
                ),
                const SizedBox(height: 16),
                Text('Description',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                TextField(
                  controller: _descCtrl,
                  decoration: const InputDecoration(
                    hintText: 'Enter Markdown description…',
                    border: OutlineInputBorder(),
                    alignLabelWithHint: true,
                  ),
                  maxLines: 6,
                  minLines: 4,
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Text('Entries',
                        style: Theme.of(context).textTheme.titleMedium),
                    const Spacer(),
                    Text('${trip.entries.length} entries',
                        style: const TextStyle(color: Colors.grey)),
                  ],
                ),
                const SizedBox(height: 8),
                if (trip.entries.isEmpty)
                  const Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Text('No entries yet. Tap + to add one.',
                          style: TextStyle(color: Colors.grey)),
                    ),
                  )
                else
                  ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: trip.entries.length,
                    itemBuilder: (_, i) {
                      final entry = trip.entries[i];
                      return _EntryTile(
                        entry: entry,
                        tripId: widget.tripId,
                        onDelete: () => _deleteEntry(entry.id),
                      );
                    },
                  ),
              ],
            ),
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: _addEntry,
            backgroundColor: const Color(0xFF2196F3),
            foregroundColor: Colors.white,
            child: const Icon(Icons.add),
          ),
        );
      },
    );
  }
}

class _EntryTile extends StatelessWidget {
  final Entry entry;
  final String tripId;
  final VoidCallback onDelete;

  const _EntryTile({
    required this.entry,
    required this.tripId,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Dismissible(
      key: Key(entry.id),
      direction: DismissDirection.endToStart,
      confirmDismiss: (_) async {
        onDelete();
        return false;
      },
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 16),
        color: Colors.red,
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      child: Card(
        child: ListTile(
          leading: const Icon(Icons.article_outlined),
          title: Text(
              entry.title.isEmpty ? entry.id : entry.title),
          subtitle: Text(
              '${entry.date}${entry.country.isNotEmpty ? ' · ${entry.country}' : ''}${entry.draft ? ' · draft' : ''}'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () =>
              context.push('/trips/$tripId/entries/${entry.id}'),
        ),
      ),
    );
  }
}
