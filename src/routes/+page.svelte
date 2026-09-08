<script lang="ts">
	import { onMount } from 'svelte';
	import { state, actions } from './main.svelte';

	onMount(() => {
		actions.checkSession();
	});
</script>

<div class="container">
	<h2>Генератор тегов медиатеки v2.2</h2>

	{#if !state.isAuthorized}
		<div class="auth-box">
			<label for="token-input">🔑 Введите IAM-токен Yandex Cloud:</label>
			<div class="token-row">
				<input type="password" id="token-input" placeholder="t1.9euelZq..." bind:value={state.iamToken} />
				<button onclick={() => actions.login()}>Войти</button>
			</div>
		</div>
	{:else}
		<button class="logout-link" onclick={() => actions.clearToken()}>
			<i class="bi bi-box-arrow-right"></i> Выйти
		</button>

		<div class="tabs">
			<button class="tab-btn" class:active={state.activeTab === 'tagger'} onclick={() => state.activeTab = 'tagger'}>🎙 Разметка треков</button>
			<button class="tab-btn" class:active={state.activeTab === 'tags_config'} onclick={() => state.activeTab = 'tags_config'}>🏷 Глобальные теги</button>
			<button class="tab-btn" class:active={state.activeTab === 'instructions'} onclick={() => state.activeTab = 'instructions'}>⚙️ Инструкции ИИ ({state.instructions.length})</button>
		</div>

		<!-- ВКЛАДКА 1: РАЗМЕТКА -->
		{#if state.activeTab === 'tagger'}
			<div class="form-group">
				<label for="playlist-search">🔍 Выберите YAML-плейлист:</label>
				<input id="playlist-search" type="text" placeholder="Начните вводить имя..." list="playlist-options" bind:value={state.selectedPlaylist} oninput={(e) => actions.handlePlaylistChange((e.target as HTMLInputElement).value)} />
				<datalist id="playlist-options">
					{#each state.playlists as item}<option value={item}></option>{/each}
				</datalist>
			</div>

			<div class="form-group">
				<label for="query-input">Задание для ИИ-агента:</label>
				<input id="query-input" type="text" bind:value={state.query} />
			</div>

			<div class="form-group">
				<label for="yaml-input">Фрагмент YAML-данных:</label>
				<textarea id="yaml-input" class="code-input" rows="12" bind:value={state.yamlData}></textarea>
			</div>

			<button onclick={() => actions.processRequest()} disabled={state.isPending}> Сгенерировать .sh скрипт </button>
		
		<!-- ВКЛАДКА 2: ГЛОБАЛЬНЫЕ ТЕГИ -->
		{:else if state.activeTab === 'tags_config'}
			<div class="expert-panel">
				<h3>✍️ Архивные метаданные (Применятся ко всему списку)</h3>
				<div class="grid">
					<div><label for="exp-artist">Исполнитель:</label><input id="exp-artist" type="text" bind:value={state.expertArtist} /></div>
					<div><label for="exp-composer">Композитор:</label><input id="exp-composer" type="text" bind:value={state.expertComposer} /></div>
					<div><label for="exp-album">Альбом:</label><input id="exp-album" type="text" bind:value={state.expertAlbum} /></div>
					<div><label for="exp-genre">Жанр:</label><input id="exp-genre" type="text" bind:value={state.expertGenre} /></div>
					<div><label for="exp-year">Год издания:</label><input id="exp-year" type="text" bind:value={state.expertReleaseYear} /></div>
					<div><label for="exp-pub">Издатель:</label><input id="exp-pub" type="text" bind:value={state.expertPublisher} /></div>
				</div>

				<h3 style="margin-top: 20px; border-top: 1px solid #ddd; padding-top: 15px;">🎼 Пользовательские фреймы (TXXX)</h3>
				<div class="grid">
					<div><label for="exp-inst">Инструмент:</label><input id="exp-inst" type="text" bind:value={state.expertInstrument} /></div>
					<div><label for="exp-style">Стиль:</label><input id="exp-style" type="text" bind:value={state.expertStyle} /></div>
					<div><label for="exp-mood">Настроение:</label><input id="exp-mood" type="text" bind:value={state.expertMood} /></div>
					<div><label for="exp-period">Эпоха:</label><input id="exp-period" type="text" bind:value={state.expertPeriod} /></div>
				</div>
			</div>

		<!-- ВКЛАДКА 3: ИНСТРУКЦИИ -->
		{:else if state.activeTab === 'instructions'}
			<div class="form-group">
				<label for="inst-select">📄 Выберите системную инструкцию из бакета:</label>
				<select id="inst-select" bind:value={state.selectedInstruction} onchange={() => actions.loadInstructionText(state.selectedInstruction)}>
					{#each state.instructions as inst}
						<option value={inst}>{inst}</option>
					{/each}
				</select>
			</div>

			<div class="form-group">
				<label for="inst-text">Содержимое промпта:</label>
				<textarea id="inst-text" class="code-input" rows="15" bind:value={state.currentInstructionText}></textarea>
			</div>
		{/if}
	{/if}

	{#if state.statusMessage}<div id="status" style="color: {state.statusColor}">{state.statusMessage}</div>{/if}
	{#if state.outputText}<pre id="output">{state.outputText}</pre>{/if}
</div>

<style>
	.container { position: relative; background: #fff; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 100%; max-width: 800px; }
	.logout-link { position: absolute; top: 25px; right: 25px; background: none; border: none; color: #dc3545; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; width: auto; font-size: 14px; }
	.tabs { display: flex; gap: 5px; border-bottom: 2px solid #ddd; margin-bottom: 20px; }
	.tab-btn { background: #f1f1f1; border: 1px solid #ddd; border-bottom: none; padding: 10px 20px; cursor: pointer; border-radius: 4px 4px 0 0; font-weight: bold; color: #555; width: auto; font-size: 14px; }
	.tab-btn.active { background: #007bff; color: white; border-color: #007bff; }
	.expert-panel { text-align: left; }
	.expert-panel h3 { margin-top: 0; margin-bottom: 15px; color: #222; font-size: 16px; font-weight: bold; }
	.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
	.auth-box { background: #fff3cd; padding: 20px; border-radius: 6px; text-align: left; }
	.token-row { display: flex; gap: 10px; margin-top: 8px; }
	.form-group { margin-bottom: 15px; text-align: left; }
	label { display: block; font-weight: bold; margin-bottom: 5px; color: #333; font-size: 14px; }
	input[type='text'], input[type='password'], select, textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-family: inherit; font-size: 14px; }
	.code-input { font-family: 'Courier New', monospace; font-size: 13px; background-color: #fafafa; }
	button { background-color: #007bff; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; width: 100%; }
	button:hover { background-color: #0056b3; }
	button:disabled { background-color: #cccccc; cursor: not-allowed; }
	#status { margin-top: 15px; font-weight: bold; text-align: left; }
	#output { margin-top: 20px; padding: 15px; background: #e9ecef; border-left: 4px solid #007bff; white-space: pre-wrap; text-align: left; font-family: 'Courier New', monospace; }
</style>
