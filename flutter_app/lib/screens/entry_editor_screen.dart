import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../providers/trips_provider.dart';
import '../models/entry.dart';

class EntryEditorScreen extends ConsumerStatefulWidget {
  final String tripId;
  final String entryId;

  const EntryEditorScreen(
      {super.key, required this.tripId, required this.entryId});

  @override
  ConsumerState<EntryEditorScreen> createState() => _EntryEditorScreenState();
}

class _EntryEditorScreenState extends ConsumerState<EntryEditorScreen> {
  final _dateCtrl = TextEditingController();
  final _countryCtrl = TextEditingController();
  final _weatherCtrl = TextEditingController();
  final _tempCtrl = TextEditingController();
  final _latCtrl = TextEditingController();
  final _lonCtrl = TextEditingController();
  final _titleCtrl = TextEditingController();
  final _textCtrl = TextEditingController();

  bool _initialized = false;
  bool _isPreview = false;
  bool _isNew = false;
  bool _draft = false;
  List<MediaItem> _media = [];

  @override
  void dispose() {
    _dateCtrl.dispose();
    _countryCtrl.dispose();
    _weatherCtrl.dispose();
    _tempCtrl.dispose();
    _latCtrl.dispose();
    _lonCtrl.dispose();
    _titleCtrl.dispose();
    _textCtrl.dispose();
    super.dispose();
  }

  void _initFromEntry(Entry entry) {
    if (_initialized) return;
    _dateCtrl.text = entry.date;
    _countryCtrl.text = entry.country;
    _weatherCtrl.text = entry.weather;
    _tempCtrl.text = entry.temperatureC;
    _latCtrl.text = entry.lat?.toString() ?? '';
    _lonCtrl.text = entry.lon?.toString() ?? '';
    _titleCtrl.text = entry.title;
    _textCtrl.text = entry.textMd;
    _draft = entry.draft;
    _media = entry.media;
    _initialized = true;
  }

  static String _slugify(String text) => text
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');

  String _buildEntryId() {
    final date = _dateCtrl.text.trim();
    final name = _titleCtrl.text.trim();
    if (name.isNotEmpty) return '$date-${_slugify(name)}';
    return date.isEmpty ? widget.entryId : '$date-entry';
  }

  Future<void> _save() async {
    final newId = _isNew ? _buildEntryId() : widget.entryId;
    final entry = Entry(
      id: newId,
      title: _titleCtrl.text.trim(),
      date: _dateCtrl.text.trim(),
      country: _countryCtrl.text.trim(),
      weather: _weatherCtrl.text.trim(),
      temperatureC: _tempCtrl.text.trim(),
      lat: double.tryParse(_latCtrl.text.trim()),
      lon: double.tryParse(_lonCtrl.text.trim()),
      textMd: _textCtrl.text,
      draft: _draft,
      media: _media,
    );

    if (_isNew) {
      await ref.read(tripsProvider.notifier).createEntry(widget.tripId, entry);
    } else {
      await ref.read(tripsProvider.notifier).updateEntry(widget.tripId, entry);
    }

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Entry saved'), duration: Duration(seconds: 1)),
      );
      Navigator.of(context).pop();
    }
  }

  Future<void> _pickDate() async {
    final initial = DateTime.tryParse(_dateCtrl.text) ?? DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked != null && mounted) {
      setState(() {
        _dateCtrl.text =
            '${picked.year}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return ref.watch(tripsProvider).when(
      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (e, _) => Scaffold(body: Center(child: Text('Error: $e'))),
      data: (trips) {
        Entry? entry;
        try {
          final trip = trips.firstWhere((t) => t.id == widget.tripId);
          entry = trip.entries.firstWhere((e) => e.id == widget.entryId);
          _isNew = false;
        } catch (_) {
          _isNew = true;
          entry = Entry(id: widget.entryId);
        }
        _initFromEntry(entry);

        return Scaffold(
          appBar: AppBar(
            title: Text(_isNew ? 'New Entry' : 'Edit Entry'),
            backgroundColor: const Color(0xFF2196F3),
            foregroundColor: Colors.white,
            actions: [
              IconButton(
                icon: Icon(_isPreview ? Icons.edit : Icons.preview),
                onPressed: () => setState(() => _isPreview = !_isPreview),
                tooltip: _isPreview ? 'Edit' : 'Preview',
              ),
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
                // Date picker
                GestureDetector(
                  onTap: _pickDate,
                  child: AbsorbPointer(
                    child: TextField(
                      controller: _dateCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Date',
                        border: OutlineInputBorder(),
                        suffixIcon: Icon(Icons.calendar_today),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _titleCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Title',
                    border: OutlineInputBorder(),
                  ),
                ),
                SwitchListTile.adaptive(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Draft'),
                  subtitle: const Text('Draft entries are skipped by the generator'),
                  value: _draft,
                  onChanged: (value) => setState(() => _draft = value),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _countryCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Country',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _weatherCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Weather',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _tempCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Temperature (°C)',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType:
                      const TextInputType.numberWithOptions(signed: true),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _latCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Latitude',
                          border: OutlineInputBorder(),
                        ),
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: _lonCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Longitude',
                          border: OutlineInputBorder(),
                        ),
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Text('Journal Entry',
                        style: Theme.of(context).textTheme.titleMedium),
                    const Spacer(),
                    ToggleButtons(
                      isSelected: [!_isPreview, _isPreview],
                      onPressed: (i) =>
                          setState(() => _isPreview = i == 1),
                      borderRadius: BorderRadius.circular(8),
                      children: const [
                        Padding(
                            padding: EdgeInsets.symmetric(horizontal: 12),
                            child: Text('Edit')),
                        Padding(
                            padding: EdgeInsets.symmetric(horizontal: 12),
                            child: Text('Preview')),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                if (_isPreview)
                  Container(
                    width: double.infinity,
                    constraints: const BoxConstraints(minHeight: 200),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.grey.shade300),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: MarkdownBody(
                      data: _textCtrl.text.isEmpty
                          ? '_No content yet_'
                          : _textCtrl.text,
                    ),
                  )
                else
                  TextField(
                    controller: _textCtrl,
                    decoration: const InputDecoration(
                      hintText: 'Write your journal entry in Markdown…',
                      border: OutlineInputBorder(),
                      alignLabelWithHint: true,
                    ),
                    maxLines: 15,
                    minLines: 8,
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}
