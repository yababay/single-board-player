// Логический модуль управления состоянием медиатеки v2.4
import tags from '$lib/assets/mp3-tags.json';

interface TagItem {
	id: string;
	label: string;
	type: string;
	flag: string;
	placeholder: string;
	value: string;
}

export const state = $state({
	query: 'Обработай названия треков из этого плейлиста.',
	yamlData: '',
	statusMessage: '',
	statusColor: '#555',
	outputText: '',
	isPending: false,
	activeTab: 'tagger',

	// 💡 ИСПРАВЛЕНИЕ: Никаких вызовов $state внутри .map(). 
	// Сам массив находится внутри прокси-оболочки state, что делает его структуру реактивной.
	expertTags: tags.map(t => ({
		id: t.id,
		label: t.label,
		type: t.type,
		flag: t.flag,
		placeholder: t.placeholder,
		value: t.value
	})) as TagItem[],

	playlists: [] as string[],
	instructions: [] as string[],
	selectedPlaylist: '',
	selectedInstruction: '',
	currentInstructionText: '',
	iamToken: '',
	isAuthorized: false
});

const ASSISTANT_URL = '/api/assistant';
const PLAYLISTS_URL = '/api/playlists';
const TOKEN_LIFETIME_MS = 4 * 60 * 60 * 1000;

export const actions = {
	checkSession() {
		const savedToken = localStorage.getItem('yc_iam_token');
		const savedTime = localStorage.getItem('yc_token_saved_at');
		if (savedToken && savedTime) {
			const age = Date.now() - parseInt(savedTime, 10);
			if (age < TOKEN_LIFETIME_MS) {
				state.iamToken = savedToken;
				state.isAuthorized = true;
				this.initCloudData();
			} else {
				this.clearToken();
			}
		}
	},

	async initCloudData() {
		await this.loadCloudFiles('playlist');
		await this.loadCloudFiles('instruction');
	},

	async loadCloudFiles(type: 'playlist' | 'instruction') {
		try {
			const res = await fetch(`${PLAYLISTS_URL}?type=${type}`, {
				headers: { 'Authorization': `Bearer ${state.iamToken}` }
			});
			if (res.ok) {
				const data = await res.json();
				if (type === 'playlist') {
					state.playlists = data;
				} else {
					state.instructions = data.sort((a: string, b: string) => a.localeCompare(b));
					if (state.instructions.length > 0 && !state.selectedInstruction) {
						state.selectedInstruction = state.instructions[0]; // Исправили на индекс 0
						this.loadInstructionText(state.selectedInstruction);
					}
				}
			}
		} catch (e) { console.error(e); }
	},

	async loadInstructionText(name: string) {
		if (!name) return;
		try {
			const res = await fetch(`${PLAYLISTS_URL}?type=instruction&name=${encodeURIComponent(name)}`, {
				headers: { 'Authorization': `Bearer ${state.iamToken}` }
			});
			if (res.ok) {
				state.currentInstructionText = await res.text();
			}
		} catch (e) { console.error(e); }
	},

	async handlePlaylistChange(name: string) {
		if (state.playlists.includes(name)) {
			state.statusMessage = `Загрузка плейлиста ${name}...`;
			state.statusColor = '#007bff';
			const res = await fetch(`${PLAYLISTS_URL}?type=playlist&name=${encodeURIComponent(name)}`, {
				headers: { 'Authorization': `Bearer ${state.iamToken}` }
			});
			if (res.ok) {
				state.yamlData = await res.text();
				state.statusMessage = `Плейлист ${name} успешно загружен.`;
				state.statusColor = 'green';
			}
		}
	},

	async processRequest() {
		if (!state.query.trim() || !state.currentInstructionText.trim()) {
			alert('Запрос и text инструкции не должны быть пустыми.');
			return;
		}

		let finalQuery = state.query.trim();
		if (state.yamlData.trim()) finalQuery += `\n\n\`\`\`yaml\n${state.yamlData.trim()}\n\`\`\``;

		state.isPending = true;
		state.statusMessage = 'Лингвистический агент обрабатывает названия треков...';
		state.statusColor = '#007bff';
		state.outputText = '';

		try {
			const response = await fetch(ASSISTANT_URL, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.iamToken}` },
				body: JSON.stringify({
					query: finalQuery,
					instruction: state.currentInstructionText,
					playlistName: state.selectedPlaylist,
					tagsConfig: state.expertTags 
				})
			});

			if (!response.ok) throw new Error(`Ошибка сервера: ${response.status}`);

			const contentType = response.headers.get('Content-Type') || '';
			if (contentType.includes('text/x-shellscript')) {
				const contentDisposition = response.headers.get('Content-Disposition') || '';
				const matches = contentDisposition.match(/filename="(.+?)"/);
				const downloadName = matches ? matches[1] : 'apply_tags.sh';

				const blob = await response.blob();
				const url = window.URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = downloadName;
				document.body.appendChild(a);
				a.click();
				a.remove();
				window.URL.revokeObjectURL(url);
				state.statusMessage = `Успешно! Скрипт ${downloadName} скачан.`;
				state.statusColor = 'green';
			} else {
				state.outputText = await response.text();
				state.statusMessage = 'Ответ от ИИ-агента:';
				state.statusColor = '#333';
			}
		} catch (error: any) {
			state.statusMessage = `Ошибка: ${error.message}`;
			state.statusColor = 'red'; // Поправили опечатку строки 148
		} finally { state.isPending = false; }
	},

	login() {
		if (!state.iamToken.trim()) return;
		localStorage.setItem('yc_iam_token', state.iamToken.trim());
		localStorage.setItem('yc_token_saved_at', Date.now().toString());
		state.isAuthorized = true;
		this.initCloudData();
	},

	clearToken() {
		localStorage.clear();
		state.iamToken = '';
		state.isAuthorized = false;
		state.playlists = [];
		state.instructions = [];
		state.selectedPlaylist = '';
		state.selectedInstruction = '';
		state.currentInstructionText = '';
	}
};
