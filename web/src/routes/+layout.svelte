<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();

	const navLinks = [
		{ href: '/', label: 'Dashboard' },
		{ href: '/builder', label: 'Builder' },
		{ href: '/analyze', label: 'Analyze' },
		{ href: '/templates', label: 'Templates' },
		{ href: '/jobs', label: 'Jobs' },
		{ href: '/settings', label: 'Settings' }
	];
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>ResumeForge</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 text-gray-900">
	<header class="border-b border-gray-200 bg-white shadow-sm">
		<nav class="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
			<a href="/" class="flex items-center gap-2 font-bold text-blue-700 text-lg">
				ResumeForge
			</a>
			<div class="flex gap-1">
				{#each navLinks as link}
					<a
						href={link.href}
						class="rounded px-3 py-1.5 text-sm font-medium text-gray-600 transition hover:bg-blue-50 hover:text-blue-700"
					>
						{link.label}
					</a>
				{/each}
			</div>
		</nav>
	</header>

	<main class="mx-auto max-w-6xl px-4 py-8">
		{@render children()}
	</main>
</div>
