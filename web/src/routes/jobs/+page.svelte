<script lang="ts">
	import { onMount } from 'svelte';
	import * as engine from '$lib/api/engine';
	import type { JobDescription } from '$lib/api/types';

	let jobs = $state<JobDescription[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// New job form state
	let showForm = $state(false);
	let formTitle = $state('');
	let formCompany = $state('');
	let formDescription = $state('');
	let formRequirements = $state('');
	let formNiceToHave = $state('');
	let formLanguage = $state('en');
	let formNotes = $state('');
	let saving = $state(false);

	onMount(async () => {
		await loadJobs();
	});

	async function loadJobs() {
		loading = true;
		try {
			jobs = await engine.listJobs();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load jobs';
		} finally {
			loading = false;
		}
	}

	async function addJob() {
		if (!formTitle || !formCompany) return;
		saving = true;
		error = null;
		try {
			await engine.createJob({
				title: formTitle,
				company: formCompany,
				description: formDescription,
				requirements: formRequirements.split('\n').map((s) => s.trim()).filter(Boolean),
				nice_to_have: formNiceToHave.split('\n').map((s) => s.trim()).filter(Boolean),
				language: formLanguage,
				notes: formNotes,
				saved_date: new Date().toISOString().slice(0, 10)
			});
			showForm = false;
			formTitle = '';
			formCompany = '';
			formDescription = '';
			formRequirements = '';
			formNiceToHave = '';
			formNotes = '';
			await loadJobs();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save job';
		} finally {
			saving = false;
		}
	}

	async function removeJob(slug: string) {
		try {
			await engine.deleteJob(slug);
			jobs = jobs.filter((j) => j.slug !== slug);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Delete failed';
		}
	}
</script>

<div class="space-y-8">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-3xl font-bold text-gray-900">Jobs</h1>
			<p class="mt-1 text-gray-500">Saved job descriptions for tailoring resumes.</p>
		</div>
		<button
			type="button"
			onclick={() => (showForm = !showForm)}
			class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
		>
			{showForm ? 'Cancel' : '+ Add Job'}
		</button>
	</div>

	{#if error}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
	{/if}

	<!-- Add Job Form -->
	{#if showForm}
		<div class="rounded-xl border border-blue-200 bg-blue-50 p-6 space-y-4">
			<h2 class="font-semibold text-gray-800">New Job Description</h2>
			<div class="grid gap-4 sm:grid-cols-2">
				<div class="space-y-1">
					<label class="text-sm font-medium text-gray-700" for="job-title">Job Title *</label>
					<input
						id="job-title"
						bind:value={formTitle}
						type="text"
						placeholder="Senior Security Engineer"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
					/>
				</div>
				<div class="space-y-1">
					<label class="text-sm font-medium text-gray-700" for="job-company">Company *</label>
					<input
						id="job-company"
						bind:value={formCompany}
						type="text"
						placeholder="Acme Corp"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
					/>
				</div>
			</div>
			<div class="space-y-1">
				<label class="text-sm font-medium text-gray-700" for="job-desc">Description</label>
				<textarea
					id="job-desc"
					bind:value={formDescription}
					rows={5}
					placeholder="Full job description text..."
					class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
				></textarea>
			</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div class="space-y-1">
					<label class="text-sm font-medium text-gray-700" for="job-reqs">Requirements (one per line)</label>
					<textarea
						id="job-reqs"
						bind:value={formRequirements}
						rows={4}
						placeholder="Application Security&#10;Kubernetes&#10;SAST/DAST"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
					></textarea>
				</div>
				<div class="space-y-1">
					<label class="text-sm font-medium text-gray-700" for="job-nice">Nice to Have (one per line)</label>
					<textarea
						id="job-nice"
						bind:value={formNiceToHave}
						rows={4}
						placeholder="CS Degree&#10;Penetration Testing"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
					></textarea>
				</div>
			</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div class="space-y-1">
					<label class="text-sm font-medium text-gray-700" for="job-lang">Language</label>
					<select
						id="job-lang"
						bind:value={formLanguage}
						class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
					>
						<option value="en">English</option>
						<option value="he">Hebrew</option>
					</select>
				</div>
				<div class="space-y-1">
					<label class="text-sm font-medium text-gray-700" for="job-notes">Notes</label>
					<input
						id="job-notes"
						bind:value={formNotes}
						type="text"
						placeholder="Any notes about this role"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
					/>
				</div>
			</div>
			<button
				type="button"
				onclick={addJob}
				disabled={saving || !formTitle || !formCompany}
				class="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
			>
				{saving ? 'Saving...' : 'Save Job'}
			</button>
		</div>
	{/if}

	<!-- Jobs List -->
	{#if loading}
		<div class="text-gray-400">Loading jobs...</div>
	{:else if jobs.length === 0}
		<div class="rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center text-gray-400">
			<p>No jobs saved yet. Add one above to start tailoring your resume.</p>
		</div>
	{:else}
		<div class="space-y-4">
			{#each jobs as job}
				<div class="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
					<div class="flex items-start justify-between gap-4">
						<div class="flex-1 min-w-0">
							<h3 class="font-semibold text-gray-900">{job.title}</h3>
							<p class="text-sm text-gray-500">{job.company}</p>
							{#if job.notes}
								<p class="mt-1 text-xs text-gray-400">{job.notes}</p>
							{/if}
							{#if job.requirements && job.requirements.length > 0}
								<div class="mt-2 flex flex-wrap gap-1">
									{#each job.requirements.slice(0, 6) as req}
										<span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{req}</span>
									{/each}
									{#if job.requirements.length > 6}
										<span class="text-xs text-gray-400">+{job.requirements.length - 6} more</span>
									{/if}
								</div>
							{/if}
						</div>
						<div class="flex items-center gap-2 flex-shrink-0">
							<a
								href="/builder?job={job.slug}"
								class="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
							>
								Build
							</a>
							<a
								href="/analyze?job={job.slug}"
								class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
							>
								Analyze
							</a>
							<button
								type="button"
								onclick={() => removeJob(job.slug)}
								class="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
							>
								Delete
							</button>
						</div>
					</div>
					{#if job.saved_date}
						<p class="mt-3 text-xs text-gray-400">Saved: {job.saved_date}</p>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
