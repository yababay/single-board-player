<script lang="ts">
	import favicon from '$lib/assets/ai-music.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Обработка плейлистов</title>
</svelte:head>

<main>
{@render children()}
</main>

<!-- Изменение в src/routes/+layout.svelte -->
<style>
	main {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		box-sizing: border-box;
		min-height: 100vh; /* Позволяет контенту расти вниз при скролле */
		padding: 20px 0;
	}
</style>


