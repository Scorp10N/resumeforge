<script lang="ts">
	import { onMount } from 'svelte';
	import * as engine from '$lib/api/engine';
	import type { TemplateInfo, JobDescription, BuildStreamEvent } from '$lib/api/types';
	import TemplatePicker from '$lib/components/TemplatePicker.svelte';

	let templates = $state<TemplateInfo[]>([]);
	let jobs = $state<JobDescription[]>([]);
	let selectedTemplate = $state('classic');
	let selectedFormat = $state<'md' | 'pdf' | 'docx'>('pdf');
	let selectedJob = $state('');
	let useAI = $state(false);

	let building = $state(false);
	let events = $state<BuildStreamEvent[]>([]);
	let outputUrl = $state<string | null>(null);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			[templates, jobs] = await Promise.all([engine.listTemplates(), engine.listJobs()]);
		} catch (e) {
			error = 'Could not load templates or jobs from engine.';
		}
	});

	async function runBuild() {
		building = true;
		events = [];
		outputUrl = null;
		error = null;

		try {
			for await (const evt of engine.streamBuild({
				template: selectedTemplate,
				format: selectedFormat,
				job_slug: selectedJob || undefined,
				ai: useAI
			})) {
				events = [...events, evt];
				if (evt.type === 'complete' && evt.output_path) {
					outputUrl = engine.exportDataUrl().replace('/api/data/export', '') + evt.output_path;
				}
				if (evt.type === 'error') {
					error = evt.error ?? evt.message;
					break;
				}
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Build failed';
		} finally {
			building = false;
		}
	}

	const lastEvent = $derived(events.at(-1));
	const progress = $derived(lastEvent?.progress ?? 0);
</script>

<div class="space-y-8">
	<div>
		<h1 class="text-3xl font-bold text-gray-900">Resume Builder</h1>
		<p class="mt-1 text-gray-500">Choose a template, format, and optional job to tailor to.</p>
	</div>

	{#if error}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
	{/if}

	<!-- Template Picker -->
	<section class="space-y-3">
		<h2 class="text-lg font-semibold text-gray-800">Template</h2>
		{#if templates.length === 0}
			<p class="text-sm text-gray-400">Loading templates...</p>
		{:else}
			<TemplatePicker {templates} selected={selectedTemplate} onSelect={(n) => (selectedTemplate = n)} />
		{/if}
	</section>

	<!-- Format + Job -->
	<section class="grid gap-6 sm:grid-cols-2">
		<div class="space-y-2">
			<label class="text-sm font-medium text-gray-700" for="format">Output Format</label>
			<select
				id="format"
				bind:value={selectedFormat}
				class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none"
			>
				<option value="pdf">PDF</option>
				<option value="md">Markdown</option>
				<option value="docx">DOCX</option>
			</select>
		</div>

		<div class="space-y-2">
			<label class="text-sm font-medium text-gray-700" for="job">Job Description (optional)</label>
			<select
				id="job"
				bind:value={selectedJob}
				class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none"
			>
				<option value="">None — general resume</option>
				{#each jobs as job}
					<option value={job.slug}>{job.title} @ {job.company}</option>
				{/each}
			</select>
		</div>
	</section>

	<!-- AI Toggle -->
	<div class="flex items-center gap-3">
		<input
			id="ai-toggle"
			type="checkbox"
			bind:checked={useAI}
			class="h-4 w-4 rounded border-gray-300 text-blue-600"
		/>
		<label for="ai-toggle" class="text-sm text-gray-700">
			Enable AI tailoring (requires AI configured in settings)
		</label>
	</div>

	<!-- Build Button -->
	<button
		type="button"
		onclick={runBuild}
		disabled={building}
		class="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
	>
		{building ? 'Building...' : 'Build Resume'}
	</button>

	<!-- Progress -->
	{#if building || events.length > 0}
		<section class="space-y-3">
			<h2 class="text-lg font-semibold text-gray-800">Build Progress</h2>
			{#if building}
				<div class="h-2 overflow-hidden rounded-full bg-gray-200">
					<div
						class="h-full rounded-full bg-blue-500 transition-all duration-300"
						style="width: {progress}%"
					></div>
				</div>
			{/if}
			<div class="space-y-1 rounded-lg bg-gray-900 p-4 font-mono text-xs text-green-300">
				{#each events as evt}
					<div class={evt.type === 'error' ? 'text-red-400' : evt.type === 'complete' ? 'text-green-400 font-bold' : ''}>
						[{evt.type}] {evt.message}
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Output Link -->
	{#if outputUrl}
		<div class="flex gap-4">
			<a
				href="/builder/preview?url={encodeURIComponent(outputUrl)}&format={selectedFormat}"
				class="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
			>
				Preview Resume
			</a>
			<a
				href={outputUrl}
				download
				class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
			>
				Download
			</a>
		</div>
	{/if}
</div>
