<script lang="ts">
	import type { TemplateInfo } from '$lib/api/types';

	interface Props {
		templates: TemplateInfo[];
		selected: string;
		onSelect: (name: string) => void;
	}

	let { templates, selected, onSelect }: Props = $props();
</script>

<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
	{#each templates as tpl}
		<button
			type="button"
			onclick={() => onSelect(tpl.name)}
			class="rounded-xl border-2 p-4 text-left transition {selected === tpl.name
				? 'border-blue-500 bg-blue-50'
				: 'border-gray-200 bg-white hover:border-blue-300'}"
		>
			<div class="flex items-start justify-between gap-2">
				<div>
					<p class="font-semibold text-gray-900">{tpl.label}</p>
					{#if tpl.description}
						<p class="mt-1 text-sm text-gray-500">{tpl.description}</p>
					{/if}
				</div>
				{#if selected === tpl.name}
					<span class="text-blue-600 text-lg">&#10003;</span>
				{/if}
			</div>

			<div class="mt-3 flex flex-wrap gap-1">
				{#if tpl.ats_friendly}
					<span class="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
						ATS Friendly
					</span>
				{/if}
				{#each tpl.supported_formats ?? [] as fmt}
					<span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 uppercase">
						{fmt}
					</span>
				{/each}
				{#if tpl.max_pages}
					<span class="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
						max {tpl.max_pages}p
					</span>
				{/if}
			</div>
		</button>
	{/each}
</div>
