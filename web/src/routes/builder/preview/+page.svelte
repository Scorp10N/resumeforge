<script lang="ts">
	import { page } from '$app/stores';
	import ResumePreview from '$lib/components/ResumePreview.svelte';

	const url = $derived(decodeURIComponent($page.url.searchParams.get('url') ?? ''));
	const format = $derived($page.url.searchParams.get('format') ?? 'pdf');
</script>

<div class="space-y-4">
	<div class="flex items-center gap-4">
		<a href="/builder" class="text-sm text-blue-600 hover:underline">&#8592; Back to Builder</a>
		<h1 class="text-2xl font-bold text-gray-900">Resume Preview</h1>
	</div>

	<ResumePreview {url} {format} />
</div>
