<script lang="ts">
	import { onMount } from 'svelte';
	import { state, actions } from '../../routes/main.svelte';
	import genresData from '$lib/assets/id3-genres.json';

	// Фильтруем список жанров, оставляя только те, у которых visible !== false
	const visibleGenres = genresData.filter(g => !!g.visible)  as { id: number; russian: string; english: string; visible?: boolean }[];

	// Находим индекс тега жанра в нашем глобальном массиве тегов, чтобы мутировать его напрямую
	const genreTagIndex = state.expertTags.findIndex(t => t.id === 'genre');

	onMount(() => {
		// Подтягиваем сохраненный жанр из localStorage при инициализации
		const savedGenre = localStorage.getItem('tag_val_genre');
		if (savedGenre && genreTagIndex !== -1) {
			state.expertTags[genreTagIndex].value = savedGenre;
		}
	});

	function handleGenreChange(e: Event) {
		const select = e.target as HTMLSelectElement;
		const selectedValue = select.value;

		if (genreTagIndex !== -1) {
			// Обновляем глобальное реактивное состояние по индексу
			state.expertTags[genreTagIndex].value = selectedValue;
			// Дублируем в localStorage, чтобы значение не потерялось по F5
			actions.saveTagValue('genre', selectedValue);
		}
	}
</script>

<div class="form-group text-left">
	<label for="genre-select">Жанр (--genre):</label>
	<!-- Используем значение из глобального state для двусторонней синхронизации -->
	<select 
		id="genre-select" 
		value={genreTagIndex !== -1 ? state.expertTags[genreTagIndex].value : ''} 
		onchange={handleGenreChange}
	>
		<option value="" selected>-- Выберите стандартный жанр --</option>
		{#each visibleGenres as genre}
			<!-- В качестве значения подставляем красивую строковую нотацию для eyeD3 -->
			<option value="{genre.russian} ({genre.id})">
				{genre.russian} ({genre.english}, id={genre.id})
			</option>
		{/each}
	</select>
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
	select {
		width: 100%;
		padding: 10px;
		border: 1px solid #ccc;
		border-radius: 4px;
		box-sizing: border-box;
		font-family: inherit;
		font-size: 14px;
		background-color: #fff;
	}
</style>