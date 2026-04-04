import 'entry.dart';

class Trip {
  final String id;
  String title;
  String odometerKm;
  String titleImage;
  String descriptionMd;
  bool draft;
  List<Entry> entries;
  bool isDirty;

  Trip({
    required this.id,
    required this.title,
    this.odometerKm = '',
    this.titleImage = '',
    this.descriptionMd = '',
    this.draft = false,
    List<Entry>? entries,
    this.isDirty = false,
  }) : entries = entries ?? [];

  /// Date of the earliest entry, or empty string.
  String get startDate {
    final dates = entries
        .map((e) => e.date)
        .where((d) => d.isNotEmpty)
        .toList()
      ..sort();
    return dates.isEmpty ? '' : dates.first;
  }

  /// Unique set of countries across all entries.
  List<String> get countries => entries
      .map((e) => e.country)
      .where((c) => c.isNotEmpty)
      .toSet()
      .toList();

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'odometerKm': odometerKm,
        'titleImage': titleImage,
        'descriptionMd': descriptionMd,
        'draft': draft,
        'entries': entries.map((e) => e.toJson()).toList(),
        'isDirty': isDirty,
      };

  factory Trip.fromJson(Map<String, dynamic> json) => Trip(
        id: json['id'] as String,
        title: json['title'] as String,
        odometerKm: json['odometerKm'] as String? ?? '',
        titleImage: json['titleImage'] as String? ?? '',
        descriptionMd: json['descriptionMd'] as String? ?? '',
        draft: json['draft'] as bool? ?? false,
        entries: (json['entries'] as List<dynamic>?)
                ?.map((e) => Entry.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [],
        isDirty: json['isDirty'] as bool? ?? false,
      );
}
