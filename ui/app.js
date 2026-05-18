const { createApp, ref, reactive, computed, onMounted, nextTick, watch } = Vue;

const I18N = {
    zh: {
        app_title: 'VocalSieve',
        tooltip_theme: '切换外观',
        tooltip_settings: '偏好设置',
        setup_title: '配置筛选任务',
        source_dir: '源数据目录',
        output_dir: '输出目录',
        select_dir: '浏览',
        placeholder_source: '选择包含音频文件的文件夹',
        placeholder_output: '筛选结果将保存到这里',
        preset_title: '处理模式',
        preset_perf: '速度优先',
        preset_perf_desc: '优先完成首轮筛查，适合快速确认素材范围。',
        preset_bal: '均衡',
        preset_bal_desc: '默认推荐，速度与识别稳定性更均衡。',
        preset_qual: '质量优先',
        preset_qual_desc: '适合正式产出，会消耗更多时间与显存。',
        target_lang: '音频语言',
        top_n: '保留数量',
        adv_settings: '高级设置',
        adv_rms: '最低音量 (RMS)',
        adv_centroid: '最低频率质心 (Hz)',
        adv_duration: '最短时长 (秒)',
        state_idle: '等待开始',
        state_running: '正在筛选',
        state_done: '任务完成',
        state_stopped: '任务中断',
        progress_idle: '选择目录后即可启动任务',
        btn_start: '开始运行',
        btn_running: '运行中',
        btn_restart: '重新运行',
        btn_cancel: '点击中止',
        view_logs: '查看日志',
        settings_title: '偏好设置',
        btn_close: '关闭',
        tab_sys: '通用',
        tab_env: '环境与检测',
        tab_log: '运行日志',
        lang_setting: '语言',
        lang_zh: '简体中文',
        lang_en: 'English',
        env_py: 'Python 核心',
        env_torch: 'PyTorch 引擎',
        env_gpu: 'GPU 加速',
        env_whisper: 'Whisper 核心',
        env_ffmpeg: 'FFmpeg 组件',
        env_scanning: '正在检测环境...',
        log_empty: '暂无运行记录',
        btn_copy: '复制',
        btn_export: '导出',
        alert_title: '系统提示',
        alert_desc: '检测到以下可能影响运行的问题：',
        alert_btn: '知道了',
        bridge_missing: '未检测到 PyWebview 桥接，浏览器预览模式下无法启动后端任务。',
        copied: '日志已复制到剪贴板',
        exported: '日志已导出至',
        copy_failed: '复制失败',
        export_failed: '导出失败',
        dir_failed: '目录选择失败',
        canceling: '已发送取消信号，等待当前文件结束',
        starting_engine: '正在请求底层处理引擎...',
        pipeline_started: '后端任务已启动',
        pipeline_done: '提取结束',
        pipeline_cancelled: '任务已取消',
        pipeline_failed: '任务失败',
        no_gpu: '未探测到兼容的 NVIDIA GPU，Whisper 可能会以 CPU 模式运行。'
    },
    en: {
        app_title: 'VocalSieve',
        tooltip_theme: 'Switch appearance',
        tooltip_settings: 'Preferences',
        setup_title: 'Configure The Pipeline',
        source_dir: 'Source Folder',
        output_dir: 'Output Folder',
        select_dir: 'Browse',
        placeholder_source: 'Choose the folder that contains audio files',
        placeholder_output: 'Filtered results will be written here',
        preset_title: 'Processing Mode',
        preset_perf: 'Speed First',
        preset_perf_desc: 'Optimized for quick first-pass review of a large folder.',
        preset_bal: 'Balanced',
        preset_bal_desc: 'Recommended default with steadier speed and recognition quality.',
        preset_qual: 'Quality',
        preset_qual_desc: 'Best for final export when longer runtime is acceptable.',
        target_lang: 'Audio Language',
        top_n: 'Retention Count',
        adv_settings: 'Advanced Settings',
        adv_rms: 'Min Volume (RMS)',
        adv_centroid: 'Min Spectral Centroid (Hz)',
        adv_duration: 'Min Duration (s)',
        state_idle: 'Ready',
        state_running: 'Filtering',
        state_done: 'Completed',
        state_stopped: 'Interrupted',
        progress_idle: 'Select folders to start the pipeline',
        btn_start: 'Start Run',
        btn_running: 'Running',
        btn_restart: 'Run Again',
        btn_cancel: 'Click To Abort',
        view_logs: 'View Logs',
        settings_title: 'Preferences',
        btn_close: 'Close',
        tab_sys: 'General',
        tab_env: 'Diagnostics',
        tab_log: 'Logs',
        lang_setting: 'Language',
        lang_zh: '简体中文',
        lang_en: 'English',
        env_py: 'Python Core',
        env_torch: 'PyTorch Engine',
        env_gpu: 'GPU Acceleration',
        env_whisper: 'Whisper Core',
        env_ffmpeg: 'FFmpeg Component',
        env_scanning: 'Scanning environment...',
        log_empty: 'No records available',
        btn_copy: 'Copy',
        btn_export: 'Export',
        alert_title: 'System Notice',
        alert_desc: 'The following issues may affect execution:',
        alert_btn: 'Got it',
        bridge_missing: 'PyWebview bridge is unavailable. Backend tasks cannot start in browser preview mode.',
        copied: 'Logs copied to clipboard',
        exported: 'Logs exported to',
        copy_failed: 'Copy failed',
        export_failed: 'Export failed',
        dir_failed: 'Directory selection failed',
        canceling: 'Cancel signal sent; waiting for the current file to finish',
        starting_engine: 'Requesting backend engine...',
        pipeline_started: 'Backend task started',
        pipeline_done: 'Extraction completed',
        pipeline_cancelled: 'Task cancelled',
        pipeline_failed: 'Task failed',
        no_gpu: 'No compatible NVIDIA GPU was detected. Whisper may run on CPU.'
    }
};

const LANG_MAP = {
    zh: { auto: '自动检测', ja: '日语', zh: '中文', en: '英语', ko: '韩语', de: '德语', fr: '法语', es: '西班牙语', ru: '俄语', it: '意大利语', pt: '葡萄牙语' },
    en: { auto: 'Auto', ja: 'Japanese', zh: 'Chinese', en: 'English', ko: 'Korean', de: 'German', fr: 'French', es: 'Spanish', ru: 'Russian', it: 'Italian', pt: 'Portuguese' }
};

createApp({
    setup() {
        const currentLang = ref(localStorage.getItem('vocalsieve.lang') || 'zh');
        const isDarkTheme = ref(localStorage.getItem('vocalsieve.theme') !== 'light');
        const bridgeReady = ref(false);

        const t = (key) => I18N[currentLang.value]?.[key] || I18N.zh[key] || key;

        const envLoaded = ref(false);
        const env = reactive({});
        const supportedLanguages = ref([{ code: 'auto', name: '自动检测' }]);

        const config = reactive({
            source_dir: '',
            output_dir: '',
            preset: 'balanced',
            target_language: 'auto',
            top_n: 1200,
            min_rms: 0.015,
            min_centroid: 1000.0,
            min_duration: 0.4
        });

        const isAdvancedOpen = ref(false);
        const isLangDropdownOpen = ref(false);
        const isDisplayLangDropdownOpen = ref(false);
        const isRunning = ref(false);
        const runFinished = ref(false);
        const runStopped = ref(false);
        const currentStage = ref('');
        const currentCount = ref(0);
        const totalCount = ref(0);
        const currentItemName = ref('');

        const logs = ref([]);
        const consoleBody = ref(null);
        const isSettingsOpen = ref(false);
        const activeTab = ref('sys');
        const isAlertOpen = ref(false);
        const alertIssues = ref([]);

        const canStart = computed(() => Boolean(config.source_dir && config.output_dir));
        const progressPercent = computed(() => {
            if (runFinished.value) return 100;
            if (totalCount.value === 0) return 0;
            return Math.min(100, Math.max(0, (currentCount.value / totalCount.value) * 100));
        });
        const selectedLangName = computed(() => getLangName(config.target_language));
        const displayLanguageOptions = computed(() => [
            { code: 'zh', label: t('lang_zh') },
            { code: 'en', label: t('lang_en') }
        ]);
        const displayLangName = computed(() => {
            const selected = displayLanguageOptions.value.find((item) => item.code === currentLang.value);
            return selected ? selected.label : t('lang_zh');
        });
        const roundedProgress = computed(() => Math.round(progressPercent.value));
        const runStateLabel = computed(() => {
            if (isRunning.value) return t('state_running');
            if (runFinished.value) return t('state_done');
            if (runStopped.value) return t('state_stopped');
            return t('state_idle');
        });
        const runButtonState = computed(() => {
            if (isRunning.value) return 'running';
            if (runFinished.value) return 'done';
            if (runStopped.value) return 'stopped';
            return 'idle';
        });
        const runButtonLabel = computed(() => {
            if (isRunning.value) return t('btn_running');
            if (runFinished.value || runStopped.value) return t('btn_restart');
            return t('btn_start');
        });
        const getLangName = (code) => {
            const map = currentLang.value === 'en' ? LANG_MAP.en : LANG_MAP.zh;
            return map[code] || code;
        };

        const formatStage = (stageCode) => {
            const zh = {
                environment_check: '环境预检',
                physics_filter: '声学粗筛',
                whisper_filter: '语义精筛',
                completed: '已完成',
                interrupted: '已中断'
            };
            const en = {
                environment_check: 'Diagnostics',
                physics_filter: 'Acoustic Filter',
                whisper_filter: 'Semantic Filter',
                completed: 'Completed',
                interrupted: 'Interrupted'
            };
            const map = currentLang.value === 'en' ? en : zh;
            return map[stageCode] || stageCode || t('state_idle');
        };

        const applyTheme = () => {
            document.body.classList.toggle('light-theme', !isDarkTheme.value);
            localStorage.setItem('vocalsieve.theme', isDarkTheme.value ? 'dark' : 'light');
        };

        const toggleTheme = (event) => {
            const update = () => {
                isDarkTheme.value = !isDarkTheme.value;
                applyTheme();
            };

            if (!document.startViewTransition || !event) {
                update();
                return;
            }

            const rect = event.currentTarget.getBoundingClientRect();
            const x = rect.left + rect.width / 2;
            const y = rect.top + rect.height / 2;
            const endRadius = Math.hypot(
                Math.max(x, window.innerWidth - x),
                Math.max(y, window.innerHeight - y)
            );

            const transition = document.startViewTransition(update);
            transition.ready.then(() => {
                document.documentElement.animate(
                    { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${endRadius}px at ${x}px ${y}px)`] },
                    { duration: 920, easing: 'cubic-bezier(.2,.8,.18,1)', pseudoElement: '::view-transition-new(root)' }
                );
            });
        };

        const addLog = (level, message) => {
            const time = new Date().toTimeString().split(' ')[0];
            logs.value.push({ time, level, message });
            if (logs.value.length > 600) logs.value.shift();
            if (isSettingsOpen.value && activeTab.value === 'log') {
                nextTick(() => {
                    if (consoleBody.value) consoleBody.value.scrollTop = consoleBody.value.scrollHeight;
                });
            }
        };

        const selectLang = (code) => {
            config.target_language = code;
            isLangDropdownOpen.value = false;
        };

        const selectDisplayLanguage = (code) => {
            currentLang.value = code;
            isDisplayLangDropdownOpen.value = false;
        };

        const selectDir = async (type) => {
            if (!window.pywebview?.api) {
                addLog('WARNING', t('bridge_missing'));
                return;
            }
            try {
                const path = await window.pywebview.api.select_directory();
                if (path) {
                    if (type === 'source') config.source_dir = path;
                    if (type === 'output') config.output_dir = path;
                }
            } catch (err) {
                addLog('ERROR', `${t('dir_failed')}: ${err}`);
            }
        };

        const resetRunState = () => {
            isRunning.value = true;
            runFinished.value = false;
            runStopped.value = false;
            currentStage.value = 'environment_check';
            currentCount.value = 0;
            totalCount.value = 0;
            currentItemName.value = '';
            logs.value = [];
        };

        const handleRunButton = () => {
            if (isRunning.value) {
                cancelPipeline();
                return;
            }
            startPipeline();
        };

        const startPipeline = async () => {
            if (!canStart.value) return;
            if (!window.pywebview?.api) {
                addLog('ERROR', t('bridge_missing'));
                return;
            }

            resetRunState();
            addLog('INFO', t('starting_engine'));

            try {
                const payload = JSON.parse(JSON.stringify(config));
                const res = await window.pywebview.api.start_pipeline(payload);
                if (res === 'started') {
                    addLog('INFO', t('pipeline_started'));
                    return;
                }
                addLog('ERROR', res);
                isRunning.value = false;
            } catch (err) {
                addLog('ERROR', `${t('pipeline_failed')}: ${err}`);
                isRunning.value = false;
            }
        };

        const cancelPipeline = async () => {
            try {
                await window.pywebview?.api?.cancel_pipeline();
                addLog('WARNING', t('canceling'));
            } catch (err) {
                addLog('ERROR', `${t('pipeline_failed')}: ${err}`);
            }
        };

        const copyLogs = async () => {
            if (logs.value.length === 0) return;
            const logText = logs.value.map((log) => `[${log.time}] [${log.level}] ${log.message}`).join('\n');
            try {
                if (window.pywebview?.api) {
                    const ok = await window.pywebview.api.copy_to_clipboard(logText);
                    if (!ok) throw new Error(t('copy_failed'));
                } else if (navigator.clipboard) {
                    await navigator.clipboard.writeText(logText);
                }
                addLog('INFO', t('copied'));
            } catch (err) {
                addLog('ERROR', `${t('copy_failed')}: ${err}`);
            }
        };

        const exportLogs = async () => {
            if (logs.value.length === 0 || !window.pywebview?.api) return;
            const logText = logs.value.map((log) => `[${log.time}] [${log.level}] ${log.message}`).join('\n');
            try {
                const path = await window.pywebview.api.export_logs(logText);
                if (path && !path.startsWith('ERROR')) addLog('INFO', `${t('exported')}: ${path}`);
                if (path?.startsWith('ERROR')) addLog('ERROR', path);
            } catch (err) {
                addLog('ERROR', `${t('export_failed')}: ${err}`);
            }
        };

        const loadEnvironment = async () => {
            if (!window.pywebview?.api) return;
            bridgeReady.value = true;
            try {
                const data = await window.pywebview.api.get_environment();
                Object.assign(env, data);
                if (data.recommended_preset) config.preset = data.recommended_preset;
                envLoaded.value = true;

                const languages = await window.pywebview.api.get_supported_languages();
                if (Array.isArray(languages) && languages.length > 0) {
                    supportedLanguages.value = languages;
                }

                const issues = [];
                if (!data.cuda_available) issues.push(t('no_gpu'));
                if (Array.isArray(data.issues)) issues.push(...data.issues);
                if (issues.length > 0) {
                    alertIssues.value = issues;
                    isAlertOpen.value = true;
                }
            } catch (err) {
                envLoaded.value = true;
                addLog('ERROR', `${t('env_scanning')}: ${err}`);
            }
        };

        const openSettings = (tab = 'sys') => {
            activeTab.value = tab;
            isSettingsOpen.value = true;
            if (tab === 'log') {
                nextTick(() => {
                    if (consoleBody.value) consoleBody.value.scrollTop = consoleBody.value.scrollHeight;
                });
            }
        };
        const closeSettings = () => { isSettingsOpen.value = false; };
        const closeAlert = () => { isAlertOpen.value = false; };

        const closeDropdowns = (event) => {
            if (!event.target.closest('.custom-select')) {
                isLangDropdownOpen.value = false;
                isDisplayLangDropdownOpen.value = false;
            }
        };

        const handleEscape = (event) => {
            if (event.key !== 'Escape') return;
            isLangDropdownOpen.value = false;
            isDisplayLangDropdownOpen.value = false;
            isSettingsOpen.value = false;
        };

        window.onStageStart = (stage, total) => {
            currentStage.value = stage;
            totalCount.value = total;
            currentCount.value = 0;
            currentItemName.value = '';
        };

        window.onItemDone = (stage, current, total, itemName, accepted, detail) => {
            currentStage.value = stage;
            currentCount.value = current;
            totalCount.value = total;
            currentItemName.value = `${accepted ? 'PASS' : 'DROP'} · ${itemName}${detail ? ` · ${detail}` : ''}`;
        };

        window.onStageEnd = (stage) => {
            currentStage.value = stage;
        };

        window.onLog = (level, message) => {
            addLog(level, message);
        };

        window.onPipelineComplete = (result) => {
            isRunning.value = false;
            runFinished.value = Boolean(result.success);
            runStopped.value = !result.success;
            currentStage.value = result.success ? 'completed' : 'interrupted';
            if (result.success) {
                currentCount.value = totalCount.value;
                addLog('INFO', `${t('pipeline_done')}: ${result.final_output_dir || '-'}`);
            } else if (result.cancelled) {
                addLog('WARNING', t('pipeline_cancelled'));
            } else {
                addLog('ERROR', `${t('pipeline_failed')}: ${result.error_message || '-'}`);
            }
        };

        watch(currentLang, (value) => {
            localStorage.setItem('vocalsieve.lang', value);
        });

        onMounted(() => {
            applyTheme();
            document.addEventListener('click', closeDropdowns);
            document.addEventListener('keydown', handleEscape);
            window.addEventListener('pywebviewready', loadEnvironment);

            if (window.pywebview?.api) {
                loadEnvironment();
            } else {
                window.setTimeout(() => {
                    if (!bridgeReady.value && !window.pywebview?.api) {
                        envLoaded.value = true;
                        Object.assign(env, {
                            python_ok: false,
                            torch_available: false,
                            cuda_available: false,
                            gpu_name: 'Preview',
                            whisper_available: false,
                            ffmpeg_found: false,
                            issues: [t('bridge_missing')]
                        });
                    }
                }, 900);
            }
        });

        return {
            t,
            currentLang,
            envLoaded,
            env,
            config,
            supportedLanguages,
            isRunning,
            runFinished,
            canStart,
            currentStage,
            currentCount,
            totalCount,
            currentItemName,
            progressPercent,
            roundedProgress,
            runStateLabel,
            runButtonState,
            runButtonLabel,
            logs,
            consoleBody,
            isDarkTheme,
            isSettingsOpen,
            activeTab,
            isAlertOpen,
            alertIssues,
            isAdvancedOpen,
            isLangDropdownOpen,
            isDisplayLangDropdownOpen,
            selectedLangName,
            displayLanguageOptions,
            displayLangName,
            getLangName,
            formatStage,
            toggleTheme,
            selectDir,
            selectLang,
            selectDisplayLanguage,
            handleRunButton,
            startPipeline,
            cancelPipeline,
            openSettings,
            closeSettings,
            closeAlert,
            copyLogs,
            exportLogs
        };
    }
}).mount('#app');
