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
		
		<!-- ВКЛАДКА 2: АВТОМАТИЧЕСКАЯ ИСПРАВЛЕННАЯ ПАНЕЛЬ ТЕГОВ -->
		{:else if state.activeTab === 'tags_config'}
			<div class="expert-panel">
				<h3>✍️ Архивные метаданные медиатеки</h3>
				<div class="grid">
					<!-- 💡 ИСПРАВЛЕНИЕ: Извлекаем индекс "i" в цикле {#each} -->
					{#each state.expertTags as tag, i}
						<div class="form-group">
							<label for="tag-{tag.id}">{tag.label} ({tag.type === 'txxx' ? 'TXXX:' : ''}{tag.flag}):</label>
							<!-- 💡 ИСПРАВЛЕНИЕ: Привязываем bind:value строго по индексу массива -->
							<input 
								id="tag-{tag.id}" 
								type="text" 
								bind:value={state.expertTags[i].value} 
								placeholder={tag.placeholder}
							/>
						</div>
					{/each}
				</div>
				<p class="hint-text">💡 Поля теперь абсолютно реактивны, а проект компилируется без ошибок Svelte 5. Пустые теги игнорируются сборщиком.</p>
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
