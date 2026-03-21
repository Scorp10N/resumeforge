<script lang="ts">
	import { onMount } from 'svelte';
	import * as engine from '$lib/api/engine';
	import type { Meta } from '$lib/api/types';

	let config = $state<Meta | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');

	// Edit fields
	let aiEnabled = $state(false);
	let aiProvider = $state('openai');
	let aiModel = $state('gpt-4o');
	let aiBaseUrl = $state('');
	let aiTemp = $state(0.3);
	let engineMode = $state<'local' | 'cloud'>('local');
	let engineUrl = $state('');
	let enginePort = $state(8080);
	let defaultTemplate = $state('classic');
	let defaultFormat = $state('pdf');
	let defaultLocale = $state('en');
	let tone = $state('professional');
	let maxPages = $state(1);

	onMount(async () => {
		try {
			config = await engine.getConfig();
			// Populate fields
			aiEnabled = config.ai?.enabled ?? false;
			aiProvider = config.ai?.provider ?? 'openai';
			aiModel = config.ai?.model ?? 'gpt-4o';
			aiBaseUrl = config.ai?.base_url ?? '';
			aiTemp = config.ai?.temperature ?? 0.3;
			engineMode = config.engine?.mode ?? 'local';
			engineUrl = config.engine?.url ?? '';
			enginePort = config.engine?.port ?? 8080;
			defaultTemplate = config.default_template ?? 'classic';
			defaultFormat = config.default_format ?? 'pdf';
			defaultLocale = config.default_locale ?? 'en';
			tone = config.style?.tone ?? 'professional';
			maxPages = config.style?.max_pages ?? 1;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load config';
		} finally {
			loading = false;
		}
	});

	async function saveConfig() {
		saveStatus = 'saving';
		error = null;
		try {
			config = await engine.patchConfig({
				default_template: defaultTemplate,
				default_format: defaultFormat,
				default_locale: defaultLocale,
				engine: {
					mode: engineMode,
					url: engineUrl || null,
					port: enginePort
				},
				ai: {
					enabled: aiEnabled,
					provider: aiProvider,
					model: aiModel,
					base_url: aiBaseUrl || null,
					temperature: aiTemp
				},
				style: {
					tone,
					max_pages: maxPages
				}
			});
			saveStatus = 'saved';
			setTimeout(() => (saveStatus = 'idle'), 2500);
		} catch (e) {
			saveStatus = 'error';
			error = e instanceof Error ? e.message : 'Save failed';
		}
	}
</script>

<div class="space-y-8">
	<div>
		<h1 class="text-3xl font-bold text-gray-900">Settings</h1>
		<p class="mt-1 text-gray-500">Configure AI, engine, and default build preferences.</p>
	</div>

	{#if error}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
	{/if}

	{#if loading}
		<div class="text-gray-400">Loading config...</div>
	{:else}
		<form
			onsubmit={(e) => { e.preventDefault(); saveConfig(); }}
			class="space-y-8"
		>
			<!-- Build Defaults -->
			<section class="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
				<h2 class="font-semibold text-gray-800 text-lg">Build Defaults</h2>
				<div class="grid gap-4 sm:grid-cols-3">
					<div class="space-y-1">
						<label for="default-template" class="text-sm font-medium text-gray-700">Default Template</label>
						<input
							id="default-template"
							bind:value={defaultTemplate}
							type="text"
							class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
						/>
					</div>
					<div class="space-y-1">
						<label for="default-format" class="text-sm font-medium text-gray-700">Default Format</label>
						<select
							id="default-format"
							bind:value={defaultFormat}
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
						>
							<option value="pdf">PDF</option>
							<option value="md">Markdown</option>
							<option value="docx">DOCX</option>
						</select>
					</div>
					<div class="space-y-1">
						<label for="default-locale" class="text-sm font-medium text-gray-700">Locale</label>
						<select
							id="default-locale"
							bind:value={defaultLocale}
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
						>
							<option value="en">English</option>
							<option value="he">Hebrew</option>
						</select>
					</div>
				</div>
			</section>

			<!-- Engine Config -->
			<section class="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
				<h2 class="font-semibold text-gray-800 text-lg">Engine</h2>
				<div class="grid gap-4 sm:grid-cols-3">
					<div class="space-y-1">
						<label for="engine-mode" class="text-sm font-medium text-gray-700">Mode</label>
						<select
							id="engine-mode"
							bind:value={engineMode}
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
						>
							<option value="local">Local</option>
							<option value="cloud">Cloud</option>
						</select>
					</div>
					<div class="space-y-1">
						<label for="engine-port" class="text-sm font-medium text-gray-700">Port</label>
						<input
							id="engine-port"
							bind:value={enginePort}
							type="number"
							min={1}
							max={65535}
							class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
						/>
					</div>
					<div class="space-y-1">
						<label for="engine-url" class="text-sm font-medium text-gray-700">Cloud URL</label>
						<input
							id="engine-url"
							bind:value={engineUrl}
							type="url"
							placeholder="https://cloud.resumeforge.io"
							class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
						/>
					</div>
				</div>
			</section>

			<!-- AI Config -->
			<section class="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
				<div class="flex items-center justify-between">
					<h2 class="font-semibold text-gray-800 text-lg">AI Provider</h2>
					<label class="flex items-center gap-2 text-sm text-gray-700">
						<input
							type="checkbox"
							bind:checked={aiEnabled}
							class="h-4 w-4 rounded border-gray-300 text-blue-600"
						/>
						Enabled
					</label>
				</div>
				{#if !aiEnabled}
					<p class="text-sm text-gray-400">AI is disabled. All operations will work without AI assistance.</p>
				{/if}
				<div class="grid gap-4 sm:grid-cols-2">
					<div class="space-y-1">
						<label for="ai-provider" class="text-sm font-medium text-gray-700">Provider</label>
						<input
							id="ai-provider"
							bind:value={aiProvider}
							type="text"
							placeholder="openai"
							disabled={!aiEnabled}
							class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none disabled:bg-gray-50 disabled:text-gray-400"
						/>
					</div>
					<div class="space-y-1">
						<label for="ai-model" class="text-sm font-medium text-gray-700">Model</label>
						<input
							id="ai-model"
							bind:value={aiModel}
							type="text"
							placeholder="gpt-4o"
							disabled={!aiEnabled}
							class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none disabled:bg-gray-50 disabled:text-gray-400"
						/>
					</div>
					<div class="space-y-1">
						<label for="ai-base-url" class="text-sm font-medium text-gray-700">Base URL (optional)</label>
						<input
							id="ai-base-url"
							bind:value={aiBaseUrl}
							type="url"
							placeholder="http://localhost:11434 (Ollama)"
							disabled={!aiEnabled}
							class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none disabled:bg-gray-50 disabled:text-gray-400"
						/>
					</div>
					<div class="space-y-1">
						<label for="ai-temp" class="text-sm font-medium text-gray-700">Temperature ({aiTemp})</label>
						<input
							id="ai-temp"
							bind:value={aiTemp}
							type="range"
							min={0}
							max={1}
							step={0.05}
							disabled={!aiEnabled}
							class="w-full disabled:opacity-50"
						/>
					</div>
				</div>
			</section>

			<!-- Style -->
			<section class="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
				<h2 class="font-semibold text-gray-800 text-lg">Style</h2>
				<div class="grid gap-4 sm:grid-cols-2">
					<div class="space-y-1">
						<label for="tone" class="text-sm font-medium text-gray-700">Tone</label>
						<select
							id="tone"
							bind:value={tone}
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
						>
							<option value="professional">Professional</option>
							<option value="confident">Confident</option>
							<option value="concise">Concise</option>
						</select>
					</div>
					<div class="space-y-1">
						<label for="max-pages" class="text-sm font-medium text-gray-700">Max Pages</label>
						<input
							id="max-pages"
							bind:value={maxPages}
							type="number"
							min={1}
							max={4}
							class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
						/>
					</div>
				</div>
			</section>

			<div class="flex items-center gap-4">
				<button
					type="submit"
					disabled={saveStatus === 'saving'}
					class="rounded-lg bg-blue-600 px-6 py-2.5 font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
				>
					{saveStatus === 'saving' ? 'Saving...' : saveStatus === 'saved' ? 'Saved!' : 'Save Settings'}
				</button>
				{#if saveStatus === 'saved'}
					<span class="text-sm text-green-600">Settings saved successfully.</span>
				{:else if saveStatus === 'error'}
					<span class="text-sm text-red-600">Save failed. Check the error above.</span>
				{/if}
			</div>
		</form>
	{/if}
</div>
