<script lang="ts">
	import { onMount } from 'svelte';
	import * as engine from '$lib/api/engine';
	import type { AnalysisReport, JobDescription } from '$lib/api/types';
	import ATSScore from '$lib/components/ATSScore.svelte';

	let jobs = $state<JobDescription[]>([]);
	let selectedJob = $state('');
	let report = $state<AnalysisReport | null>(null);
	let running = $state(false);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			jobs = await engine.listJobs();
		} catch {
			// jobs list is optional
		}
	});

	async function runAnalysis() {
		running = true;
		error = null;
		report = null;
		try {
			report = await engine.analyze(selectedJob || undefined);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Analysis failed';
		} finally {
			running = false;
		}
	}

	const overallPct = $derived(report ? Math.round(report.overall_score * 100) : 0);
</script>

<div class="space-y-8">
	<div>
		<h1 class="text-3xl font-bold text-gray-900">Resume Analysis</h1>
		<p class="mt-1 text-gray-500">Run ATS scoring, gap analysis, and quality checks.</p>
	</div>

	{#if error}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
	{/if}

	<!-- Controls -->
	<div class="flex flex-wrap gap-4 items-end">
		<div class="space-y-1">
			<label for="job-select" class="text-sm font-medium text-gray-700">Job Description (optional)</label>
			<select
				id="job-select"
				bind:value={selectedJob}
				class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none"
			>
				<option value="">None — general analysis</option>
				{#each jobs as job}
					<option value={job.slug}>{job.title} @ {job.company}</option>
				{/each}
			</select>
		</div>
		<button
			type="button"
			onclick={runAnalysis}
			disabled={running}
			class="rounded-lg bg-blue-600 px-5 py-2 font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
		>
			{running ? 'Analyzing...' : 'Run Analysis'}
		</button>
	</div>

	<!-- Report -->
	{#if report}
		<div class="space-y-6">
			<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				<ATSScore score={overallPct} label="Overall Score" />
				{#each report.results as result}
					<ATSScore score={Math.round(result.score * 100)} label={result.label} />
				{/each}
			</div>

			{#if report.summary}
				<div class="rounded-lg border border-gray-200 bg-white p-4">
					<h2 class="font-semibold text-gray-800 mb-2">Summary</h2>
					<p class="text-sm text-gray-600">{report.summary}</p>
				</div>
			{/if}

			<!-- Per-analyzer findings -->
			{#each report.results as result}
				{#if result.findings.length > 0}
					<div class="rounded-lg border border-gray-200 bg-white overflow-hidden">
						<div class="flex items-center justify-between border-b border-gray-100 px-4 py-3">
							<h3 class="font-semibold text-gray-800">{result.label}</h3>
							<span class={`text-xs font-medium px-2 py-0.5 rounded-full ${result.passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
								{result.passed ? 'Pass' : 'Fail'}
							</span>
						</div>
						<ul class="divide-y divide-gray-50">
							{#each result.findings as finding}
								<li class="px-4 py-3">
									<div class="flex items-start gap-3">
										<span class={`mt-0.5 text-xs font-bold uppercase ${finding.severity === 'critical' ? 'text-red-600' : finding.severity === 'warning' ? 'text-yellow-600' : 'text-blue-600'}`}>
											{finding.severity}
										</span>
										<div>
											<p class="text-sm text-gray-800">{finding.message}</p>
											{#if finding.suggestion}
												<p class="mt-0.5 text-xs text-gray-500">{finding.suggestion}</p>
											{/if}
										</div>
									</div>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			{/each}

			<p class="text-xs text-gray-400">Generated at: {report.generated_at}</p>
		</div>
	{/if}
</div>
