<script lang="ts">
	import { onMount } from 'svelte';
	import { state, actions } from './main.svelte';
	import Genre from '$lib/components/Genre.svelte';
	import PlaylistSelect from '$lib/components/PlaylistSelect.svelte'; // 💡 Импортируем новый компонент
	import { PUBLIC_PAGE_TITLE } from '$env/static/public';
	
	onMount(() => {
		actions.checkSession();
	});
</script>

<div class="container">
	<h3>{PUBLIC_PAGE_TITLE}</h3>

	{#if !state.isAuthorized}
		<div class="auth-box">
			<label for="token-input">🔑 Введите IAM-токен Yandex Cloud:</label>
			<div class="token-row">
				<input type="password" id="token-input" placeholder="t1.9euelZq..." bind:value={state.iamToken} />
				<button onclick={() => actions.login()}>Войти</button>
			</div>
		</div>
	{:else}
		<section id="playlist">
			<button class="logout-link" onclick={() => actions.clearToken()}>
				<i class="bi bi-box-arrow-right"></i> Выйти
			</button>

			<!-- Четырехвкладочная навигационная панель -->
			<div class="tabs">
				<button class="tab-btn" class:active={state.activeTab === 'tagger'} onclick={() => state.activeTab = 'tagger'}>🎙 Разметка треков</button>
				<button class="tab-btn" class:active={state.activeTab === 'tags_config'} onclick={() => state.activeTab = 'tags_config'}>🏷 Глобальные теги</button>
				<button class="tab-btn" class:active={state.activeTab === 'instructions'} onclick={() => state.activeTab = 'instructions'}>⚙️ Инструкции ИИ ({state.instructions.length})</button>
				<button class="tab-btn" class:active={state.activeTab === 'testing'} onclick={() => state.activeTab = 'testing'}>🔍 Тестирование</button>
			</div>

			<!-- ВКЛАДКА 1: РАЗМЕТКА -->
			{#if state.activeTab === 'tagger'}
				<PlaylistSelect />

				<div class="form-group">
					<label for="query-input">Задание для ИИ-агента:</label>
					<input id="query-input" type="text" bind:value={state.query} />
				</div>

				<div class="form-group">
					<label for="yaml-input">Фрагмент YAML-данных:</label>
					<textarea id="yaml-input" class="code-input" rows="12" bind:value={state.yamlData}></textarea>
				</div>
				
				<!-- Перенесли вывод ответа разметки сюда -->
				{#if state.outputText}
					<pre id="output">{state.outputText}</pre>
				{/if}
			
			<!-- ВКЛАДКА 2: ГЛОБАЛЬНЫЕ ТЕГИ -->
			{:else if state.activeTab === 'tags_config'}
				<div class="expert-panel">
					<h3>✍️ Архивные метаданные медиатеки</h3>
					<form autocomplete="on" onsubmit={() => false}>
						<div class="grid">
							{#each state.expertTags as tag, i}
								{#if tag.id !== 'genre'}
									<div class="form-group">
										<label for="tag-{tag.id}">{tag.label} ({tag.type === 'txxx' ? 'TXXX:' : ''}{tag.flag}):</label>
										<input 
											id="tag-{tag.id}" 
											name="archive-tag-{tag.id}"
											type="text" 
											bind:value={state.expertTags[i].value} 
											placeholder={tag.placeholder}
											oninput={(e) => actions.saveTagValue(tag.id, (e.target as HTMLInputElement).value)}
										/>
									</div>
								{:else}
									<Genre />
								{/if}
							{/each}
						</div>
					</form>
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
				
				{#if state.outputText}
					<pre id="output">{state.outputText}</pre>
				{/if}

			<!-- 💡 НОВАЯ ВКЛАДКА 4: ТЕСТИРОВАНИЕ РЕКОМЕНДАЦИЙ -->
			{:else if state.activeTab === 'testing'}
				<div class="expert-panel" id="recommendations">
					<h3>🔍 Поиск музыкальных рекомендаций (RAG)</h3>
					
					<div class="form-group text-left">
						<!-- label for="recommend-input">Что послушать?</label -->
						<div class="search-row">
							<input 
								id="recommend-input" 
								type="text" 
								placeholder="Найди ноктюрн Шопена" 
								bind:value={state.recommendQuery}
								disabled={state.isPending}
								onkeydown={(e) => e.key === 'Enter' && actions.processRecommendation()}
							/>
							<button 
								type="button" 
								class="btn-search" 
								onclick={() => actions.processRecommendation()} 
								disabled={state.isPending || !state.recommendQuery.trim()}
							>
								<i class="bi bi-search"></i> Найти
							</button>
						</div>
					</div>

					<!-- Красивое форматированное поле ответа ИИ-рекомендатора -->
					{#if state.recommendOutput}
						<div class="recommendation-result">
							<i class="bi bi-music-note-beaming text-primary"></i> 
							<span>{state.recommendOutput}</span>
						</div>
					{/if}
					<p class="text-muted" style="margin-top: 10px; font-size: .875rem;">💡 Рекомендации формируются на основе векторного поиска по архивным метаданным и инструкциям ИИ.</p>
				</div>
			{/if}
			<!-- Горизонтальная панель управления (Toolbar): Скрываем её на вкладке тестирования, чтобы не путать кнопки -->
			{#if state.activeTab !== 'testing'}
				<div class="toolbar-panel">
					<button class="btn-toolbar btn-warning" onclick={() => actions.clearExpertTags()}>
						<i class="bi bi-trash"></i> Очистить теги
					</button>
					<button class="btn-toolbar btn-primary" onclick={() => actions.processRequest()} disabled={state.isPending}>
						<i class="bi bi-terminal"></i> Сгенерировать скрипт
					</button>
				</div>
			{/if}
		</section>
	{/if}


	<!-- 💡 В самом низу остаются ТОЛЬКО отладочные, короткие системные сообщения -->
	{#if state.statusMessage}
		<div id="status" style="color: {state.statusColor}">{state.statusMessage}</div>
	{/if}
</div>

<style>
	h3 { margin-bottom: 1.7rem; color: #333; font-size: 1.25rem; }
	.container { position: relative; background: #fff; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 100%; max-width: 800px; }
	.logout-link { 
		/* position: absolute; top: 25px; */
		position: fixed; top: 25px; right: 25px; 
		background: none; border: none; 
		color: #dc3545; cursor: pointer; display: inline-flex; 
		align-items: center; gap: 5px; width: auto; font-size: 14px; 
	}
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

	/* Стили горизонтальной панели управления */
	.toolbar-panel {
		display: flex;
		justify-content: space-between;
		align-items: center;
		background-color: #f8f9fa;
		border: 1px solid #e9ecef;
		padding: 12px 15px;
		border-radius: 6px;
		margin-bottom: 20px;
	}

	/* Базовый класс для кнопок на панели */
	.btn-toolbar {
		width: auto; /* Отменяем 100%-ширину, делаем естественный размер */
		padding: 10px 18px;
		font-size: 14px;
		font-weight: bold;
		display: inline-flex;
		align-items: center;
		gap: 6px; /* Зазор между иконкой и текстом */
		transition: background-color 0.2s ease;
	}

	/* Кнопка генерации (Синяя) */
	.btn-primary {
		background-color: #007bff;
		color: white;
	}
	.btn-primary:hover:not(:disabled) {
		background-color: #0056b3;
	}

	/* Кнопка очистки (Оранжевая/Варнинг) */
	.btn-warning {
		background-color: #ffc107;
		color: #212529; /* Темный текст для хорошей читаемости на желтом */
	}
	.btn-warning:hover {
		background-color: #e0a800;
	}
	/* Стили для вкладки тестирования рекомендаций */
	.search-row {
		display: flex;
		gap: 8px;
		margin-bottom: 5rem;
	}
	.btn-search {
		width: auto;
		padding: 0 25px;
		background-color: #28a745; /* Зеленая кнопка поиска */
		color: white;
		border: none;
		border-radius: 4px;
		font-weight: bold;
		display: inline-flex;
		align-items: center;
		gap: 8px;
	}
	.btn-search:hover:not(:disabled) {
		background-color: #218838;
	}
	.btn-search:disabled {
		background-color: #cccccc;
		cursor: not-allowed;
	}
	
	/* Плашка вывода рекомендации */
	.recommendation-result {
		margin-top: 20px;
		padding: 15px 20px;
		background-color: #e8f4fd;
		border-left: 5px solid #007bff;
		border-radius: 4px;
		font-size: 15px;
		font-weight: bold;
		color: #004085;
		display: flex;
		align-items: center;
		gap: 12px;
		text-align: left;
	}
	.recommendation-result i {
		font-size: 20px;
	}

	#recommendations {
		min-height: 50vh; /* Минимальная высота для вкладки тестирования */
		display: flex;
		flex-direction: column;
		justify-content: space-between;
	}


</style>
