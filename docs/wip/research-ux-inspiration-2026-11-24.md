# UX inspiration research for the scene and the explanations

Date: 2026-11-24. Method: web search and page fetches run on 2026-11-24, outside photogrammetry software on purpose, harvesting interaction concepts from current products and explanatory work. Every fetched page was summarised by a small model before it reached the author, so a [V] claim is accurate to that summary and not to the page's exact wording; a claim that needs exact wording needs a second read before it enters a UX spec. Frame and scene follow the "Two registers in one interface" paragraph of the [brief](../concept/RC-brief.md) §2 and the eight ideas in [visual ideas](visual-ideas.md).

Legend:

- [V] read on a primary page today; the URL follows the claim. Vendor documentation, vendor blogs and the author's own site count as primary. Trade press that reports on a vendor is marked "(trade press)".
- [U] from memory, from a search-result snippet, or from a page that failed to load. Unconfirmed; treat as a lead, not a fact. A snippet URL is given where one exists.

Idea numbers #1 to #8 refer to the table in [visual ideas](visual-ideas.md). "NEW" refers to the list in the section "New ideas" below.

## 1. Autodesk and the generative 3D wave

**Flow Studio 3D Editor and Canvas.** Flow Studio splits generative work into two surfaces. The Canvas is a node-based 2D workspace for image and video generation and refinement; the 3D Editor is a spatial surface where characters, environments, camera tracks and motion capture are assembled "before generation occurs", with blocking, composition and camera movement set by hand rather than by prompt. [V] https://digitalproduction.com/2026/08/04/autodesk-flow-studio-adds-3d-editor-and-canvas/ (trade press). The pattern: direct the scene spatially first, then let the model render it. The delight is control without a text box; the person points, the machine fills in.

Recce mapping: the same inversion applies to capture planning. A ghost camera (#3) is placed in 3D by hand or by an agent, and the engine then judges the plan. The Canvas-versus-3D-Editor split also maps to Recce's two registers: a node-like run view in the frame, the spatial scene in the viewport.

**Neural Layer and AI Rigging.** AI Rigging places skeletal joints on a generated character "in a few clicks" and previews the rig in the app before export to Maya, Blender or Unreal; Neural Layer refines materials and lighting inside a Live Action project without a traditional render pipeline, priced at 15 credits per second of footage. [V] https://blogs.autodesk.com/media-and-entertainment/2026/04/28/introducing-ai-rigging-and-neural-layer-in-autodesk-flow-studio/ . The pattern that transfers is the visible cost per unit of output: the price is stated next to the action. Recce runs on the owner's hardware, so the equivalent is a stated time and energy estimate on a recipe before it runs.

**Wonder 3D, text and image to 3D.** Flow Studio adds a generative model for text to 3D and image to 3D, available at all subscription levels. [U] search snippet, https://adsknews.autodesk.com/en/news/autodesk-flow-studio-launches-wonder-3d-gen-ai-model-to-help-creators-make-3d-characters-and-objects-faster-and-easier/ . Relevance to Recce is indirect: a generated model has no coverage or uncertainty, a reconstruction has both, and that is the product difference to make visible.

**Neural CAD and Project Bernini.** Autodesk describes foundation models trained on CAD data, shown first as Project Bernini in May 2024, aimed at Fusion and Forma, where "you will watch the neural CAD engine reason through your request". [U] search snippet, https://www.autodesk.com/design-make/articles/neural-cad (the page returned HTTP 403 to the fetch). The claim to test later is the UX phrase "watch it reason": the reasoning is shown as an event stream the person can follow, which is the shape of idea #5.

**Forma analysis layers.** Forma runs sun, wind, noise, microclimate and embodied-carbon analyses on a massing model and re-evaluates within seconds of an edit, using ML predictors for the rapid versions. [U] search snippet, https://illustrarch.com/articles/design-softwares/73363-autodesk-forma-review.html (the vendor page returned HTTP 403). The concept is an analysis painted onto the model that updates live while the person moves geometry. In Recce the analysis is coverage and uncertainty; the live-edit equivalent is dragging a ghost camera and watching the surrounding surface relight (#3, #4) from a cheap predictor, with the exact recomputation following later.

**Maya, 3ds Max, Fusion recent UX.** A search returned a trade-press headline that Autodesk released major updates across Maya, 3ds Max, Flow Studio and Arnold. [U] https://awn.com/print/news/autodesk-releases-major-updates-across-maya-3ds-max-flow-studio-and-arnold . The article was not read. The Autodesk University 2026 announcements page returned HTTP 403, so no AU 2026 claim is made here.

## 2. Creative 3D tools winning new users

**Blender 5.0 (released 2025-11-18).** The release notes list: "Full Screen Area" renamed "Focus Mode"; more than 300 theme settings removed and the rest unified, including a shared playhead appearance across editors; group nodes show a stack indicator and open on double-click, with clickable breadcrumbs to navigate back out; a Swap Node operator (Shift+S) replaces a node type and keeps its connections; a "Reduce Motion" option; tree views gain multi-select, F2 rename and name search; animation editors share unified footer playback controls. [V] https://developer.blender.org/docs/release_notes/5.0/user_interface/ and https://developer.blender.org/docs/release_notes/5.0/ . Three transferable patterns: breadcrumbed drill-in for nested structure (a run contains stages, a stage contains steps), swap-in-place for a strategy that keeps its connections (COLMAP to GLOMAP with the inputs and outputs preserved, matching #6), and a Reduce Motion switch that Recce needs because idea #1 is animation-heavy.

**Spline.** A browser 3D tool with real-time multi-user editing, states and events for interaction, and publishing the same scene to web, iOS (SwiftUI) and Android. It exposes an MCP server so Claude, ChatGPT or Cursor agents can read the scene, write changes and frame views, and the person keeps editing the same file without a re-import. [V] https://spline.design/ . This is the closest existing example of Recce's agent face working on the visible scene: the agent edits what the person sees, in place. Mapping: an agent debrief (#5) that moves the camera to frame its evidence and drops annotations into the scene the person can then move or delete.

**Womp.** Browser modelling built on SDF/CSG "Liquid 3D" shapes that blend and merge, with iridescent and holographic material finishes, and an ordering path to physical prints. [V] https://womp.com/ . The concept is soft blending as the default response to input: shapes melt together instead of intersecting with hard edges. For Recce this suggests uncertainty drawn as a soft field that merges between neighbouring cameras (#4) rather than a patchwork of per-point colours.

**Plasticity.** Direct editing with no history tree, curvature-continuous fillets and surface blends. [V] https://www.plasticity.xyz/ . The recorded concept is direct manipulation with immediate geometric feedback. The feel (not the CAD content) is the reference for dragging a ghost camera.

**Shapr3D.** One interface across Windows, Mac, iPad, iPhone and Apple Vision Pro, Apple Pencil and SpaceMouse input, review links that open in a browser, and a claim that most users build a first model within 15 minutes. [V] https://www.shapr3d.com/ . The pattern is the browser review link: a reviewer needs no install. Recce's web UI is that by construction, so a shareable read-only link to a presentation scene (#7) is the matching feature.

**Nomad Sculpt.** The fetched page covered licensing only (activation per computer, a 15-day offline grace). [V] https://nomadsculpt.com/ . No UX claim about its gesture model is made from a read page. [U] From memory, Nomad's strength is a dense tool set made usable on a phone by large touch targets and a bottom tool shelf; unconfirmed.

**Houdini.** SideFX describes every action as a node, with nodes wired into networks that "define a 'recipe' that can be tweaked to explore different creative paths". [V] https://www.sidefx.com/products/houdini/ . The word is the same one Recce uses. Mapping: a Recce recipe is a node network whose comparison view (#6) highlights which node's parameter differs, rather than diffing two flat settings lists. [U] From memory, Houdini's geometry spreadsheet shows per-point attributes at any node and the viewport shows the network's state at the selected node; if confirmed, it is the model for "inspect the reconstruction as it stood after this stage".

**Godot 4.5.** Adds screen-reader support through AccessKit for the Project Manager, standard UI nodes and the inspector, translation preview in the editor viewport, colour swatches beside colour values in scripts, multi-node selection while debugging a running game, and editor language switching without restart. [V] https://godotengine.org/releases/4.5/ . The transferable idea is inline preview of a value where it is written: a swatch next to a colour. In Recce, a number in the inspector (overlap 0.7, focal length 24 mm) carries a small drawing beside it.

**Cinema 4D 2027.** Scatter (surface population), Liquid FX (foam, spray, bubbles) and Redshift speedups, plus viewport, node-editing and scene-management refinements. [V] https://www.maxon.net/en/cinema-4d . No UX concept beyond feature names was extracted. Unreal Engine 5.7 release notes returned HTTP 403, so nothing is claimed about the UE editor.

## 3. Colour, finishing and media

**DaVinci Resolve 21.** One application divided into page-sized workspaces (Photo, Cut, Edit, Color, Fusion, Fairlight, Deliver) switched with one click, with camera-original quality throughout; the Color page offers HDR colour wheels, curves, a node graph and Power Windows. [V] https://www.blackmagicdesign.com/products/davinciresolve . The concept is task pages: the same project, a different room per job. Recce's equivalent is a small set of rooms (Capture review, Registration, Coverage, Compare, Present, Debrief) over one run, each with its own tool set. [U] From memory, Resolve's still-store split-screen wipe compares a graded frame with a reference; it is the interaction behind #6.

**Final Cut Pro.** A magnetic timeline that keeps clips in sync while the editor experiments; Magnetic Mask separating people and objects without a green screen; Object Tracker; Visual Search and Transcript Search that find footage by what is in it or said in it. [V] https://www.apple.com/final-cut-pro/ . Two transfers: search by content (find "the photos that see the left hull" through the scene, not through file names) and tracking that attaches an annotation to a moving subject.

**Capture One.** Tethering with live view and focus assistance, custom workspaces and shortcuts, assisted masking, style matching. [V] https://www.captureone.com/en/features . Tethering is the pattern: a result appears on a large screen the moment the shutter fires. For Recce, a live capture session (a phone or a robot streaming photos) shows each frame registering into the model within seconds.

**Lightroom.** Release notes mention Assisted Culling with a Faces panel showing eye-sharpness and eyes-open scores per face, Adaptive Profiles, and a Color Variance slider. [U] search snippet, https://helpx.adobe.com/dk/lightroom/desktop/introduction/release-notes.html . The idea to keep is culling with a per-item score shown next to the thumbnail: each input photo carries a blur score, an overlap score and a "holds up N matches" count.

**Halide.** Mark III lists a 14-bit RAW waveform, colour zebras, focus peaking, a focus loupe and histograms, with a minimal-processing mode (Process Zero). [U] search snippet, https://lux.camera/halide-mark-iii/ (the vendor page returned HTTP 404 at a guessed path). The pattern is the measurement overlay: the image stays whole and the analysis lies over it as zebras and peaking, toggled by one control. Recce's coverage and confidence layers (#3, #4) take this form: overlays on the scene, one toggle each, never a separate chart.

**Darkroom.** Not fetched. [U] No claim is made.

## 4. iPhone and iPad capture apps

**Apple Object Capture guided capture (WWDC23 session 10191).** The session describes: automatic image selection by sharpness, clarity and exposure; a capture dial that shows which areas of the object have enough images and shows completion; real-time guidance on lighting (avoid dark places), movement speed (slow and smooth), distance (the object must fit in frame) and keeping the object in view; a state machine of initializing, ready, detecting, capturing, finishing, completed; a flip flow with advice on which objects to flip (rigid, texture-rich) and which not (deformable, symmetric or repetitive texture, textureless) and a recommended three passes; an ObjectCapturePointCloudView to review before processing; and a poses output giving camera position and orientation per image. [V] https://developer.apple.com/videos/play/wwdc2023/10191 . The delight of the dial is that coverage is a shape the person completes, a ring that fills, not a percentage. The point-cloud review before processing is the same instinct as #1 applied to capture.

Mapping to Recce: the dial is a template for a coverage glyph (#3) that works on a phone, on a robot operator's tablet and in the web UI. The flip advice is a model of a capture recommendation that names its reason ("symmetric texture: do not flip") instead of stating a rule.

**Polycam.** One app combining LiDAR, photogrammetry, Gaussian splat and non-LiDAR capture; real-time haptic and visual feedback during a walk-through; LiDAR meshes appear while scanning. [U] search snippet, https://poly.cam/blog/lidar-vs-photogrammetry-which-3d-scanning-method-is-right-for-you (the homepage host did not resolve). The pattern is haptic feedback as guidance: a buzz when coverage is thin. Whether Recce's capture companion exists is a scope question for the owner; the pattern is recorded here for that decision.

**Scaniverse.** Now delivered under Niantic Spatial's Capture platform: a web and mobile app, inputs from phones, 360 cameras, drones, LiDAR and robots, outputs SPZ (an open splat format), PLY, GLB and USDZ, private by default. [V] https://www.nianticspatial.com/products/capture . The page has no capture-UX detail.

**KIRI Engine.** Photo scan, LiDAR scan, 3D Gaussian splatting, a featureless-object mode for shiny or transparent items, quad meshes with PBR materials and AI auto-rigging. [V] https://www.kiriengine.app/ . The featureless-object mode is a named response to a known failure; Recce's failure explanations (#2, #4) name the failure the same way.

**Luma.** The fetched homepage now presents video-generation products (Ray 3.2, Uni-1, Luma Skills) and an Open Physical AI Lab. [V] https://lumalabs.ai/ . The page offers no capture-UX detail.

**RealityScan and Reality Composer.** Both fetches failed (HTTP 403 and 404). Nothing is claimed.

## 5. Craft in design and productivity tools

**Linear.** The 2024 redesign moved theme generation from HSL to LCH ("perceptually uniform", so a red and a yellow at lightness 50 look equally light) and cut 98 variables per theme to three: base colour, accent colour and contrast, with high-contrast variants. The work took about six weeks. [V] https://linear.app/now/how-we-redesigned-the-linear-ui . Two direct transfers. The frame's tokens should be generated from three inputs, which keeps the calm register consistent and gives a high-contrast theme at no cost. Every colour ramp in the scene (coverage, confidence) should be built in a perceptually uniform space so equal steps look equal; that is a correctness requirement for an honest uncertainty display, not decoration.

**Raycast.** A keyboard-first launcher with a command palette, more than 1,000 extensions and built-in AI chat. [V] https://www.raycast.com/ . Rerun, below, also ships a command palette. A palette lets Recce expose every action (go to stage, compare recipes, show gaps, narrate) without growing the chrome, and the same verb list is the MCP tool list: one vocabulary for people and agents.

**Figma.** The Figma blog's current themes: an agent now present in FigJam and Slides (the page dates the expansion to November 2026), code layers that put working prototypes on the canvas, 3D transforms combined with motion. [V] https://www.figma.com/blog/ . The pattern is the agent living where the work is, on the canvas, and its output remaining editable objects. [U] From memory, Figma's named multiplayer cursors and comment pins anchored to a spot on the canvas are the model for anchored notes on a 3D point.

**Arc and Dia.** Dia has an assistant in the address bar and sidebar that chats about open tabs, saved prompts called Skills, and a stated plan to bring Arc's sidebar back. [U] search snippet, https://techcrunch.com/2025/11/03/dias-ai-browser-starts-adding-arcs-greatest-hits-to-its-feature-set . The concept is the assistant that sees what the person sees. Recce's agent receives the current view, selection and time cursor as context.

**Things.** Not fetched. [U] No claim made.

**visionOS.** The HIG page lists windows, glass material, ornaments, depth, eye and hand input and comfort as the design elements. [V] https://developer.apple.com/design/human-interface-guidelines/designing-for-visionos (summary level only). Two ideas to carry from memory, both unconfirmed here: [U] glass lets the world show through the panel, so panels over a 3D scene could keep the scene legible behind them; [U] ornaments attach controls to the edge of an object instead of floating in a toolbar, which suggests per-object controls that sit beside the selected cluster.

## 6. Engineering and high-tech visualisation

**Rerun.** The viewer is built from a Blueprint panel (what is shown and how), a Selection panel (details and configuration of the selected item), a Timeline panel that "gives you controls over what point in time you're looking at on which timeline for the rest of the viewer", and a viewport of arrangeable Views. A command palette opens with Cmd/Ctrl+K, and views carry an info icon that reveals usage guidance on hover. [V] https://rerun.io/docs/reference/viewer/overview . Timelines are plural: log time by default, a log tick opt-in, and custom timelines added by the logger, holding only 64-bit integers (sequence, nanosecond timestamp, duration). Data logged as static belongs to every timeline, including ones not yet created, and takes precedence over temporal data. [V] https://rerun.io/docs/concepts/timelines . Recce maps this directly. A run has several timelines (photo order, capture time, registration order, iteration of bundle adjustment), and the person picks which one drives the scene. Camera intrinsics and the scale reference are static data valid at every time. The existing frame already follows robotics-lab's Rerun-like look; this research adds the plural timelines and the static layer as concrete mechanics.

**Foxglove.** "20+ panels on one synchronized timeline" including point clouds, camera feeds, transforms and plots; semantic search over image and video topics with text prompts; saved prompts that run as agents on webhooks or schedules. [V] https://foxglove.dev/ . Panel docs: drag and drop topics onto a panel for instant visualisation, a purple border for the selected panel, panel settings as importable JSON. [V] https://docs.foxglove.dev/docs/visualization/panels/introduction . Recce's mapping: scene, photo strip, match graph and residual plot share one time cursor, so scrubbing registration moves all four. Semantic search by prompt over the photo set ("photos that look at the stern") reuses the Final Cut search idea.

**Cesium.** Streams 3D Tiles (buildings, photogrammetry, point clouds), takes CZML and GeoJSON, offers first-class time-dynamic visualisation "for simulations, real-time telemetry, and 4D", and switches among 3D, 2D and 2.5D Columbus views. [V] https://cesium.com/platform/cesiumjs/ . Photogrammetry arrives as 3D Tiles, so Recce's export is a Cesium input; the concept to take is time-dynamic as a first-class dimension, which a run replay (#1) is.

**NASA Eyes.** Browser apps for the solar system (time controls over 1950 to 2050 with fast-forward and rewind, 150 missions), asteroids (30,000 near-Earth objects), Earth (carbon dioxide, ozone, sea level), exoplanets (5,500 systems), DSN Now (real-time spacecraft links), and Mars 2020 EDL (a landing simulation). [V] https://science.nasa.gov/eyes/ . The concept is real data wrapped in a play-and-scrub frame with a time range the person can see the edges of. The EDL app is a replay of a single critical event, the model for a "replay the moment registration broke" shortcut.

**NVIDIA Omniverse.** Modular libraries on OpenUSD, SimReady validation that checks an asset against simulation requirements before use, RTX sensor output (camera, lidar, radar), freely available for development and production as of May 2026. [V] https://www.nvidia.com/en-us/omniverse/ . SimReady is the pattern for a readiness check: an asset passes or fails named requirements before it enters a downstream use. Recce's quality report for a robotics or survey consumer is the same shape: "scale known, frame known, coverage at least X, ready for use Y".

**Flightradar24, Google Earth, Tesla, F1 telemetry, Palantir, robotics fleet UIs.** The Flightradar24 blog and the Palantir Gotham page returned nothing usable (HTTP 403 and an empty summary), the F1 fetch redirected to the homepage, and Google Earth, Tesla and fleet UIs were not fetched. Everything below is [U], from memory. [U] Flightradar24 pairs a live map with a playback slider and a trail behind each aircraft, so recent history is drawn as a fading line; the matching Recce idea is a fading trail behind each camera showing where it was before bundle adjustment moved it. [U] F1 broadcast graphics pair a speed trace with a position on the track map, and call out one number against a reference lap; the matching idea is a delta against a reference recipe, drawn on the scene. [U] Tesla's in-car view renders only what the sensors believe is there, including ghosted objects when confidence is low; this is the direct precedent for #4. [U] Situational displays in the Palantir style centre an object-and-link graph with a map and a timeline; the matching idea is the match graph (#2) as a linked panel next to the scene.

## 7. Explanatory and interactive work

**Bartosz Ciechanowski.** The most recent article on his index is "Moon" (17 December 2024), built from draggable 3D simulators where the reader moves bodies and changes velocities, time-scrubbing sliders, camera controls that lock on a body or orbit freely, parameter sliders for mass, distance and eccentricity, side-by-side space and surface views, and an observer figurine the reader places anywhere on Earth. [V] https://ciechanow.ski/ . The index may be dated; newer articles may exist that the fetch did not show. The concepts to take: each diagram has one or two controls, the same object is shown from two viewpoints at once, and the reader's finger is the instrument. Recce mapping: a "why triangulation needs a baseline" explainer where the reader drags two camera icons apart and the uncertainty ellipsoid of a point shrinks; a second view shows the same point from above. Each such mini-lab lives next to the term it explains in the inspector.

**Distill.** The momentum article uses sliders for step size and momentum with live phase diagrams, an error decomposition per eigenvalue animated as parameters change, and side-by-side loss curves of two methods. [V] https://distill.pub/2017/momentum/ . Distill ran from 2016 to 2021 and is on an indefinite hiatus; its stated belief is that "reactive diagrams allow for a type of communication not possible in static mediums". [V] https://distill.pub/about/ . The pattern for #6: two curves from two recipes on shared axes with the parameter that separates them under the reader's hand.

**Bret Victor, Learnable Programming.** Principles stated on the page: show the data; make meaning transparent (labels on hover, annotations connecting code to output); visualise flow over time so the reader scrubs execution; eliminate hidden state or make it visible; create by reacting, starting from something visible and adjusting; move from concrete to abstract in small steps. [V] https://worrydream.com/LearnableProgramming/ . These six apply nearly line for line. Show the data: the match is a line, not a count. Hidden state: the intermediate pose estimate after each iteration is drawn, because the engine's belief at step k is the hidden state of a reconstruction. Scrub: #1. Concrete to abstract: the first explanation of coverage is one photo's frustum, then two, then the whole set.

**Nicky Case.** Explorable explanations including The Evolution of Trust and a tool for nested, expandable explanations (Nutshell), all under a public-domain waiver. [V] https://ncase.me/ . Nutshell's idea, an explanation that expands inline inside a sentence, fits a debrief (#5): a sentence says "twelve photos hold the left side" and the phrase opens to show them, with no navigation away.

**3Blue1Brown.** The newest lesson as of today is dated 17 November 2026 (compression and arithmetic coding). [V] https://www.3blue1brown.com/ . The page says nothing about method. [U] From memory, the lessons are built in the author's Manim library and rely on one persistent visual object transformed step by step; the lesson for Recce is object permanence, so the cloud on screen at step k is the same object as at step k-1, morphing, never cut.

**Observable and the Pudding (scrollytelling).** The Observable homepage returned HTTP 429 and the Pudding process page returned 404. [U] From memory, scrollytelling binds a sticky scene to scroll position so each paragraph triggers a camera move or a state change; it is the delivery form of #7 (a presentation is a scroll or a click path through camera positions) and of a shareable debrief page.

## 8. AI-native and multimodal UX

Evidence from this pass: Spline's MCP (agents read the scene, write changes, frame views, and the human keeps editing in the same file) [V] https://spline.design/ ; Figma's agent arriving in more canvases and producing editable layers [V] https://www.figma.com/blog/ ; Foxglove's semantic search and saved-prompt agents [V] https://foxglove.dev/ ; Flow Studio's 3D Editor, which puts a spatial step before generation [V] https://digitalproduction.com/2026/08/04/autodesk-flow-studio-adds-3d-editor-and-canvas/ (trade press); Dia's assistant that reads open tabs [U] https://techcrunch.com/2025/11/03/dias-ai-browser-starts-adding-arcs-greatest-hits-to-its-feature-set . No page fetched in this pass documents a product that shows an agent's evidence as clickable citations; that pattern comes from memory ([U]: search products that attach numbered sources to claims, and coding agents that show tool calls as a collapsible log). It is the central pattern for #5 and appears in the ranked table as an adopted rule, not a copied feature: every sentence in a debrief carries a handle to the photos, matches or numbers behind it, and activating the handle moves the camera there.

Rules distilled from the V items above for the agent face:

1. The agent edits the shared scene, not a copy (Spline).
2. Its output stays editable and deletable (Figma).
3. It receives the current selection and time cursor as context (Dia, [U]).
4. It states the cost of a step before it runs (Flow Studio credits, [V] Autodesk blog above).
5. It searches the photo set by meaning (Foxglove).

## Patterns worth stealing

Ranked by expected effect on the "wow" and the understanding, then by cost.

| Rank | Pattern | Source | What it does in Recce | Idea |
|---|---|---|---|---|
| 1 | One shared time cursor driving every panel, with plural timelines and a static layer | Rerun, Foxglove [V] | Scrubbing registration moves scene, photo strip, match graph and residual plot together; the person chooses photo order, capture time or iteration as the axis | #1, NEW 1 |
| 2 | Completion ring for coverage | Apple capture dial [V] | A ring or sphere glyph that fills as angles are covered; works on a phone, a tablet, the web UI | #3, NEW 5 |
| 3 | Every claim carries a clickable handle to its evidence | Agent UX pattern [U], Spline MCP [V] | A debrief sentence opens its photos and matches and flies the camera there | #5, NEW 2 |
| 4 | Show hidden state, scrub flow, concrete to abstract | Bret Victor [V] | The engine's pose belief after each iteration is drawn; explanations build from one frustum to the full set | #1, #2, NEW 3 |
| 5 | Reader-driven mini-lab beside a term | Ciechanowski, Distill [V] | Drag two cameras apart and watch a point's uncertainty ellipsoid shrink; one control, two viewpoints | #4, NEW 4 |
| 6 | Analysis as overlay with one toggle each | Halide zebras and peaking [U], Forma layers [U] | Coverage and confidence laid over the scene as toggleable overlays that never replace it | #3, #4 |
| 7 | Perceptually uniform colour ramps and a three-input theme | Linear [V] | Coverage and confidence ramps built in LCH, so equal data steps look equal; frame tokens from base, accent and contrast | #3, #4, NEW 6 |
| 8 | Recipe as a node network with swap-in-place | Houdini [V], Blender Swap Node [V] | Compare two recipes by the node whose parameter differs; swap a strategy and keep its connections | #6 |
| 9 | Command palette with one verb list for people and agents | Raycast, Rerun [V] | Cmd+K reaches every action; the same verbs form the MCP tool list | NEW 7 |
| 10 | Drill in with breadcrumbs, double-click to enter | Blender 5.0 [V] | Run, stage, step navigation without losing place | #1 |
| 11 | Soft blending as the default | Womp [V] | Uncertainty rendered as a field that merges between cameras, not a patchwork | #4 |
| 12 | Inline expandable explanation | Nutshell (Nicky Case) [V] | A phrase in the debrief opens in place to show the photos | #5 |
| 13 | Readiness check against named requirements | Omniverse SimReady [V] | The quality report states "ready for use Y" with the requirements it checked | NEW 8 |
| 14 | Browser review link, no install | Shapr3D [V] | A read-only link to a presentation scene | #7 |
| 15 | Reduce Motion switch | Blender 5.0 [V] | Required once #1 animates by default | #1 |
| 16 | Fading trail behind a moving object | Flightradar24 [U] | Camera positions before and after bundle adjustment as a fading trail | #1 |
| 17 | Compare as a wipe on one view | Resolve still store [U] | The split slider already in #6, with a reference lap style delta | #6 |
| 18 | Tethered live result | Capture One [V] | A streaming capture session registers each frame within seconds | NEW 9 |

## New ideas

These are suggestions beyond the eight in [visual ideas](visual-ideas.md), each a direction to mock, not a decision.

1. **Plural timelines.** The run has a timeline per axis (photo order, capture time, registration order, optimiser iteration), a picker chooses which drives the scene, and static facts (intrinsics, scale reference) belong to all of them. Source: Rerun [V].
2. **Evidence handles.** Each sentence and each number in a debrief or report has a handle. Activating it selects the underlying photos or matches in the scene and flies the camera. A sentence without a handle is flagged in the report as an unsupported claim. Source: agent pattern [U], Spline [V].
3. **The engine's belief at step k.** A scrubbable view of what the engine believed at each iteration, including poses it later discarded. Source: Bret Victor, hidden state [V].
4. **Mini-labs.** A short set of reader-driven demonstrations (baseline and triangulation, overlap and match count, blur and feature count, rolling shutter and straight lines, refraction and apparent focal length) embedded beside the term in the inspector, each with one or two controls. Source: Ciechanowski, Distill [V].
5. **A shared coverage glyph.** One ring or sphere glyph drawn identically in the web UI, a phone companion and an operator tablet, so a person who learned it on one surface reads it on the others. Source: Apple capture dial [V].
6. **Honest colour.** A rule that every ramp in the scene is perceptually uniform, with a colour-blind-safe variant and a luminance-only fallback, and a "what does this colour mean" legend that opens from any overlay. Source: Linear [V].
7. **One verb list.** A single registry of actions powers the command palette, the CLI subcommands, the HTTP routes and the MCP tools. Source: Raycast, Rerun [V]; the registry itself is a design inference, not copied.
8. **Readiness stamps.** The quality report ends with named downstream uses (survey, robot localisation, print, web viewing) and a pass, fail or unknown for each against stated requirements. Source: Omniverse SimReady [V].
9. **Live registration during capture.** For a streaming source, each arriving frame registers into the model in view; a frame that fails to register is shown as a ghost at its expected pose. Source: Capture One tethering [V], Apple point-cloud preview [V].
10. **The agent as a scene editor.** The agent places ghost cameras, labels and a camera path directly into the scene through MCP, and the person moves or deletes them. Source: Spline [V].
11. **Replay the moment.** One click replays the few iterations around the registration step with the largest residual jump. Source: NASA Eyes EDL replay [V], Flightradar24 playback [U].
12. **Frame the cost.** Every recipe shows a time and energy estimate before it runs and the measured figure after. Source: Flow Studio credits [V].

## Not covered

What the pass did not check, and why. Treat every item as an open lead.

Pages that failed or returned nothing usable:

- Autodesk University 2026 announcements (HTTP 403), the Autodesk neural CAD article (403), the Forma environmental-analysis page (403), the Revit Forma wind analysis page (not fetched). Forma, neural CAD and Bernini rest on search snippets only.
- Blender's own 5.0 release page (403) and the CG Channel Blender review (403); the Blender claims rest on the developer release notes only, which cover the UI and not the headline features.
- Unreal Engine 5.7 release notes (403): no UE editor claim of any kind. Unreal's Sequencer, MegaLights and editor mode changes are unchecked.
- RealityScan (403), Reality Composer (404), Apple's ObjectCaptureSession documentation page (it returned a title only) and the Apple Object Capture capture-guidance article (404).
- Polycam (host did not resolve): capture guidance rests on one snippet. Scaniverse's own capture UX (its page redirected to an enterprise product page with no UX detail). Luma's capture product (the page now shows video generation).
- Observable (HTTP 429), the Pudding (404), Palantir Gotham (empty summary), the F1 page (redirect, not followed), Flightradar24's blog (403), Halide's own page (404) and the Rerun blueprint page (404).

Arenas or items not attempted:

- Darkroom, Things, Tesla visualisation, Google Earth, robotics fleet UIs, the Houdini viewport and spreadsheet behaviour, Capture One layers and styles, Lightroom's before and after modes, Resolve scopes, Maya and 3ds Max UX changes, Fusion's UX, Shapr3D's Apple Pencil gestures, Nomad's gestures, Spline's AI generation, Arc's boosts, 3Blue1Brown's tooling (all from memory where mentioned, otherwise absent).
- Bartosz Ciechanowski's articles other than the index summary; the summary may predate newer articles. No Distill article beyond momentum.
- Whether any shipping product shows agent evidence as clickable citations inside a 3D scene. The nearest finding is Spline's MCP, which does not cite evidence.

Limits of method:

- Every [V] came through a model-generated summary of the fetched page, not a raw read. Counts, names and dates are likelier to be right than the nuance of a phrase. Trade-press items (Flow Studio 3D Editor) report on the vendor and are not the vendor's own words.
- No product was run, so every statement about delight is an inference from a description, not an observation of use. No video, motion or interaction was seen; patterns such as the capture dial and Rerun's timeline are known only as text.
- Nothing here was tested against Recce's data. RC-P6 is the place to test any of these on the ETH3D kicker scene; the mini-lab, evidence-handle and plural-timeline ideas need a mock before a UX spec.
- No claim was made about licensing. Several sources (Spline, Foxglove, Omniverse, Resolve) are proprietary; Rerun and Cesium are open source, and Recce takes concepts from all of them, not code.
- The search tool is US-only and reported results as of today; snippets can be stale.
