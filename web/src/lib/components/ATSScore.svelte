<script lang="ts">
	interface Props {
		score: number;
		label?: string;
	}

	let { score, label = 'ATS Score' }: Props = $props();

	const pct = $derived(Math.min(100, Math.max(0, Math.round(score))));

	const colorClass = $derived(
		pct >= 75
			? 'text-green-600 bg-green-50 border-green-200'
			: pct >= 50
				? 'text-yellow-600 bg-yellow-50 border-yellow-200'
				: 'text-red-600 bg-red-50 border-red-200'
	);

	const barColor = $derived(pct >= 75 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500');
</script>

<div class="rounded-lg border p-4 {colorClass}">
	<div class="flex items-center justify-between">
		<span class="text-sm font-medium">{label}</span>
		<span class="text-2xl font-bold">{pct}%</span>
	</div>
	<div class="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-200">
		<div
			class="h-full rounded-full transition-all duration-500 {barColor}"
			style="width: {pct}%"
		></div>
	</div>
</div>
