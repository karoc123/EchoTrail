import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'providers/auth_provider.dart';
import 'screens/login_screen.dart';
import 'screens/folder_picker_screen.dart';
import 'screens/trips_list_screen.dart';
import 'screens/trip_detail_screen.dart';
import 'screens/entry_editor_screen.dart';

class TraceVoyageApp extends ConsumerWidget {
  const TraceVoyageApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(_routerProvider);
    return MaterialApp.router(
      title: 'TraceVoyage',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2196F3)),
        useMaterial3: true,
      ),
      routerConfig: router,
    );
  }
}

final _routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/trips',
    redirect: (context, state) {
      final auth = authState.valueOrNull;
      if (auth == null) return null; // still loading

      final isLoggedIn = auth.isLoggedIn;
      final isConfigured = auth.isConfigured;
      final location = state.matchedLocation;

      if (!isLoggedIn && location != '/login') return '/login';
      if (isLoggedIn && !isConfigured && location != '/folder-picker') {
        return '/folder-picker';
      }
      if (isLoggedIn &&
          isConfigured &&
          (location == '/login' || location == '/folder-picker')) {
        return '/trips';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(
          path: '/folder-picker', builder: (_, __) => const FolderPickerScreen()),
      GoRoute(path: '/trips', builder: (_, __) => const TripsListScreen()),
      GoRoute(
        path: '/trips/:tripId',
        builder: (_, state) =>
            TripDetailScreen(tripId: state.pathParameters['tripId']!),
      ),
      GoRoute(
        path: '/trips/:tripId/entries/:entryId',
        builder: (_, state) => EntryEditorScreen(
          tripId: state.pathParameters['tripId']!,
          entryId: state.pathParameters['entryId']!,
        ),
      ),
    ],
  );
});
