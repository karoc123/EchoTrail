class Entry {
  final String id;
  String title;
  String date;
  String country;
  String weather;
  String temperatureC;
  double? lat;
  double? lon;
  String textMd;
  bool draft;
  List<MediaItem> media;
  bool isDirty;

  Entry({
    required this.id,
    this.title = '',
    this.date = '',
    this.country = '',
    this.weather = '',
    this.temperatureC = '',
    this.lat,
    this.lon,
    this.textMd = '',
    this.draft = false,
    List<MediaItem>? media,
    this.isDirty = false,
  }) : media = media ?? [];

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'date': date,
        'country': country,
        'weather': weather,
        'temperatureC': temperatureC,
        'lat': lat,
        'lon': lon,
        'textMd': textMd,
        'draft': draft,
        'media': media.map((m) => m.toJson()).toList(),
        'isDirty': isDirty,
      };

  factory Entry.fromJson(Map<String, dynamic> json) => Entry(
        id: json['id'] as String,
      title: json['title'] as String? ?? json['pointName'] as String? ?? '',
        date: json['date'] as String? ?? '',
        country: json['country'] as String? ?? '',
        weather: json['weather'] as String? ?? '',
        temperatureC: json['temperatureC'] as String? ?? '',
        lat: (json['lat'] as num?)?.toDouble(),
        lon: (json['lon'] as num?)?.toDouble(),
        textMd: json['textMd'] as String? ?? '',
      draft: json['draft'] as bool? ?? false,
        media: (json['media'] as List<dynamic>?)
                ?.map((m) => MediaItem.fromJson(m as Map<String, dynamic>))
                .toList() ??
            [],
        isDirty: json['isDirty'] as bool? ?? false,
      );
}

class MediaItem {
  String name;
  String description;

  MediaItem({required this.name, this.description = ''});

  Map<String, dynamic> toJson() => {'name': name, 'description': description};

  factory MediaItem.fromJson(Map<String, dynamic> json) => MediaItem(
        name: json['name'] as String,
        description: json['description'] as String? ?? '',
      );
}
