import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';
import '../services/github_service.dart';

class FolderPickerScreen extends ConsumerStatefulWidget {
  const FolderPickerScreen({super.key});

  @override
  ConsumerState<FolderPickerScreen> createState() => _FolderPickerScreenState();
}

class _FolderPickerScreenState extends ConsumerState<FolderPickerScreen> {
  String _currentPath = '';
  List<String> _breadcrumbs = [];
  List<Map<String, dynamic>> _items = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadContents('');
  }

  GitHubService? _service() {
    final auth = ref.read(authProvider).valueOrNull;
    if (auth == null || !auth.isLoggedIn) return null;
    return GitHubService(
      token: auth.token!,
      repoOwner: auth.repoOwner!,
      repoName: auth.repoName!,
    );
  }

  Future<void> _loadContents(String path) async {
    setState(() {
      _isLoading = true;
      _error = null;
      _currentPath = path;
      _breadcrumbs = path.isEmpty ? [] : path.split('/');
    });
    try {
      final svc = _service();
      if (svc == null) throw Exception('Not authenticated');
      final items = await svc.getRepoTree(path);
      setState(() {
        _items = items.where((i) => i['type'] == 'dir').toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _selectFolder(String path) async {
    await ref.read(authProvider.notifier).setTripsPath(path);
    if (mounted) context.go('/trips');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Select Trips Folder'),
        backgroundColor: const Color(0xFF2196F3),
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Breadcrumb bar
          Container(
            width: double.infinity,
            color: Colors.grey.shade100,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  GestureDetector(
                    onTap: () => _loadContents(''),
                    child: const Text('root',
                        style: TextStyle(color: Color(0xFF2196F3))),
                  ),
                  ..._breadcrumbs.asMap().entries.map((e) {
                    final path =
                        _breadcrumbs.sublist(0, e.key + 1).join('/');
                    return Row(children: [
                      const Text(' / ', style: TextStyle(color: Colors.grey)),
                      GestureDetector(
                        onTap: () => _loadContents(path),
                        child: Text(e.value,
                            style:
                                const TextStyle(color: Color(0xFF2196F3))),
                      ),
                    ]);
                  }),
                ],
              ),
            ),
          ),
          // "Use this folder" button
          Padding(
            padding: const EdgeInsets.all(8),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.folder_open),
                label: Text(_currentPath.isEmpty
                    ? 'Use repository root'
                    : 'Use "$_currentPath"'),
                onPressed: () => _selectFolder(_currentPath),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF2196F3),
                  foregroundColor: Colors.white,
                ),
              ),
            ),
          ),
          const Divider(height: 1),
          // Directory listing
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(_error!,
                                style: const TextStyle(color: Colors.red)),
                            const SizedBox(height: 8),
                            ElevatedButton(
                              onPressed: () => _loadContents(_currentPath),
                              child: const Text('Retry'),
                            ),
                          ],
                        ),
                      )
                    : _items.isEmpty
                        ? const Center(
                            child: Text('No subdirectories found'))
                        : ListView.builder(
                            itemCount: _items.length,
                            itemBuilder: (_, i) {
                              final name = _items[i]['name'] as String;
                              final itemPath = _currentPath.isEmpty
                                  ? name
                                  : '$_currentPath/$name';
                              return ListTile(
                                leading: const Icon(Icons.folder,
                                    color: Color(0xFFFFA000)),
                                title: Text(name),
                                trailing: const Icon(Icons.chevron_right),
                                onTap: () => _loadContents(itemPath),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }
}
