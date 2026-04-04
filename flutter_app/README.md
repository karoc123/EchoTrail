# TraceVoyage App

A Flutter application for offline-first editing and GitHub synchronisation of TraceVoyage trip data.

## Features

- **Offline-first**: Edit trips locally without an internet connection
- **GitHub sync**: Push changes to GitHub with a single tap
- **Full trip management**: Create, edit and delete trips and journal entries
- **Markdown editor**: Rich journal entries with live preview
- **All entry fields**: Date, country, weather, temperature, GPS coordinates and point name

## Getting Started

### Prerequisites

- [Flutter](https://flutter.dev/docs/get-started/install) ≥ 3.19.0
- A GitHub account with a [Personal Access Token (PAT)](https://github.com/settings/tokens)
  - Required scopes: `repo` (full control of private repositories) or `public_repo` for public repos
- A GitHub repository containing your TraceVoyage trip data

### Run from source

```bash
cd flutter_app
flutter pub get
flutter run
```

### Download pre-built APK

1. Go to the **Actions** tab in this repository
2. Click **"Build TraceVoyage App (APK)"**
3. Click **"Run workflow"** → choose build type → **"Run workflow"**
4. After the build completes (~5 minutes), download the APK from the **Artifacts** section

## Usage

### 1. Login

Enter your GitHub repository URL and a Personal Access Token with `repo` scope.
The token is stored in the device's encrypted storage — never in plain text.

### 2. Select Trips Folder

Browse your repository's directory tree and select the folder that contains the `trips/`
subdirectory. Use **"Use repository root"** if `trips/` is at the root of your repo.

### 3. Download trips

On the **My Trips** screen, tap the **download icon** (↓) in the top bar to fetch all
trip data from GitHub to your device.

### 4. Edit offline

- Tap a trip card to open it
- Edit the title, odometer and description, then tap **Save**
- Tap **+** to add a new journal entry
- Fill in all metadata fields and write in Markdown; toggle **Preview** for rendered output
- Changes are saved immediately to local storage

### 5. Sync to GitHub

Tap the **sync icon** (↻) in the top bar. All locally modified files are uploaded.
If a file changed on GitHub in the meantime, the local version wins
(force-write using the current remote SHA).

## Data Format

Trip data uses the TraceVoyage format:

```
trips/
└── {trip-id}/
    ├── description.md       # TOML front matter + Markdown description
    └── entries/
        └── {YYYY-MM-DD-slug}/
            ├── text.md      # TOML front matter + Markdown journal entry
            └── media.json   # media file metadata
```

**description.md example:**
```toml
+++
title = 'My Europe Trip'
odometer_km = '3,240'
+++

# My Europe Trip

Trip description in Markdown...
```

**text.md example:**
```toml
+++
date = 2026-03-31
country = 'Germany'
weather = 'Cloudy, light wind'
temperature_c = 9
lat = 52.52
lon = 13.405
point_name = 'Berlin – Starting Point'
+++

# Departure from Berlin

Journal entry in Markdown...
```

## Project Structure

```
flutter_app/
├── lib/
│   ├── main.dart                        # App entry point
│   ├── app.dart                         # GoRouter + theme
│   ├── models/
│   │   ├── trip.dart                    # Trip data model
│   │   └── entry.dart                   # Entry + MediaItem models
│   ├── services/
│   │   ├── toml_service.dart            # Custom +++ front-matter parser
│   │   ├── local_storage_service.dart   # Local file I/O + dirty tracking
│   │   └── github_service.dart          # GitHub Contents API client
│   ├── providers/
│   │   ├── auth_provider.dart           # Authentication state
│   │   ├── trips_provider.dart          # Trip/entry CRUD
│   │   └── sync_provider.dart           # GitHub sync logic
│   └── screens/
│       ├── login_screen.dart            # GitHub PAT + repo URL form
│       ├── folder_picker_screen.dart    # Repository folder browser
│       ├── trips_list_screen.dart       # Trip list with sync status
│       ├── trip_detail_screen.dart      # Trip editor + entry list
│       └── entry_editor_screen.dart     # Entry form + Markdown editor
└── android/                             # Android platform configuration
```

## Dependencies

| Package | Purpose |
|---|---|
| `flutter_riverpod` | State management |
| `go_router` | Navigation |
| `http` | GitHub REST API calls |
| `flutter_secure_storage` | Encrypted token storage |
| `path_provider` | App documents directory |
| `shared_preferences` | Non-sensitive settings (repo URL, folder path) |
| `flutter_markdown` | Markdown rendering in preview mode |
| `crypto` | SHA computation |
| `intl` | Date formatting |
