const { createApp, ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } = Vue;

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
        state_starting: '正在启动',
        state_running: '正在筛选',
        state_canceling: '正在中止',
        state_done: '任务完成',
        state_failed: '任务失败',
        state_stopped: '任务中断',
        btn_start: '开始运行',
        btn_starting: '启动中',
        btn_running: '运行中',
        btn_restart: '重新运行',
        btn_canceling: '中止中',
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
        bridge_missing: '未检测到 PyWebview 桥接，当前预览环境不能启动后端任务。',
        copied: '日志已复制到剪贴板',
        exported: '日志已导出至',
        copy_failed: '复制失败',
        export_failed: '导出失败',
        dir_failed: '目录选择失败',
        canceling: '已发送取消信号，等待当前文件处理结束',
        starting_engine: '正在请求底层处理引擎...',
        pipeline_started: '后端任务已启动',
        pipeline_done: '筛选完成',
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
        preset_qual: 'Quality First',
        preset_qual_desc: 'Best for final export when longer runtime is acceptable.',
        target_lang: 'Audio Language',
        top_n: 'Retention Count',
        adv_settings: 'Advanced Settings',
        adv_rms: 'Min Volume (RMS)',
        adv_centroid: 'Min Spectral Centroid (Hz)',
        adv_duration: 'Min Duration (s)',
        state_idle: 'Ready',
        state_starting: 'Starting',
        state_running: 'Filtering',
        state_canceling: 'Stopping',
        state_done: 'Completed',
        state_failed: 'Failed',
        state_stopped: 'Interrupted',
        btn_start: 'Start Run',
        btn_starting: 'Starting',
        btn_running: 'Running',
        btn_restart: 'Run Again',
        btn_canceling: 'Stopping',
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
        pipeline_done: 'Filtering completed',
        pipeline_cancelled: 'Task cancelled',
        pipeline_failed: 'Task failed',
        no_gpu: 'No compatible NVIDIA GPU was detected. Whisper may run on CPU.'
    }
};

const LANGUAGE_LABELS = {
    zh: {
        auto: '自动检测',
        ja: '日语',
        zh: '中文',
        en: '英语',
        ko: '韩语',
        de: '德语',
        fr: '法语',
        es: '西班牙语',
        ru: '俄语',
        it: '意大利语',
        pt: '葡萄牙语'
    },
    en: {
        auto: 'Auto',
        ja: 'Japanese',
        zh: 'Chinese',
        en: 'English',
        ko: 'Korean',
        de: 'German',
        fr: 'French',
        es: 'Spanish',
        ru: 'Russian',
        it: 'Italian',
        pt: 'Portuguese'
    }
};

const DEFAULT_LANGUAGES = [
    { code: 'auto', name: 'Auto' },
    { code: 'ja', name: 'Japanese' },
    { code: 'zh', name: 'Chinese' },
    { code: 'en', name: 'English' },
    { code: 'ko', name: 'Korean' },
    { code: 'de', name: 'German' },
    { code: 'fr', name: 'French' },
    { code: 'es', name: 'Spanish' },
    { code: 'ru', name: 'Russian' },
    { code: 'it', name: 'Italian' },
    { code: 'pt', name: 'Portuguese' }
];

const RUN_STATUS = {
    IDLE: 'idle',
    STARTING: 'starting',
    RUNNING: 'running',
    CANCELING: 'canceling',
    SUCCESS: 'success',
    FAILED: 'failed',
    CANCELLED: 'cancelled'
};

createApp({
    setup() {
        const currentLang = ref(localStorage.getItem('vocalsieve.lang') || 'zh');
        const isDarkTheme = ref(localStorage.getItem('vocalsieve.theme') !== 'light');
        const bridgeReady = ref(false);
        const bridgeChecked = ref(false);

        const t = (key) => I18N[currentLang.value]?.[key] || I18N.zh[key] || key;

        const envLoaded = ref(false);
        const env = reactive({});
        const supportedLanguages = ref(DEFAULT_LANGUAGES);

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

        const ui = reactive({
            dropdown: null,
            advancedOpen: false,
            settingsOpen: false,
            alertOpen: false,
            activeTab: 'sys'
        });

        const run = reactive({
            status: RUN_STATUS.IDLE,
            stage: '',
            current: 0,
            total: 0,
            itemName: '',
            result: null
        });

        const logs = ref([]);
        const consoleBody = ref(null);
        const alertIssues = ref([]);

        const hasBridge = () => Boolean(window.pywebview && window.pywebview.api);

        const markBridgeReady = () => {
            bridgeReady.value = hasBridge();
            bridgeChecked.value = true;
            return bridgeReady.value;
        };

        const waitForBridge = (timeout = 2500) => new Promise((resolve) => {
            if (markBridgeReady()) {
                resolve(true);
                return;
            }

            let settled = false;
            const finish = (ok) => {
                if (settled) return;
                settled = true;
                window.removeEventListener('pywebviewready', onReady);
                clearTimeout(timer);
                bridgeReady.value = ok;
                bridgeChecked.value = true;
                resolve(ok);
            };
            const onReady = () => finish(markBridgeReady());
            const timer = window.setTimeout(() => finish(markBridgeReady()), timeout);
            window.addEventListener('pywebviewready', onReady, { once: true });
        });

        const callApi = async (method, ...args) => {
            const ready = hasBridge() || await waitForBridge();
            if (!ready || !window.pywebview.api || typeof window.pywebview.api[method] !== 'function') {
                throw new Error(t('bridge_missing'));
            }
            return window.pywebview.api[method](...args);
        };

        const canStart = computed(() => Boolean(config.source_dir && config.output_dir));
        const isRunning = computed(() => [
            RUN_STATUS.STARTING,
            RUN_STATUS.RUNNING,
            RUN_STATUS.CANCELING
        ].includes(run.status));
        const runFinished = computed(() => run.status === RUN_STATUS.SUCCESS);
        const runStopped = computed(() => [RUN_STATUS.FAILED, RUN_STATUS.CANCELLED].includes(run.status));
        const progressPercent = computed(() => {
            if (run.status === RUN_STATUS.SUCCESS) return 100;
            if (run.status === RUN_STATUS.STARTING) return 1;
            if (run.total <= 0) return 0;
            return Math.min(99, Math.max(0, (run.current / run.total) * 100));
        });
        const roundedProgress = computed(() => Math.round(progressPercent.value));
        const currentStage = computed(() => run.stage);
        const currentCount = computed(() => run.current);
        const totalCount = computed(() => run.total);
        const currentItemName = computed(() => run.itemName);
        const isAdvancedOpen = computed({
            get: () => ui.advancedOpen,
            set: (value) => { ui.advancedOpen = Boolean(value); }
        });
        const isSettingsOpen = computed({
            get: () => ui.settingsOpen,
            set: (value) => { ui.settingsOpen = Boolean(value); }
        });
        const isAlertOpen = computed({
            get: () => ui.alertOpen,
            set: (value) => { ui.alertOpen = Boolean(value); }
        });
        const activeTab = computed({
            get: () => ui.activeTab,
            set: (value) => { ui.activeTab = value; }
        });
        const isLangDropdownOpen = computed({
            get: () => ui.dropdown === 'audio',
            set: (value) => { ui.dropdown = value ? 'audio' : null; }
        });
        const isDisplayLangDropdownOpen = computed({
            get: () => ui.dropdown === 'display',
            set: (value) => { ui.dropdown = value ? 'display' : null; }
        });

        const displayLanguageOptions = computed(() => [
            { code: 'zh', label: t('lang_zh') },
            { code: 'en', label: t('lang_en') }
        ]);
        const displayLangName = computed(() => (
            displayLanguageOptions.value.find((item) => item.code === currentLang.value)?.label || t('lang_zh')
        ));
        const selectedLangName = computed(() => getLangName(config.target_language));
        const runStateLabel = computed(() => {
            const stateMap = {
                [RUN_STATUS.IDLE]: 'state_idle',
                [RUN_STATUS.STARTING]: 'state_starting',
                [RUN_STATUS.RUNNING]: 'state_running',
                [RUN_STATUS.CANCELING]: 'state_canceling',
                [RUN_STATUS.SUCCESS]: 'state_done',
                [RUN_STATUS.FAILED]: 'state_failed',
                [RUN_STATUS.CANCELLED]: 'state_stopped'
            };
            return t(stateMap[run.status] || 'state_idle');
        });
        const runButtonState = computed(() => {
            if (run.status === RUN_STATUS.SUCCESS) return 'done';
            if (run.status === RUN_STATUS.FAILED || run.status === RUN_STATUS.CANCELLED) return 'stopped';
            if (run.status === RUN_STATUS.STARTING || run.status === RUN_STATUS.RUNNING || run.status === RUN_STATUS.CANCELING) return 'running';
            return 'idle';
        });
        const runButtonLabel = computed(() => {
            if (run.status === RUN_STATUS.STARTING) return t('btn_starting');
            if (run.status === RUN_STATUS.CANCELING) return t('btn_canceling');
            if (run.status === RUN_STATUS.RUNNING) return t('btn_running');
            if (run.status === RUN_STATUS.SUCCESS || run.status === RUN_STATUS.FAILED || run.status === RUN_STATUS.CANCELLED) return t('btn_restart');
            return t('btn_start');
        });

        function getLangName(code) {
            return LANGUAGE_LABELS[currentLang.value]?.[code] || LANGUAGE_LABELS.zh[code] || code;
        }

        function formatStage(stageCode) {
            const labels = {
                zh: {
                    environment_check: '环境预检',
                    physics_filter: '声学粗筛',
                    whisper_filter: '语义精筛',
                    completed: '已完成',
                    interrupted: '已中断'
                },
                en: {
                    environment_check: 'Diagnostics',
                    physics_filter: 'Acoustic Filter',
                    whisper_filter: 'Semantic Filter',
                    completed: 'Completed',
                    interrupted: 'Interrupted'
                }
            };
            return labels[currentLang.value]?.[stageCode] || stageCode || t('state_idle');
        }

        function applyTheme() {
            document.body.classList.toggle('light-theme', !isDarkTheme.value);
            localStorage.setItem('vocalsieve.theme', isDarkTheme.value ? 'dark' : 'light');
        }

        function toggleTheme(event) {
            const update = () => {
                isDarkTheme.value = !isDarkTheme.value;
                applyTheme();
            };

            if (!document.startViewTransition || !event?.currentTarget) {
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
                    { duration: 1100, easing: 'cubic-bezier(.2,.8,.18,1)', pseudoElement: '::view-transition-new(root)' }
                );
            }).catch(() => {});
        }

        function addLog(level, message) {
            const time = new Date().toTimeString().split(' ')[0];
            logs.value.push({ time, level, message: String(message ?? '') });
            if (logs.value.length > 700) logs.value.shift();
            if (ui.settingsOpen && ui.activeTab === 'log') {
                nextTick(scrollLogsToBottom);
            }
        }

        function scrollLogsToBottom() {
            if (consoleBody.value) {
                consoleBody.value.scrollTop = consoleBody.value.scrollHeight;
            }
        }

        function toggleDropdown(name, event) {
            if (event) event.stopPropagation();
            if (isRunning.value && name === 'audio') return;
            ui.dropdown = ui.dropdown === name ? null : name;
        }

        function closeDropdowns(event) {
            if (!event || !event.target.closest('.custom-select')) {
                ui.dropdown = null;
            }
        }

        function selectLang(code) {
            config.target_language = code;
            ui.dropdown = null;
        }

        function selectDisplayLanguage(code) {
            currentLang.value = code;
            document.documentElement.lang = code === 'zh' ? 'zh-CN' : 'en';
            ui.dropdown = null;
        }

        async function selectDir(type) {
            if (isRunning.value) return;
            try {
                const path = await callApi('select_directory');
                if (!path) return;
                if (type === 'source') config.source_dir = path;
                if (type === 'output') config.output_dir = path;
            } catch (err) {
                addLog('ERROR', `${t('dir_failed')}: ${err.message || err}`);
            }
        }

        function prepareRun() {
            run.status = RUN_STATUS.STARTING;
            run.stage = 'environment_check';
            run.current = 0;
            run.total = 0;
            run.itemName = '';
            run.result = null;
            logs.value = [];
            ui.dropdown = null;
        }

        function finishRun(result) {
            run.result = result || {};
            if (result?.success) {
                run.status = RUN_STATUS.SUCCESS;
                run.stage = 'completed';
                run.current = run.total || run.current;
                addLog('INFO', `${t('pipeline_done')}: ${result.final_output_dir || '-'}`);
                return;
            }
            if (result?.cancelled) {
                run.status = RUN_STATUS.CANCELLED;
                run.stage = 'interrupted';
                addLog('WARNING', t('pipeline_cancelled'));
                return;
            }
            run.status = RUN_STATUS.FAILED;
            run.stage = 'interrupted';
            addLog('ERROR', `${t('pipeline_failed')}: ${result?.error_message || '-'}`);
        }

        function handleRunButton() {
            if (run.status === RUN_STATUS.STARTING || run.status === RUN_STATUS.RUNNING) {
                cancelPipeline();
                return;
            }
            if (run.status === RUN_STATUS.CANCELING) return;
            startPipeline();
        }

        async function startPipeline() {
            if (!canStart.value || isRunning.value) return;
            prepareRun();
            addLog('INFO', t('starting_engine'));

            try {
                const payload = JSON.parse(JSON.stringify(config));
                const response = await callApi('start_pipeline', payload);
                if (response === 'started') {
                    run.status = RUN_STATUS.RUNNING;
                    addLog('INFO', t('pipeline_started'));
                    return;
                }
                run.status = RUN_STATUS.FAILED;
                addLog('ERROR', response || t('pipeline_failed'));
            } catch (err) {
                run.status = RUN_STATUS.FAILED;
                addLog('ERROR', `${t('pipeline_failed')}: ${err.message || err}`);
            }
        }

        async function cancelPipeline() {
            if (!isRunning.value || run.status === RUN_STATUS.CANCELING) return;
            run.status = RUN_STATUS.CANCELING;
            try {
                await callApi('cancel_pipeline');
                addLog('WARNING', t('canceling'));
            } catch (err) {
                run.status = RUN_STATUS.FAILED;
                addLog('ERROR', `${t('pipeline_failed')}: ${err.message || err}`);
            }
        }

        async function copyLogs() {
            if (logs.value.length === 0) return;
            const logText = logs.value.map((log) => `[${log.time}] [${log.level}] ${log.message}`).join('\n');
            try {
                if (hasBridge()) {
                    const ok = await callApi('copy_to_clipboard', logText);
                    if (!ok) throw new Error(t('copy_failed'));
                } else if (navigator.clipboard) {
                    await navigator.clipboard.writeText(logText);
                }
                addLog('INFO', t('copied'));
            } catch (err) {
                addLog('ERROR', `${t('copy_failed')}: ${err.message || err}`);
            }
        }

        async function exportLogs() {
            if (logs.value.length === 0) return;
            const logText = logs.value.map((log) => `[${log.time}] [${log.level}] ${log.message}`).join('\n');
            try {
                const path = await callApi('export_logs', logText);
                if (path && !String(path).startsWith('ERROR')) addLog('INFO', `${t('exported')}: ${path}`);
                if (path && String(path).startsWith('ERROR')) addLog('ERROR', path);
            } catch (err) {
                addLog('ERROR', `${t('export_failed')}: ${err.message || err}`);
            }
        }

        async function loadEnvironment() {
            const ready = await waitForBridge(1800);
            if (!ready) {
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
                return;
            }

            try {
                const data = await callApi('get_environment');
                Object.assign(env, data || {});
                if (data?.recommended_preset) config.preset = data.recommended_preset;
                envLoaded.value = true;

                const languages = await callApi('get_supported_languages');
                if (Array.isArray(languages) && languages.length > 0) {
                    supportedLanguages.value = languages;
                }

                const issues = [];
                if (!data?.cuda_available) issues.push(t('no_gpu'));
                if (Array.isArray(data?.issues)) issues.push(...data.issues);
                if (issues.length > 0) {
                    alertIssues.value = issues;
                    ui.alertOpen = true;
                }
            } catch (err) {
                envLoaded.value = true;
                addLog('ERROR', `${t('env_scanning')}: ${err.message || err}`);
            }
        }

        function openSettings(tab = 'sys') {
            ui.activeTab = tab;
            ui.settingsOpen = true;
            ui.dropdown = null;
            if (tab === 'log') nextTick(scrollLogsToBottom);
        }

        function closeSettings() {
            ui.settingsOpen = false;
            ui.dropdown = null;
        }

        function closeAlert() {
            ui.alertOpen = false;
        }

        function handleEscape(event) {
            if (event.key !== 'Escape') return;
            if (ui.dropdown) {
                ui.dropdown = null;
                return;
            }
            if (ui.alertOpen) {
                ui.alertOpen = false;
                return;
            }
            if (ui.settingsOpen) {
                ui.settingsOpen = false;
            }
        }

        window.onStageStart = (stage, total) => {
            run.status = RUN_STATUS.RUNNING;
            run.stage = stage || run.stage;
            run.total = Number(total) || 0;
            run.current = 0;
            run.itemName = '';
        };

        window.onItemDone = (stage, current, total, itemName, accepted, detail) => {
            run.status = RUN_STATUS.RUNNING;
            run.stage = stage || run.stage;
            run.current = Number(current) || 0;
            run.total = Number(total) || run.total;
            const prefix = accepted ? 'PASS' : 'DROP';
            run.itemName = `${prefix} · ${itemName || ''}${detail ? ` · ${detail}` : ''}`;
        };

        window.onStageEnd = (stage) => {
            run.stage = stage || run.stage;
        };

        window.onLog = (level, message) => {
            addLog(level || 'INFO', message || '');
        };

        window.onPipelineComplete = (result) => {
            finishRun(result || {});
        };

        watch(currentLang, (value) => {
            localStorage.setItem('vocalsieve.lang', value);
            document.documentElement.lang = value === 'zh' ? 'zh-CN' : 'en';
        }, { immediate: true });

        onMounted(() => {
            applyTheme();
            document.addEventListener('click', closeDropdowns);
            document.addEventListener('keydown', handleEscape);
            window.addEventListener('pywebviewready', loadEnvironment, { once: true });
            loadEnvironment();
        });

        onBeforeUnmount(() => {
            document.removeEventListener('click', closeDropdowns);
            document.removeEventListener('keydown', handleEscape);
        });

        return {
            t,
            currentLang,
            bridgeReady,
            bridgeChecked,
            envLoaded,
            env,
            config,
            supportedLanguages,
            isRunning,
            runFinished,
            runStopped,
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
            toggleDropdown,
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
