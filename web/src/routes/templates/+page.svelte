<script lang="ts">
	import { onMount } from 'svelte';
	import * as engine from '$lib/api/engine';
	import type { TemplateInfo } from '$lib/api/types';

	let templates = $state<TemplateInfo[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let previewing = $state<string | null>(null);

	onMount(async () => {
		try {
			templates = await engine.listTemplates();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load templates';
		} finally {
			loading = false;
		}
	});

	function previewUrl(name: string): string {
		return engine.templatePreviewUrl(name);
	}
</script>

<div class="space-y-8">
	<div>
		<h1 class="text-3xl font-bold text-gray-900">Templates</h1>
		<p class="mt-1 text-gray-500">Browse available resume templates.</p>
	</div>

	{#if error}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
	{/if}

	{#if loading}
		<div class="text-gray-400">Loading templates...</div>
	{:else if templates.length === 0}
		<p class="text-gray-400">No templates found. Ensure the engine is running.</p>
	{:else}
		<div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
			{#each templates as tpl}
				<div class="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
					<div class="p-5 space-y-2">
						<div class="flex items-start justify-between">
							<h2 class="text-lg font-semibold text-gray-900">{tpl.label}</h2>
							{#if tpl.ats_friendly}
								<span class="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">ATS</span>
							{/if}
						</div>
						{#if tpl.description}
							<p class="text-sm text-gray-500">{tpl.description}</p>
						{/if}
						<div class="flex flex-wrap gap-1 pt-1">
							{#each tpl.supported_formats ?? [] as fmt}
								<span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 uppercase">{fmt}</span>
							{/each}
							{#if tpl.max_pages}
								<span class="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">max {tpl.max_pages}p</span>
							{/if}
						</div>
						{#if tpl.author}
							<p class="text-xs text-gray-400">by {tpl.author}{tpl.version ? ` v${tpl.version}` : ''}</p>
						{/if}
					</div>
					<div class="border-t border-gray-100 px-5 py-3">
						<button
							type="button"
							onclick={() => (previewing = previewing === tpl.name ? null : tpl.name)}
							class="text-sm text-blue-600 hover:underline"
						>
							{previewing === tpl.name ? 'Hide preview' : 'Preview PDF'}
						</button>
					</div>
					{#if previewing === tpl.name}
						<div class="border-t border-gray-100">
							<iframe
								src={previewUrl(tpl.name)}
								title="Preview of {tpl.label}"
								class="w-full"
								style="height: 500px;"
							></iframe>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
