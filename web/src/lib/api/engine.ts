/**
 * Typed engine API client.
 * ALL fetch calls to the ResumeForge engine go through this module.
 * Engine base URL is read from the VITE_ENGINE_URL env var.
 */

import type {
	BuildRequest,
	BuildResponse,
	BuildStreamEvent,
	AnalysisReport,
	JobDescription,
	Meta,
	SectionData,
	TemplateInfo
} from './types';

// ── Base URL ───────────────────────────────────────────────────────────────

function getBaseUrl(): string {
	// In browser context, VITE_ env vars are statically replaced at build time
	return (
		(typeof import.meta !== 'undefined' && (import.meta as unknown as { env: Record<string, string> }).env
			? ((import.meta as unknown as { env: Record<string, string> }).env.VITE_ENGINE_URL ?? '')
			: '') || 'http://localhost:8080'
	);
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
	const url = `${getBaseUrl()}${path}`;
	const res = await fetch(url, {
		headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
		...init
	});
	if (!res.ok) {
		const text = await res.text().catch(() => res.statusText);
		throw new Error(`Engine API error ${res.status}: ${text}`);
	}
	return res.json() as Promise<T>;
}

// ── Build ──────────────────────────────────────────────────────────────────

export async function build(req: BuildRequest): Promise<BuildResponse> {
	return apiFetch<BuildResponse>('/api/build', {
		method: 'POST',
		body: JSON.stringify(req)
	});
}

/**
 * Stream build progress events via SSE.
 * Yields BuildStreamEvent objects until the stream closes or an error occurs.
 */
export async function* streamBuild(req: BuildRequest): AsyncIterable<BuildStreamEvent> {
	const url = `${getBaseUrl()}/api/build/stream?${new URLSearchParams(
		Object.fromEntries(
			Object.entries(req)
				.filter(([, v]) => v !== undefined && v !== null)
				.map(([k, v]) => [k, String(v)])
		)
	).toString()}`;

	const res = await fetch(url, {
		headers: { Accept: 'text/event-stream' }
	});

	if (!res.ok || !res.body) {
		throw new Error(`SSE connection failed: ${res.status}`);
	}

	const reader = res.body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });
			const lines = buffer.split('\n');
			buffer = lines.pop() ?? '';

			for (const line of lines) {
				if (line.startsWith('data: ')) {
					const data = line.slice(6).trim();
					if (data && data !== '[DONE]') {
						try {
							yield JSON.parse(data) as BuildStreamEvent;
						} catch {
							// skip malformed events
						}
					}
				}
			}
		}
	} finally {
		reader.releaseLock();
	}
}

// ── Analysis ───────────────────────────────────────────────────────────────

export async function analyze(job_slug?: string): Promise<AnalysisReport> {
	return apiFetch<AnalysisReport>('/api/analyze', {
		method: 'POST',
		body: JSON.stringify({ job_slug })
	});
}

export async function getAnalysis(job_slug: string): Promise<AnalysisReport> {
	return apiFetch<AnalysisReport>(`/api/analyze/${encodeURIComponent(job_slug)}`);
}

// ── Data sections ──────────────────────────────────────────────────────────

export async function getSection(section: string): Promise<SectionData> {
	return apiFetch<SectionData>(`/api/data/${encodeURIComponent(section)}`);
}

export async function putSection(section: string, data: SectionData): Promise<SectionData> {
	return apiFetch<SectionData>(`/api/data/${encodeURIComponent(section)}`, {
		method: 'PUT',
		body: JSON.stringify(data)
	});
}

export async function importData(file: File): Promise<{ status: string }> {
	const form = new FormData();
	form.append('file', file);
	const url = `${getBaseUrl()}/api/data/import`;
	const res = await fetch(url, { method: 'POST', body: form });
	if (!res.ok) throw new Error(`Import failed: ${res.status}`);
	return res.json();
}

export function exportDataUrl(): string {
	return `${getBaseUrl()}/api/data/export`;
}

// ── Templates ──────────────────────────────────────────────────────────────

export async function listTemplates(): Promise<TemplateInfo[]> {
	return apiFetch<TemplateInfo[]>('/api/templates');
}

export function templatePreviewUrl(name: string): string {
	return `${getBaseUrl()}/api/templates/${encodeURIComponent(name)}/preview`;
}

// ── Jobs ───────────────────────────────────────────────────────────────────

export async function listJobs(): Promise<JobDescription[]> {
	return apiFetch<JobDescription[]>('/api/jobs');
}

export async function createJob(job: Omit<JobDescription, 'slug'> & { slug?: string }): Promise<JobDescription> {
	return apiFetch<JobDescription>('/api/jobs', {
		method: 'POST',
		body: JSON.stringify(job)
	});
}

export async function getJob(slug: string): Promise<JobDescription> {
	return apiFetch<JobDescription>(`/api/jobs/${encodeURIComponent(slug)}`);
}

export async function deleteJob(slug: string): Promise<void> {
	const url = `${getBaseUrl()}/api/jobs/${encodeURIComponent(slug)}`;
	const res = await fetch(url, { method: 'DELETE' });
	if (!res.ok) throw new Error(`Delete job failed: ${res.status}`);
}

// ── Config ─────────────────────────────────────────────────────────────────

export async function getConfig(): Promise<Meta> {
	return apiFetch<Meta>('/api/config');
}

export async function patchConfig(patch: Partial<Meta>): Promise<Meta> {
	return apiFetch<Meta>('/api/config', {
		method: 'PATCH',
		body: JSON.stringify(patch)
	});
}
