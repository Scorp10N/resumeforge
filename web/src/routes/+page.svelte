<script lang="ts">
	import { onMount } from 'svelte';
	import * as engine from '$lib/api/engine';
	import type { BuildResponse, AnalysisReport } from '$lib/api/types';

	let lastBuild = $state<BuildResponse | null>(null);
	let lastAnalysis = $state<AnalysisReport | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			// Try to load config to confirm engine is alive
			await engine.getConfig();
		} catch (e) {
			error = 'Engine is not reachable. Start with: uv run uvicorn resumeforge.api.app:app';
		} finally {
			loading = false;
		}
	});
</script>

<div class="space-y-8">
	<div>
		<h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
		<p class="mt-1 text-gray-500">Welcome to ResumeForge — your resume automation platform.</p>
	</div>

	{#if loading}
		<div class="text-gray-400">Connecting to engine...</div>
	{:else if error}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
			<strong>Engine offline:</strong> {error}
		</div>
	{:else}
		<div class="text-sm text-green-600 font-medium">Engine connected</div>
	{/if}

	<!-- Quick Actions -->
	<section>
		<h2 class="mb-4 text-xl font-semibold text-gray-800">Quick Actions</h2>
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
			<a
				href="/builder"
				class="flex flex-col items-center gap-2 rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm transition hover:border-blue-300 hover:shadow-md"
			>
				<span class="text-3xl">&#128196;</span>
				<span class="font-medium text-gray-800">Build Resume</span>
				<span class="text-xs text-gray-500">Choose template &amp; format</span>
			</a>
			<a
				href="/analyze"
				class="flex flex-col items-center gap-2 rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm transition hover:border-blue-300 hover:shadow-md"
			>
				<span class="text-3xl">&#128270;</span>
				<span class="font-medium text-gray-800">Analyze</span>
				<span class="text-xs text-gray-500">ATS score &amp; gaps</span>
			</a>
			<a
				href="/templates"
				class="flex flex-col items-center gap-2 rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm transition hover:border-blue-300 hover:shadow-md"
			>
				<span class="text-3xl">&#127912;</span>
				<span class="font-medium text-gray-800">Templates</span>
				<span class="text-xs text-gray-500">Browse &amp; preview</span>
			</a>
			<a
				href="/jobs"
				class="flex flex-col items-center gap-2 rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm transition hover:border-blue-300 hover:shadow-md"
			>
				<span class="text-3xl">&#128188;</span>
				<span class="font-medium text-gray-800">Jobs</span>
				<span class="text-xs text-gray-500">Saved job descriptions</span>
			</a>
		</div>
	</section>

	<!-- Data Sections -->
	<section>
		<h2 class="mb-4 text-xl font-semibold text-gray-800">Data Sections</h2>
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
			{#each ['profile', 'experience', 'skills', 'education', 'projects', 'certifications'] as section}
				<a
					href="/data/{section}"
					class="rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm transition hover:border-blue-300 hover:text-blue-700 capitalize"
				>
					{section}
				</a>
			{/each}
		</div>
	</section>
</div>
