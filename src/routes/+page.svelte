<script lang="ts">
	import { onMount } from 'svelte';

	let query = $state('Сформируй .sh скрипт разметки для этого плейлиста');
	let yamlData = $state('');
	let statusMessage = $state('');
	let statusColor = $state('#555');
	let outputText = $state('');
	let isPending = $state(false);

	let iamToken = $state('');
	let isAuthorized = $state(false);

	let playlists: string[] = $state([]);
	let selectedPlaylistName = $state('');

	const ASSISTANT_URL = '/api/assistant';
	const PLAYLISTS_URL = '/api/playlists';
	const TOKEN_LIFETIME_MS = 4 * 60 * 60 * 1000;

	onMount(() => {
		const savedToken = localStorage.getItem('yc_iam_token');
		const savedTime = localStorage.getItem('yc_token_saved_at');

		if (savedToken && savedTime) {
			const age = Date.now() - parseInt(savedTime, 10);
			if (age < TOKEN_LIFETIME_MS) {
				iamToken = savedToken;
				isAuthorized = true;
				loadPlaylists(); 
			} else {
				clearToken();
			}
		}
	});

	async function loginWithToken() {
		if (!iamToken.trim()) {
			alert('Пожалуйста, введите IAM-токен.');
			return;
		}

		isPending = true;
		statusMessage = 'Проверка токена и загрузка плейлистов...';
		statusColor = '#007bff';

		try {
			const response = await fetch(PLAYLISTS_URL, {
				method: 'GET',
				headers: { 'Authorization': `Bearer ${iamToken.trim()}` }
			});

			if (response.status === 401 || response.status === 403) {
				throw new Error('Введенный IAM-токен невалиден или его срок действия истек.');
			}

			if (!response.ok) {
				const errData = await response.json().catch(() => ({}));
				throw new Error(errData.error || `Ошибка сервера ${response.status}`);
			}

			playlists = await response.json();
			
			localStorage.setItem('yc_iam_token', iamToken.trim());
			localStorage.setItem('yc_token_saved_at', Date.now().toString());
			isAuthorized = true;
			
			statusMessage = `Авторизация успешна. Доступно плейлистов: ${playlists.length}`;
			statusColor = 'green';
		} catch (error: any) {
			statusMessage = `Ошибка авторизации: ${error.message}`;
			statusColor = 'red';
			clearToken();
		} finally {
			isPending = false;
		}
	}

	async function loadPlaylists() {
		try {
			const response = await fetch(PLAYLISTS_URL, {
				method: 'GET',
				headers: { 'Authorization': `Bearer ${iamToken.trim()}` }
			});
			if (response.ok) {
				playlists = await response.json();
			} else if (response.status === 401) {
				clearToken();
			}
		} catch (e) {
			console.error('Ошибка загрузки плейлистов:', e);
		}
	}

	// Реальное скачивание содержимого выбранного YAML-файла
	async function handlePlaylistChange(e: Event) {
		const target = e.target as HTMLInputElement;
		const name = target.value.trim();
		
		if (playlists.includes(name)) {
			statusMessage = `Загрузка содержимого файла ${name}...`;
			statusColor = '#007bff';
			yamlData = ''; // Очищаем старые данные перед загрузкой
			
			try {
				// Делаем GET запрос с query-параметром ?name=...
				const response = await fetch(`${PLAYLISTS_URL}?name=${encodeURIComponent(name)}`, {
					method: 'GET',
					headers: { 'Authorization': `Bearer ${iamToken.trim()}` }
				});

				if (!response.ok) {
					const errData = await response.json().catch(() => ({}));
					throw new Error(errData.error || `Ошибка загрузки файла: ${response.status}`);
				}

				yamlData = await response.text();
				statusMessage = `Плейлист ${name} успешно загружен и готов к редактированию.`;
				statusColor = 'green';
			} catch (err: any) {
				statusMessage = `Не удалось загрузить файл: ${err.message}`;
				statusColor = 'red';
			}
		}
	}

	function clearToken() {
		localStorage.removeItem('yc_iam_token');
		localStorage.removeItem('yc_token_saved_at');
		iamToken = '';
		isAuthorized = false;
		playlists = [];
		selectedPlaylistName = '';
	}

	async function processRequest() {
		if (!query.trim()) {
			alert('Пожалуйста, введите запрос для ИИ-агента.');
			return;
		}

		let finalQuery = query.trim();
		if (yamlData.trim()) {
			finalQuery += `\n\n\`\`\`yaml\n${yamlData.trim()}\n\`\`\``;
		}

		isPending = true;
		statusMessage = 'Агент анализирует данные и формирует ответ...';
		statusColor = '#007bff';
		outputText = '';

		try {
			const response = await fetch(ASSISTANT_URL, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Authorization': `Bearer ${iamToken.trim()}`
				},
				body: JSON.stringify({ query: finalQuery })
			});

			if (response.status === 401 || response.status === 403) {
				clearToken();
				throw new Error('Срок действия токена истек. Войдите заново.');
			}

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.error || `Ошибка сервера: ${response.status}`);
			}

			const contentType = response.headers.get('Content-Type') || '';

			if (contentType.includes('text/x-shellscript')) {
				const blob = await response.blob();
				const url = window.URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = 'apply_tags.sh';
				document.body.appendChild(a);
				a.click();
				a.remove();
				window.URL.revokeObjectURL(url);

				statusMessage = 'Успешно! Скрипт apply_tags.sh скачан.';
				statusColor = 'green';
			} else {
				outputText = await response.text();
				statusMessage = 'Ответ от ИИ-агента:';
				statusColor = '#333';
			}
		} catch (error: any) {
			statusMessage = `Произошла ошибка: ${error.message}`;
			statusColor = 'red';
		} finally {
			isPending = false;
		}
	}
</script>

<div class="container">
	<h2>Генератор тегов медиатеки</h2>

	{#if !isAuthorized}
		<div class="auth-box">
			<label for="token-input">🔑 Требуется авторизация (введите IAM-токен Yandex Cloud):</label>
			<div class="token-row">
				<input
					type="password"
					id="token-input"
					placeholder="t1.9euelZq..."
					bind:value={iamToken}
				/>
				<button class="btn-auth" onclick={loginWithToken} disabled={isPending || !iamToken.trim()}>
					Войти
				</button>
			</div>
		</div>
	{:else}
		<!-- Ссылка «Выйти» с иконкой из bootstrap-icons в правом верхнем углу -->
		<button class="logout-link" onclick={clearToken} title="Выйти из сессии">
			<i class="bi bi-box-arrow-right"></i> Выйти
		</button>

		<div class="session-info">
			<span>Сессия активна ({playlists.length} плейлистов найдено в облаке)</span>
		</div>

		<div class="form-group">
			<label for="playlist-search">🔍 Выберите или найдите YAML-плейлист:</label>
			<input
				type="text"
				id="playlist-search"
				list="playlist-options"
				placeholder="Начните вводить имя..."
				bind:value={selectedPlaylistName}
				oninput={handlePlaylistChange}
			/>
			<datalist id="playlist-options">
				{#each playlists as item}
					<option value={item}></option>
				{/each}
			</datalist>
		</div>

		<div class="form-group">
			<label for="query-input">Ваш запрос к ИИ-агенту:</label>
			<input type="text" id="query-input" bind:value={query} />
		</div>

		<div class="form-group">
			<label for="yaml-input">Содержимое YAML-плейлиста (можно сократить):</label>
			<textarea id="yaml-input" class="code-input" rows="12" bind:value={yamlData}></textarea>
		</div>

		<button onclick={processRequest} disabled={isPending}> Отправить запрос </button>
	{/if}

	{#if statusMessage}
		<div id="status" style="color: {statusColor}">{statusMessage}</div>
	{/if}

	{#if outputText}
		<pre id="output">{outputText}</pre>
	{/if}
</div>

<style>
	.container { 
		position: relative; /* Чтобы спозиционировать ссылку Выйти относительно контейнера */
		background: #fff; 
		padding: 25px; 
		border-radius: 8px; 
		box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
		width: 100%; 
		max-width: 800px; 
	}
	
	/* Кнопка-ссылка выхода в правом верхнем углу */
	.logout-link {
		position: absolute;
		top: 25px;
		right: 25px;
		background: none;
		border: none;
		color: #dc3545;
		cursor: pointer;
		font-size: 14px;
		font-weight: normal;
		width: auto;
		padding: 0;
		display: inline-flex;
		align-items: center;
		gap: 5px;
	}
	.logout-link:hover {
		color: #bd2130;
		background: none;
		text-decoration: underline;
	}

	.auth-box { background: #fff3cd; border: 1px solid #ffeeba; padding: 20px; border-radius: 6px; margin-bottom: 15px; text-align: left; }
	.token-row { display: flex; gap: 10px; margin-top: 8px; }
	.token-row input { flex: 1; }
	.btn-auth { width: auto; padding: 0 25px; }
	
	.session-info { 
		display: flex; 
		justify-content: space-between; 
		align-items: center; 
		background: #d4edda; 
		color: #155724; 
		padding: 8px 15px; 
		border-radius: 4px; 
		margin-bottom: 20px; 
		font-size: 14px; 
		text-align: left;
	}
	
	.form-group { margin-bottom: 20px; }
	label { display: block; font-weight: bold; margin-bottom: 8px; color: #333; text-align: left; }
	input[type='text'], input[type='password'], textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-family: inherit; }
	textarea { resize: vertical; }
	.code-input { font-family: 'Courier New', Courier, monospace; font-size: 14px; background-color: #fafafa; }
	
	button { background-color: #007bff; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; width: 100%; }
	button:hover { background-color: #0056b3; }
	button:disabled { background-color: #cccccc; cursor: not-allowed; }
	
	#status { margin-top: 15px; font-weight: bold; text-align: left; }
	#output { margin-top: 20px; padding: 15px; background: #e9ecef; border-left: 4px solid #007bff; border-radius: 4px; white-space: pre-wrap; text-align: left; font-family: 'Courier New', Courier, monospace; }
</style>
