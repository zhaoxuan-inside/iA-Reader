import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/ffi/reader_engine_bridge.dart';

/// 伴读 LLM 设置对话框 (iA Writer 极简范式)
///
/// 配置 I/O 全部经由引擎层 FFI (`config.get` / `config.save` / `config.test`)，
/// Flutter 不直接触碰文件系统（ADR_004）。保存写入
/// `~/.config/ai-reader/llm_config.json`，引擎每次伴读调用时重读，即存即生效。
class LlmSettingsDialog extends StatefulWidget {
  final ReaderEngineBridge bridge;

  const LlmSettingsDialog({super.key, required this.bridge});

  /// 统一入口：书库齿轮 / 伴读抽屉离线提示共用
  static Future<void> show(BuildContext context, ReaderEngineBridge bridge) {
    return showDialog(
      context: context,
      builder: (_) => Dialog(
        backgroundColor: Colors.transparent,
        child: LlmSettingsDialog(bridge: bridge),
      ),
    );
  }

  @override
  State<LlmSettingsDialog> createState() => _LlmSettingsDialogState();
}

class _LlmSettingsDialogState extends State<LlmSettingsDialog> {
  final _endpointController = TextEditingController();
  final _apiKeyController = TextEditingController();
  final _modelController = TextEditingController();
  final _temperatureController = TextEditingController();
  final _maxTokensController = TextEditingController();
  final _systemPromptController = TextEditingController();
  final _timeoutController = TextEditingController();
  final _maxRetriesController = TextEditingController();

  /// 原位校验错误（FEAT-006 REQ-004）：字段 → 错误文案；非空渲染红框 + errorText
  final Map<String, String> _fieldErrors = {};

  bool _loading = true;
  bool _obscureKey = true;
  bool _testing = false;
  bool _saving = false;
  String _configPath = '';
  Map<String, String> _paths = const {};
  /// 掩码占位已废弃：引擎不回显密钥，前端不回填——留空提交=保持既有
  bool _apiKeyConfigured = false;
  String _apiKeyTail = '';

  @override
  void initState() {
    super.initState();
    _loadConfig();
  }

  Future<void> _loadConfig() async {
    final res = await widget.bridge.invoke('config.get', {});
    final cfg = (res.data['config'] as Map<String, dynamic>?) ?? {};
    _endpointController.text = (cfg['endpoint'] ?? '') as String;
    // 密钥不回填（引擎不回显明文）：已配置时以尾号提示，留空提交=保持不变
    _apiKeyController.clear();
    _apiKeyConfigured = (cfg['api_key_configured'] ?? false) as bool;
    _apiKeyTail = (cfg['api_key_tail'] ?? '') as String;
    _modelController.text = (cfg['model_name'] ?? '') as String;
    _temperatureController.text = '${cfg['temperature'] ?? 0.7}';
    _maxTokensController.text = '${cfg['max_output_tokens'] ?? 2048}';
    _systemPromptController.text = (cfg['system_prompt'] ?? '') as String;
    _timeoutController.text = '${cfg['timeout_ms'] ?? 60000}';
    _maxRetriesController.text = '${cfg['max_retries'] ?? 3}';
    _configPath = (res.data['config_path'] ?? '') as String;
    final rawPaths = (res.data['paths'] as Map<String, dynamic>?) ?? {};
    _paths = rawPaths.map((k, v) => MapEntry(k, v?.toString() ?? ''));
    if (mounted) setState(() => _loading = false);
  }

  Map<String, dynamic> _gatherForm() {
    final form = <String, dynamic>{
      'endpoint': _endpointController.text.trim(),
      'model_name': _modelController.text.trim(),
      'temperature': double.tryParse(_temperatureController.text.trim()) ?? 0.7,
      'max_output_tokens':
          int.tryParse(_maxTokensController.text.trim()) ?? 2048,
      'system_prompt': _systemPromptController.text.trim(),
      'timeout_ms': int.tryParse(_timeoutController.text.trim()) ?? 60000,
      'max_retries': int.tryParse(_maxRetriesController.text.trim()) ?? 3,
    };
    // 密钥语义：留空=保持既有（引擎不覆盖）；输入新值=更新；配置态下清空=显式移除
    form['api_key'] = _apiKeyController.text.trim();
    return form;
  }

  String? _validateForm() {
    final cfg = _gatherForm();
    final errors = <String, String>{};
    final endpoint = cfg['endpoint'] as String;
    if (endpoint.isEmpty) {
      errors['endpoint'] = '不能为空';
    } else if (!(endpoint.startsWith('http://') || endpoint.startsWith('https://'))) {
      errors['endpoint'] = '必须以 http:// 或 https:// 开头';
    }
    if ((cfg['model_name'] as String).isEmpty) {
      errors['model'] = '不能为空';
    }
    final temperature = cfg['temperature'] as double;
    if (temperature < 0.0 || temperature > 2.0) {
      errors['temperature'] = '需在 0.0 ~ 2.0';
    }
    final maxTokens = cfg['max_output_tokens'] as int;
    if (maxTokens < 1 || maxTokens > 8192) {
      errors['max_tokens'] = '需在 1 ~ 8192';
    }
    final timeout = cfg['timeout_ms'] as int;
    if (timeout < 1000 || timeout > 120000) {
      errors['timeout'] = '需在 1000 ~ 120000';
    }
    final retries = cfg['max_retries'] as int;
    if (retries < 0 || retries > 5) {
      errors['max_retries'] = '需在 0 ~ 5';
    }
    setState(() => _fieldErrors
      ..clear()
      ..addAll(errors));
    if (errors.isEmpty) return null;
    return errors.values.first;
  }

  Future<void> _testConnection() async {
    final err = _validateForm();
    if (err != null) {
      _toast(err);
      return;
    }
    setState(() => _testing = true);
    final res =
        await widget.bridge.invoke('config.test', {'config': _gatherForm()});
    if (!mounted) return;
    setState(() => _testing = false);
    if (res.isSuccess) {
      final ms = (res.data['latency_ms'] as num?)?.toStringAsFixed(0) ?? '?';
      _toast('连接成功 · ${ms}ms');
    } else {
      _toast(res.message);
    }
  }

  Future<void> _save() async {
    final err = _validateForm();
    if (err != null) {
      _toast(err);
      return;
    }
    setState(() => _saving = true);
    final res =
        await widget.bridge.invoke('config.save', {'config': _gatherForm()});
    if (!mounted) return;
    setState(() => _saving = false);
    if (res.isSuccess) {
      Navigator.of(context).pop();
      _toast('伴读配置已保存，下次划词即生效');
    } else {
      _toast(res.message);
    }
  }

  void _toast(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
          content: Text(msg), duration: const Duration(milliseconds: 2600)),
    );
  }

  @override
  void dispose() {
    _endpointController.dispose();
    _apiKeyController.dispose();
    _modelController.dispose();
    _temperatureController.dispose();
    _maxTokensController.dispose();
    _systemPromptController.dispose();
    super.dispose();
  }

  /// 存储位置区块（ADR_005）：展示集中目录解析结果；重定位经配置文件/环境变量，重启生效。
  Widget _buildStorageSection(
      bool isDark, Color textPrimary, Color textSecondary) {
    final borderColor = isDark ? Colors.white24 : Colors.black12;
    final rows = <(String, String)>[
      ('数据目录', _paths['data'] ?? ''),
      ('配置目录', _paths['config'] ?? ''),
      ('日志目录', _paths['logs'] ?? ''),
      ('书籍副本', _paths['books'] ?? ''),
      ('数据库', _paths['db'] ?? ''),
    ];
    return Container(
      key: const Key('settings_storage_section'),
      padding: const EdgeInsets.all(12.0),
      decoration: BoxDecoration(
        color: isDark
            ? Colors.white.withValues(alpha: 0.04)
            : Colors.black.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(8.0),
        border: Border.all(color: borderColor, width: 1.0),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '存储位置（全部集中于 ${_paths['base'] ?? '~/.ai-reader'}）',
            style: TextStyle(
                fontSize: 12.0,
                fontWeight: FontWeight.w600,
                color: textPrimary),
          ),
          const SizedBox(height: 8.0),
          ...rows.map((r) => Padding(
                padding: const EdgeInsets.only(bottom: 3.0),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 62.0,
                      child: Text(r.$1,
                          style:
                              TextStyle(fontSize: 10.5, color: textSecondary)),
                    ),
                    Expanded(
                      child: Text(r.$2,
                          style:
                              TextStyle(fontSize: 10.5, color: textSecondary)),
                    ),
                  ],
                ),
              )),
          const SizedBox(height: 4.0),
          Text(
            '可通过环境变量 AI_READER_HOME 或配置文件 data_dir/log_dir/books_dir 键重定位，重启后生效',
            style: TextStyle(fontSize: 10.0, color: textSecondary),
          ),
        ],
      ),
    );
  }

  UnderlineInputBorder _hairline(Color c) =>
      UnderlineInputBorder(borderSide: BorderSide(color: c, width: 1.0));

  InputDecoration _decoration(String label, {Widget? suffix, String? errorKey}) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final hairline = _hairline(isDark ? Colors.white24 : Colors.black12);
    final error = errorKey == null ? null : _fieldErrors[errorKey];
    final errorBorder = _hairline(const Color(0xFFE5484D));
    // iA 语言：无框输入，仅一条发丝底线（ADR_006）；校验失败红框 + 原位错误文案
    return InputDecoration(
      labelText: label,
      labelStyle: TextStyle(
          fontSize: 12.5, color: isDark ? Colors.white60 : Colors.black54),
      isDense: true,
      suffixIcon: suffix,
      errorText: error,
      errorStyle: const TextStyle(fontSize: 10.5, height: 1.1),
      errorMaxLines: 2,
      border: hairline,
      enabledBorder: error != null ? errorBorder : hairline,
      focusedBorder: error != null
          ? errorBorder
          : _hairline(Theme.of(context).colorScheme.primary),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surface = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final textPrimary =
        isDark ? Colors.white.withValues(alpha: 0.92) : Colors.black87;
    final textSecondary = isDark ? Colors.white54 : Colors.black45;

    return Container(
      width: 460.0,
      constraints: const BoxConstraints(maxHeight: 640.0),
      padding: const EdgeInsets.all(24.0),
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(14.0),
      ),
      child: _loading
          ? const SizedBox(
              height: 120.0,
              child: Center(child: CircularProgressIndicator(strokeWidth: 2.0)),
            )
          : Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '伴读 LLM 设置',
                  style: TextStyle(
                    fontSize: 18.0,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.3,
                    color: textPrimary,
                  ),
                ),
                const SizedBox(height: 4.0),
                Text(
                  '本地优先 · 凭据仅存于本机用户配置，划词伴读即用即读',
                  style: TextStyle(fontSize: 12.0, color: textSecondary),
                ),
                const SizedBox(height: 18.0),
                Flexible(
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        TextField(
                          key: const Key('settings_endpoint'),
                          controller: _endpointController,
                          style: TextStyle(fontSize: 13.0, color: textPrimary),
                          decoration: _decoration(
                              'API Endpoint (OpenAI 兼容 /chat/completions)',
                              errorKey: 'endpoint'),
                        ),
                        const SizedBox(height: 12.0),
                        TextField(
                          key: const Key('settings_api_key'),
                          controller: _apiKeyController,
                          obscureText: _obscureKey,
                          style: TextStyle(fontSize: 13.0, color: textPrimary),
                          decoration: _decoration(
                            _apiKeyConfigured
                                ? 'API Key（已配置，尾号 $_apiKeyTail；修改请直接输入新值，清空并保存即移除）'
                                : 'API Key（未配置）',
                            suffix: IconButton(
                              icon: Icon(
                                _obscureKey
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                                size: 17.0,
                                color: textSecondary,
                              ),
                              onPressed: () =>
                                  setState(() => _obscureKey = !_obscureKey),
                            ),
                          ),
                        ),
                        const SizedBox(height: 12.0),
                        TextField(
                          key: const Key('settings_model'),
                          controller: _modelController,
                          style: TextStyle(fontSize: 13.0, color: textPrimary),
                          decoration: _decoration('模型名称', errorKey: 'model'),
                        ),
                        const SizedBox(height: 12.0),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                key: const Key('settings_temperature'),
                                controller: _temperatureController,
                                keyboardType:
                                    const TextInputType.numberWithOptions(
                                        decimal: true),
                                inputFormatters: [
                                  FilteringTextInputFormatter.allow(
                                      RegExp(r'[0-9.]')),
                                ],
                                style: TextStyle(
                                    fontSize: 13.0, color: textPrimary),
                                decoration: _decoration('Temperature (0.0~2.0)',
                                    errorKey: 'temperature'),
                              ),
                            ),
                            const SizedBox(width: 12.0),
                            Expanded(
                              child: TextField(
                                key: const Key('settings_max_tokens'),
                                controller: _maxTokensController,
                                keyboardType: TextInputType.number,
                                inputFormatters: [
                                  FilteringTextInputFormatter.digitsOnly
                                ],
                                style: TextStyle(
                                    fontSize: 13.0, color: textPrimary),
                                decoration: _decoration('Max Tokens (1~8192)',
                                    errorKey: 'max_tokens'),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12.0),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                key: const Key('settings_timeout'),
                                controller: _timeoutController,
                                keyboardType: TextInputType.number,
                                inputFormatters: [
                                  FilteringTextInputFormatter.digitsOnly
                                ],
                                style: TextStyle(
                                    fontSize: 13.0, color: textPrimary),
                                decoration: _decoration('超时 ms (1000~120000)',
                                    errorKey: 'timeout'),
                              ),
                            ),
                            const SizedBox(width: 12.0),
                            Expanded(
                              child: TextField(
                                key: const Key('settings_max_retries'),
                                controller: _maxRetriesController,
                                keyboardType: TextInputType.number,
                                inputFormatters: [
                                  FilteringTextInputFormatter.digitsOnly
                                ],
                                style: TextStyle(
                                    fontSize: 13.0, color: textPrimary),
                                decoration: _decoration('重试次数 (0~5)',
                                    errorKey: 'max_retries'),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12.0),
                        TextField(
                          key: const Key('settings_system_prompt'),
                          controller: _systemPromptController,
                          maxLines: 3,
                          style: TextStyle(fontSize: 13.0, color: textPrimary),
                          decoration: _decoration('伴读人设 System Prompt'),
                        ),
                        if (_configPath.isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 10.0),
                            child: Text(
                              '配置文件：$_configPath',
                              style: TextStyle(
                                  fontSize: 10.5, color: textSecondary),
                            ),
                          ),
                        const SizedBox(height: 16.0),
                        _buildStorageSection(
                            isDark, textPrimary, textSecondary),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20.0),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      key: const Key('settings_test_button'),
                      onPressed: _testing ? null : _testConnection,
                      child: _testing
                          ? const SizedBox(
                              width: 14.0,
                              height: 14.0,
                              child:
                                  CircularProgressIndicator(strokeWidth: 2.0),
                            )
                          : const Text('测试连接',
                              style: TextStyle(fontSize: 13.0)),
                    ),
                    const SizedBox(width: 8.0),
                    TextButton(
                      onPressed:
                          _saving ? null : () => Navigator.of(context).pop(),
                      child: const Text('取消', style: TextStyle(fontSize: 13.0)),
                    ),
                    const SizedBox(width: 8.0),
                    TextButton(
                      key: const Key('settings_save_button'),
                      onPressed: _saving ? null : _save,
                      style: TextButton.styleFrom(
                        foregroundColor:
                            Theme.of(context).colorScheme.primary,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14.0, vertical: 12.0),
                      ),
                      child: _saving
                          ? const SizedBox(
                              width: 14.0,
                              height: 14.0,
                              child:
                                  CircularProgressIndicator(strokeWidth: 2.0),
                            )
                          : const Text('保存',
                              style: TextStyle(
                                  fontSize: 13.0, fontWeight: FontWeight.w600)),
                    ),
                  ],
                ),
              ],
            ),
    );
  }
}
