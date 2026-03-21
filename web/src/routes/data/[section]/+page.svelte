<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import * as engine from '$lib/api/engine';
	import type { SectionData } from '$lib/api/types';
	import SectionEditor from '$lib/components/SectionEditor.svelte';

	const section = $derived($page.params.section ?? '');

	let data = $state<SectionData | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let editJson = $state('');
	let editMode = $state(false);

	$effect(() => {
		// Reload when section changes
		const s = section;
		loading = true;
		error = null;
		data = null;
		engine
			.getSection(s)
			.then((d) => {
				data = d;
				editJson = JSON.stringify(d, null, 2);
			})
			.catch((e) => {
				error = e instanceof Error ? e.message : 'Failed to load section';
			})
			.finally(() => {
				loading = false;
			});
	});

	async function saveSection() {
		if (!editJson) return;
		saveStatus = 'saving';
		try {
			const parsed = JSON.parse(editJson) as SectionData;
			data = await engine.putSection(section, parsed);
			editJson = JSON.stringify(data, null, 2);
			saveStatus = 'saved';
			editMode = false;
			setTimeout(() => (saveStatus = 'idle'), 2000);
		} catch (e) {
			saveStatus = 'error';
			error = e instanceof Error ? e.message : 'Save failed';
		}
	}

	const knownSections = ['profile', 'experience', 'skills', 'education', 'projects', 'certifications', 'meta'];
</script>

<div class="space-y-6">
	<div class="flex items-center gap-4">
		<div>
			<h1 class="text-3xl font-bold text-gray-900 capitalize">{section}</h1>
			<p class="mt-1 text-gray-500">View and edit this data section.</p>
		</div>
	</div>

	<!-- Section nav -->
	<nav class="flex flex-wrap gap-2">
		{#each knownSections as s}
			<a
				href="/data/{s}"
				class="rounded-full px-3 py-1 text-xs font-medium transition capitalize {s === section
					? 'bg-blue-600 text-white'
					: 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
			>
				{s}
			</a>
		{/each}
	</nav>

	{#if error}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
	{/if}

	{#if loading}
		<div class="text-gray-400">Loading...</div>
	{:else if data !== null}
		{#if editMode}
			<div class="space-y-3">
				<textarea
					bind:value={editJson}
					rows={30}
					class="w-full rounded-lg border border-gray-300 p-3 font-mono text-xs focus:border-blue-500 focus:outline-none"
					spellcheck={false}
				></textarea>
				<div class="flex gap-3">
					<button
						type="button"
						onclick={saveSection}
						disabled={saveStatus === 'saving'}
						class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
					>
						{saveStatus === 'saving' ? 'Saving...' : saveStatus === 'saved' ? 'Saved!' : 'Save'}
					</button>
					<button
						type="button"
						onclick={() => { editMode = false; error = null; }}
						class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
					>
						Cancel
					</button>
				</div>
			</div>
		{:else}
			<SectionEditor {section} data={data} />
			<button
				type="button"
				onclick={() => (editMode = true)}
				class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
			>
				Edit JSON
			</button>
		{/if}
	{/if}
</div>
