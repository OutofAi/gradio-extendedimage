<script lang="ts">
	import { createEventDispatcher, tick } from "svelte";
	import { BlockLabel, IconButtonWrapper, IconButton } from "@gradio/atoms";
	import { Clear, Image as ImageIcon } from "@gradio/icons";
	import o169 from "./o169.svelte";
	import o916 from "./o916.svelte";
	import o11 from "./o11.svelte";
	import { FullscreenButton } from "@gradio/atoms";
	import {
		type SelectData,
		type I18nFormatter,
		type ValueData
	} from "@gradio/utils";
	import { get_coordinates_of_clicked_image } from "./utils";
	import Webcam from "./Webcam.svelte";

	import { Upload } from "@gradio/upload";
	import { FileData, type Client } from "@gradio/client";
	import SelectSource from "./SelectSource.svelte";
	import Image from "./Image.svelte";
	import type { Base64File, WebcamOptions } from "./types";

	export let value: null | FileData | Base64File = null;
	export let label: string | undefined = undefined;
	export let show_label: boolean;

	type source_type = "upload" | "webcam" | "clipboard" | "microphone" | null;

	export let sources: source_type[] = ["upload", "clipboard", "webcam"];
	export let streaming = false;
	export let pending = false;
	export let webcam_options: WebcamOptions;
	export let selectable = false;
	export let root: string;
	export let i18n: I18nFormatter;
	export let max_file_size: number | null = null;
	export let upload: Client["upload"];
	export let stream_handler: Client["stream"];
	export let stream_every: number;

	export let modify_stream: (state: "open" | "closed" | "waiting") => void;
	export let set_time_limit: (arg0: number) => void;
	export let show_fullscreen_button = true;

	let upload_input: Upload;
	export let uploading = false;
	export let active_source: source_type = null;
	export let fullscreen = false;


	type Orientation = "9:16" | "1:1" | "16:9";
	export let orientation: Orientation = "9:16";


	export async function handleOrientation(next: Orientation): Promise<void> {
		// call this on EVERY click (even if already selected)
		orientation = next;
		await tick(); // keep if any layout depends on it
		dispatch("orientation", { value: next }); // let parent know
	}

	async function handle_upload({
		detail
	}: CustomEvent<FileData>): Promise<void> {
		if (!streaming) {
			if (detail.path?.toLowerCase().endsWith(".svg") && detail.url) {
				const response = await fetch(detail.url);
				const svgContent = await response.text();
				value = {
					...detail,
					url: `data:image/svg+xml,${encodeURIComponent(svgContent)}`
				};
			} else {
				value = detail;
			}

			await tick();
			dispatch("upload");
		}
	}

	function handle_clear(): void {
		value = null;
		dispatch("clear");
		dispatch("change", null);
	}

	async function handle_save(
		img_blob: Blob | any,
		event: "change" | "stream" | "upload"
	): Promise<void> {
		if (event === "stream") {
			dispatch("stream", {
				value: { url: img_blob } as Base64File,
				is_value_data: true
			});
			return;
		}
		pending = true;
		const f = await upload_input.load_files([
			new File([img_blob], `image/${streaming ? "jpeg" : "png"}`)
		]);

		if (event === "change" || event === "upload") {
			value = f?.[0] || null;
			await tick();
			dispatch("change");
		}
		pending = false;
	}

	$: active_streaming = streaming && active_source === "webcam";
	$: if (uploading && !active_streaming) value = null;

	const dispatch = createEventDispatcher<{
		change?: never;
		stream: ValueData;
		clear?: never;
		drag: boolean;
		upload?: never;
		select: SelectData;
		end_stream: never;
		orientation: { value: Orientation };
		stroke: { points: [number, number][]; done: boolean };
	}>();

	let isDrawing = false;
	let points: [number, number][] = [];
	let frameEl: HTMLDivElement | null = null;

	function getPointFromEvent(e: PointerEvent): [number, number] | null {
	// Find the actual <img> rendered by <Image />
	const img = frameEl?.querySelector("img") as HTMLImageElement | null;
	if (!img) return null;

	const rect = img.getBoundingClientRect();
	const x = e.clientX - rect.left;
	const y = e.clientY - rect.top;

	// outside image bounds
	if (x < 0 || y < 0 || x > rect.width || y > rect.height) return null;

	// Convert to image pixel coordinates (natural size)
	const xn = x / rect.width;
	const yn = y / rect.height;

	const px = Math.round(xn * img.naturalWidth);
	const py = Math.round(yn * img.naturalHeight);

	return [px, py];
	}

	let moved = false;

	function onImgDragStart(e: DragEvent) {
		e.preventDefault();
	}

	function onPointerDown(e: PointerEvent) {
	if (!selectable) return;
	// only left-click / primary touch
	if (e.pointerType === "mouse" && e.button !== 0) return;

	const p = getPointFromEvent(e);
	if (!p) return;

	isDrawing = true;
	points = [p];
	drawOverlay();

	// keep receiving move/up even if pointer leaves element
	(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);

	// optional: prevent text selection / drag ghosting
	e.preventDefault();
	moved = false;
	}

	const MIN_DIST_PX = 2;

	function onPointerMove(e: PointerEvent) {
	if (!isDrawing) return;
	moved = true;

	const p = getPointFromEvent(e);
	if (!p) return;

	const last = points[points.length - 1];
	if (last[0] === p[0] && last[1] === p[1]) return;

	const dx = p[0] - last[0];
	const dy = p[1] - last[1];
	if (dx*dx + dy*dy < MIN_DIST_PX*MIN_DIST_PX) return;

	points = [...points, p];

	// ✅ live draw
	drawOverlay();
	}


	let overlayCanvas: HTMLCanvasElement | null = null;

	function drawOverlay() {
	const canvas = overlayCanvas;
	const img = frameEl?.querySelector("img") as HTMLImageElement | null;
	if (!canvas || !img) return;

	const ctx = canvas.getContext("2d");
	if (!ctx) return;

	const rect = img.getBoundingClientRect();
	const dpr = window.devicePixelRatio || 1;

	// Match canvas to displayed image size (crisp)
	canvas.style.width = `${rect.width}px`;
	canvas.style.height = `${rect.height}px`;
	canvas.width = Math.round(rect.width * dpr);
	canvas.height = Math.round(rect.height * dpr);

	ctx.setTransform(dpr, 0, 0, dpr, 0, 0); // draw in CSS pixels
	ctx.clearRect(0, 0, rect.width, rect.height);

	if (points.length < 2) return;

	// Convert image-pixel points -> displayed-pixel points
	const nw = img.naturalWidth || 1;
	const nh = img.naturalHeight || 1;

	ctx.lineWidth = 6;  
	ctx.lineJoin = "round";
	ctx.lineCap = "round";
	ctx.strokeStyle = "rgba(0, 120, 255, 0.5)"; 

	ctx.beginPath();
	for (let i = 0; i < points.length; i++) {
		const [px, py] = points[i];
		const x = (px / nw) * rect.width;
		const y = (py / nh) * rect.height;
		if (i === 0) ctx.moveTo(x, y);
		else ctx.lineTo(x, y);
	}
	ctx.stroke();
	}


	function endStroke(e: PointerEvent) {
	if (!isDrawing) return;
	isDrawing = false;

	// final emit
	drawOverlay(); // final paint
	dispatch("stroke", { points, done: true });
	}

	function clearOverlay() {
	const canvas = overlayCanvas;
	if (!canvas) return;
	const ctx = canvas.getContext("2d");
	if (!ctx) return;
	ctx.clearRect(0, 0, canvas.width, canvas.height);
	}


	export let dragging = false;

	$: dispatch("drag", dragging);

	function handle_click(evt: MouseEvent): void {
		if (moved) return; 
		let coordinates = get_coordinates_of_clicked_image(evt);
		if (coordinates) dispatch("select", { index: coordinates, value: null });
	}
	
	$: if (!active_source && sources) {
		active_source = sources[0];
	}

	async function handle_select_source(
		source: (typeof sources)[number]
	): Promise<void> {
		switch (source) {
			case "clipboard":
				upload_input.paste_clipboard();
				break;
			default:
				break;
		}
	}

	let image_container: HTMLElement;

	function on_drag_over(evt: DragEvent): void {
		evt.preventDefault();
		evt.stopPropagation();
		if (evt.dataTransfer) {
			evt.dataTransfer.dropEffect = "copy";
		}

		dragging = true;
	}

	async function on_drop(evt: DragEvent): Promise<void> {
		evt.preventDefault();
		evt.stopPropagation();
		dragging = false;

		if (value) {
			handle_clear();
			await tick();
		}

		active_source = "upload";
		await tick();
		upload_input.load_files_from_drop(evt);
	}
</script>

<BlockLabel {show_label} Icon={ImageIcon} label={label || "Image"} />

<div data-testid="image" class="image-container" bind:this={image_container}>
	<IconButtonWrapper>
		{#if value?.url && !active_streaming}
		
			{#if show_fullscreen_button}
				<FullscreenButton {fullscreen} on:fullscreen />
			{/if}

			<IconButton
				Icon={Clear}
				label="Remove Image"
				on:click={(event) => {
					value = null;
					dispatch("clear");
					event.stopPropagation();
				}}
			/>


		{/if}
	</IconButtonWrapper>
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="upload-container"
		class:reduced-height={sources.length > 1}
		style:width={value ? "auto" : "100%"}
		on:dragover={on_drag_over}
		on:drop={on_drop}
	>
		<Upload
			hidden={value !== null || active_source === "webcam"}
			bind:this={upload_input}
			bind:uploading
			bind:dragging
			filetype={active_source === "clipboard" ? "clipboard" : "image/*"}
			on:load={handle_upload}
			on:error
			{root}
			{max_file_size}
			disable_click={!sources.includes("upload") || value !== null}
			{upload}
			{stream_handler}
			aria_label={i18n("image.drop_to_upload")}
		>
			{#if value === null}
				<slot />
			{/if}
		</Upload>
		{#if active_source === "webcam" && (streaming || (!streaming && !value))}
			<Webcam
				{root}
				{value}
				on:capture={(e) => handle_save(e.detail, "change")}
				on:stream={(e) => handle_save(e.detail, "stream")}
				on:error
				on:drag
				on:upload={(e) => handle_save(e.detail, "upload")}
				on:close_stream
				mirror_webcam={webcam_options.mirror}
				{stream_every}
				{streaming}
				mode="image"
				include_audio={false}
				{i18n}
				{upload}
				bind:modify_stream
				bind:set_time_limit
				webcam_constraints={webcam_options.constraints}
			/>
		{:else if value !== null && !streaming}
			<!-- svelte-ignore a11y-click-events-have-key-events-->
			<!-- svelte-ignore a11y-no-static-element-interactions-->
			<div
				bind:this={frameEl}
				class:selectable
				class="image-frame"
				on:dragstart|preventDefault={onImgDragStart}
				on:pointerdown={onPointerDown}
				on:pointermove={onPointerMove}
				on:pointerup={endStroke}
				on:pointercancel={endStroke}
				on:click={handle_click}
				>
				<Image src={value.url} alt={value.alt_text} />
				<canvas bind:this={overlayCanvas} class="stroke-overlay"></canvas>
			</div>

		{/if}
	</div>
	<div class="bottom-row">

	<IconButtonWrapper top_panel={""}>
		{#if value?.url && !active_streaming}

			<div>
			<IconButton Icon={o916} label="9:16" on:click={() => handleOrientation("9:16")} />
			</div>

			<div>
			<IconButton Icon={o11} label="1:1" on:click={() => handleOrientation("1:1")} />
			</div>

			<div>
			<IconButton Icon={o169} label="16:9" on:click={() => handleOrientation("16:9")} />
			</div>

			
		{/if}
	</IconButtonWrapper>
	</div>

	{#if sources.length > 1 || sources.includes("clipboard")}
		
		<SelectSource
			{sources}
			{value}
			bind:active_source
			{handle_clear}
			handle_select={handle_select_source}
		/>
	{/if}

</div>

<style>
	/* make the bottom row an overlay that doesn't affect layout */
	.bottom-row {
		position: absolute;          /* ✨ float it */
		left: 5px;
		bottom: 45px;
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);

		padding: var(--spacing-xxs);
		border-bottom: none;
		border-left: none;
		border-radius: var(--block-label-radius);

		z-index: var(--layer-3);
		
	}
	
	:global(.bottom-row .is-selected div) {
	color: var(--color-accent);
	background: transparent;
	box-shadow: none;
	border-color: transparent;
	transition: color .15s ease;
	}



	.image-frame :global(img) {
	width: var(--size-full);
	height: var(--size-full);
	object-fit: scale-down;

	-webkit-user-drag: none; /* ✅ stops ghost drag on Safari/Chrome */
	user-select: none;       /* ✅ stops selection */
	touch-action: none;      /* ✅ makes pointer events behave on touch */
	}

	.upload-container {
		display: flex;
		align-items: center;
		justify-content: center;

		height: 100%;
		flex-shrink: 1;
		max-height: 100%;
	}

	.reduced-height {
		height: calc(100% - var(--size-10));
	}

	.image-container {
		display: flex;
		height: 100%;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		max-height: 100%;
	}

	.selectable {
		cursor: crosshair;
	}

	.image-frame {
	position: relative; /* ✅ needed for overlay positioning */
	object-fit: cover;
	width: 100%;
	height: 100%;
	}

	.stroke-overlay {
	position: absolute;
	inset: 0;
	pointer-events: none; /* ✅ don’t block pointer events */
	}
</style>
