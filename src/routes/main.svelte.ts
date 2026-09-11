// Логический модуль управления состоянием медиатеки v2.5
import { dev } from '$app/env';
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

	// Состояния для вкладки рекомендаций
	recommendQuery: 'Найди ноктюрн Шопена',
	recommendOutput: '',
	recommendInstructionName: '999-recommend-me-a-track.md',


	// Инициализируем массив тегов
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
	async processRecommendation() {
		if (!state.recommendQuery.trim()) {
			alert('Пожалуйста, введите поисковый запрос.');
			return;
		}

		state.isPending = true;
		state.statusMessage = 'Поиск рекомендаций в векторном хранилище...';
		state.statusColor = '#007bff';
		state.recommendOutput = '';

		try {
			// Шаг 1: Гарантированно считываем текст инструкции 999 из бакета
			const instRes = await fetch(`${PLAYLISTS_URL}?type=instruction&name=${encodeURIComponent(state.recommendInstructionName)}`, {
				headers: { 'Authorization': `Bearer ${state.iamToken}` }
			});
			if (!instRes.ok) throw new Error('Не удалось загрузить системный промпт рекомендаций.');
			const recommendationPrompt = await instRes.text();

			// Шаг 2: Отправляем запрос ассистенту
			const response = await fetch(ASSISTANT_URL, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.iamToken}` },
				body: JSON.stringify({
					query: state.recommendQuery.trim(),
					instruction: recommendationPrompt,
					playlistName: 'recommendation_request.yaml', // Фиктивное имя
					tagsConfig: [] // Для поиска теги не нужны
				})
			});

			if (!response.ok) throw new Error(`Ошибка сервера: ${response.status}`);

			const rawResult = await response.text();
			
			// Шаг 3: Парсим ответ вида "12;5"
			if (rawResult.includes(';')) {
				const parts = rawResult.split(';');
				const playlistNum = parts[0].trim();
				const trackNum = parts[1].trim();
				state.recommendOutput = `Рекомендация агента: плейлист № ${playlistNum}, трек № ${trackNum}.`;
				state.statusMessage = 'Рекомендация успешно получена.';
				state.statusColor = 'green';
			} else {
				// Если модель ответила развернутым текстом или ошибкой
				state.recommendOutput = rawResult;
				state.statusMessage = 'Ответ получен в свободном формате.';
				state.statusColor = '#333';
			}

		} catch (error: any) {
			state.statusMessage = `Ошибка поиска: ${error.message}`;
			state.statusColor = 'red';
			if(dev) console.error(error);
		} finally {
			state.isPending = false;
		}
	},
	checkSession() {
		const savedToken = localStorage.getItem('yc_iam_token');
		const savedTime = localStorage.getItem('yc_token_saved_at');
		if (savedToken && savedTime) {
			const age = Date.now() - parseInt(savedTime, 10);
			if (age < TOKEN_LIFETIME_MS) {
				state.iamToken = savedToken;
				state.isAuthorized = true;
				
				// 💡 НОВАЯ ЛОГИКА: Подтягиваем сохраненные значения тегов из localStorage
				this.loadSavedTags();
				
				this.initCloudData();
			} else {
				this.clearToken();
			}
		}
	},

	// 💡 НОВАЯ ЛОГИКА: Загрузка тегов из памяти браузера
	loadSavedTags() {
		state.expertTags.forEach(tag => {
			const savedValue = localStorage.getItem(`tag_val_${tag.id}`);
			if (savedValue !== null) {
				tag.value = savedValue;
			}
		});
	},

	// 💡 НОВАЯ ЛОГИКА: Сохранение конкретного тега при вводе
	saveTagValue(id: string, value: string) {
		localStorage.setItem(`tag_val_${id}`, value);
	},

	// 💡 НОВАЯ ЛОГИКА: Кнопка полной очистки полей и localStorage
	clearExpertTags() {
		if (confirm('Вы уверены, что хотите полностью очистить все глобальные теги?')) {
			state.expertTags.forEach(tag => {
				tag.value = '';
				localStorage.removeItem(`tag_val_${tag.id}`);
			});
			state.statusMessage = 'Все глобальные теги успешно очищены.';
			state.statusColor = '#555';
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
						state.selectedInstruction = state.instructions[0];
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
			alert('Запрос и текст инструкции не должны быть пустыми.');
			return;
		}

		const findTagValue = (id: string) => state.expertTags.find(t => t.id === id)?.value?.trim() || '';
		const contextComposer = findTagValue('composer');
		const contextArtist = findTagValue('artist');
		const contextAlbum = findTagValue('album');

		let finalQuery = '';
		if (contextComposer || contextArtist || contextAlbum) {
			finalQuery += `Контекст альбома для разметки:\n`;
			if (contextComposer) finalQuery += `- Композитор: ${contextComposer}\n`;
			if (contextArtist)   finalQuery += `- Исполнитель: ${contextArtist}\n`;
			if (contextAlbum)    finalQuery += `- Произведение: ${contextAlbum}\n`;
			finalQuery += `\n`;
		}

		finalQuery += state.query.trim();

		if (state.yamlData.trim()) {
			finalQuery += `\n\n\`\`\`yaml\n${state.yamlData.trim()}\n\`\`\``;
		}

		state.isPending = true;
		state.statusMessage = 'Лингвистический агент анализирует контекст альбома и обрабатывает названия треков...';
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
				const downloadName = matches?.[1] ?? 'apply_tags.sh';

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
			state.statusColor = 'red';
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