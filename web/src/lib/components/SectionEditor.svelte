<script lang="ts">
	interface Props {
		section: string;
		data: unknown;
	}

	let { section, data }: Props = $props();

	const formatted = $derived(
		JSON.stringify(data, null, 2)
	);
</script>

<div class="rounded-xl border border-gray-200 bg-white shadow-sm">
	<div class="flex items-center justify-between border-b border-gray-100 px-4 py-3">
		<h3 class="font-semibold text-gray-800 capitalize">{section}</h3>
		<span class="text-xs text-gray-400">Read-only view</span>
	</div>
	<div class="overflow-auto p-4">
		<pre class="text-xs text-gray-700 whitespace-pre-wrap break-words font-mono leading-relaxed">{formatted}</pre>
	</div>
</div>
