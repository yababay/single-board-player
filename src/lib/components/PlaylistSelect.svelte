<script lang="ts">
	import { state as mainState, actions } from '../../routes/main.svelte';

	// Локальное состояние для отслеживания процесса синхронизации
	let isRefreshing = $state(false);

	async function handleRefresh() {
		isRefreshing = true;
		mainState.statusMessage = 'Обновление списка плейлистов из облака...';
		mainState.statusColor = '#007bff';

		try {
			// Вызываем метод загрузки файлов, который мы перевели в actions
			await actions.loadCloudFiles('playlist');
			mainState.statusMessage = `Список обновлен. Найдено плейлистов: ${mainState.playlists.length}`;
			mainState.statusColor = 'green';
		} catch (e: any) {
			mainState.statusMessage = `Не удалось обновить список: ${e.message}`;
			mainState.statusColor = 'red';
		} finally {
			isRefreshing = false;
		}
	}
</script>

<div class="form-group text-left">
	<label for="playlist-search">🔍 Выберите YAML-плейлист:</label>
	<div class="playlist-row">
		<input 
			id="playlist-search" 
			type="text" 
			placeholder="Начните вводить имя плейлиста..." 
			list="playlist-options" 
			bind:value={mainState.selectedPlaylist} 
			oninput={(e) => actions.handlePlaylistChange((e.target as HTMLInputElement).value)} 
		/>
		
		<!-- Квадратная кнопка обновления. Класс spin запускает анимацию вращения иконки -->
		<button 
			type="button" 
			class="btn-refresh" 
			onclick={handleRefresh} 
			disabled={isRefreshing || mainState.isPending}
			title="Обновить список плейлистов из бакета"
		>
			<i class="bi bi-arrow-clockwise" class:spin={isRefreshing}></i>
		</button>
	</div>

	<datalist id="playlist-options">
		{#each mainState.playlists as item}
			<option value={item}></option>
		{/each}
	</datalist>
</div>

<style>
	.form-group {
		margin-bottom: 15px;
		text-align: left;
	}
	label {
		display: block;
		font-weight: bold;
		margin-bottom: 5px;
		color: #333;
		font-size: 14px;
	}
	.playlist-row {
		display: flex;
		gap: 8px; /* Небольшой зазор между инпутом и квадратной кнопкой */
	}
	input {
		flex: 1;
		padding: 10px;
		border: 1px solid #ccc;
		border-radius: 4px;
		box-sizing: border-box;
		font-family: inherit;
		font-size: 14px;
	}
	.btn-refresh {
		width: 42px; /* Фиксированная ширина делает кнопку идеально квадратной */
		height: 42px;
		padding: 0;
		background-color: #6c757d;
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: 18px;
		transition: background-color 0.2s ease;
	}
	.btn-refresh:hover:not(:disabled) {
		background-color: #5a6268;
	}
	.btn-refresh:disabled {
		background-color: #cccccc;
		cursor: not-allowed;
	}

	/* Анимация плавного вращения иконки во время запроса к S3 */
	.spin {
		display: inline-block;
		animation: rotation 1s infinite linear;
	}
	@keyframes rotation {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}
</style>
