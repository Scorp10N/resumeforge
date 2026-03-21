<script lang="ts">
	interface Props {
		url: string | null;
		format: string;
	}

	let { url, format }: Props = $props();

	const isPdf = $derived(format === 'pdf');
	const isMarkdown = $derived(format === 'md');
</script>

<div class="flex h-full min-h-[400px] flex-col rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
	{#if !url}
		<div class="flex flex-1 items-center justify-center text-gray-400 p-8">
			<div class="text-center">
				<div class="text-5xl mb-3">&#128196;</div>
				<p class="text-sm">No preview available yet. Build your resume first.</p>
			</div>
		</div>
	{:else if isPdf}
		<iframe
			src={url}
			title="Resume PDF Preview"
			class="w-full flex-1"
			style="min-height: 600px;"
		></iframe>
	{:else if isMarkdown}
		<div class="p-4">
			<a
				href={url}
				target="_blank"
				rel="noopener noreferrer"
				class="text-sm text-blue-600 hover:underline"
			>
				Open Markdown output
			</a>
		</div>
		<iframe
			src={url}
			title="Resume Markdown Preview"
			class="w-full flex-1"
			style="min-height: 500px;"
		></iframe>
	{:else}
		<div class="flex flex-1 flex-col items-center justify-center gap-4 p-8">
			<p class="text-sm text-gray-600">
				Format <strong>{format}</strong> — download to view.
			</p>
			<a
				href={url}
				download
				class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
			>
				Download Resume
			</a>
		</div>
	{/if}
</div>
