# Photogrammetry primer

This document is the standing reference for the theory behind the engine. It exists so that the operator, who knows light, lenses and water better than linear algebra, and the coding agents, who know linear algebra better than reefs, share one vocabulary and one set of reasons. Every section explains the intuition first, then the maths, then states what the idea forces on the design. When a design question comes up, such as why a model must say whether its scale is metric, why a flat port breaks the pinhole model or why a splat is not a measurement, the answer starts here. Where this primer and the code disagree, one of them is wrong and the disagreement gets fixed, not tolerated.

## Contents

1. [What photogrammetry is](#1-what-photogrammetry-is)
2. [The camera](#2-the-camera)
3. [Two-view geometry](#3-two-view-geometry)
4. [Features and matching](#4-features-and-matching)
5. [Structure from motion](#5-structure-from-motion)
6. [Bundle adjustment](#6-bundle-adjustment)
7. [Learned feed-forward reconstruction](#7-learned-feed-forward-reconstruction)
8. [Dense reconstruction](#8-dense-reconstruction)
9. [Surfaces and textures](#9-surfaces-and-textures)
10. [Radiance fields and gaussian splatting](#10-radiance-fields-and-gaussian-splatting)
11. [Capture](#11-capture)
12. [RAW and colour](#12-raw-and-colour)
13. [Underwater](#13-underwater)
14. [Frames, units and georeferencing](#14-frames-units-and-georeferencing)
15. [Measuring quality](#15-measuring-quality)
16. [Glossary](#16-glossary)
17. [Further reading](#17-further-reading)

---

## 1. What photogrammetry is

Photogrammetry recovers the shape of the world from photographs. A photograph throws away one dimension: every pixel records light that arrived along a ray, and nothing says how far along the ray the surface sat. A single image cannot give depth. Two images of the same point from different positions can, because the two rays cross at the point. Photogrammetry is the discipline of finding those crossings for millions of points at once, while also discovering where the cameras were and how their lenses bend light.

The difficulty is that nothing is known at the start. The camera positions are unknown, the point positions are unknown, and the only observations are pixel colours. The field's central trick is to solve everything together. If enough points are seen from enough views, the system of equations that ties points, cameras and pixel observations together has a unique answer, up to a small, well-understood ambiguity (section 6). The rest of the pipeline is engineering around that idea: finding which pixels in different photographs show the same point, solving for geometry robustly in the presence of wrong matches, then densifying and dressing the result.

### The pipeline at a glance

```text
 capture --> develop --> features --> matching --> SfM (poses + sparse points)
 (photos,    (RAW to     (keypoints,  (pairs,        |
  video,      matched     descriptors) verification) v
  poses)      images)                          bundle adjustment
                                                     |
                  +----------------------------------+
                  |                                  |
                  v                                  v
            dense MVS                        radiance-field branch
            (depth maps, fusion)             (NeRF, 3D gaussian splatting)
                  |                                  |
                  v                                  v
            surface (mesh)                       splat (.ply and kin)
                  |
                  v
            texture (UV, materials)
```

Each stage consumes the output of the one before and adds a kind of knowledge:

| Stage | Input | Output |
|---|---|---|
| Capture | The scene | Images, optionally poses, depth, GPS |
| Develop | RAW or camera JPEG | Consistent, linear-light-aware images |
| Features | Images | Keypoints with descriptors |
| Matching | Descriptors | Verified image pairs with point correspondences |
| SfM | Correspondences | Camera poses, intrinsics, sparse 3D points |
| Bundle adjustment | All of the above | Jointly refined poses and points |
| Dense MVS | Posed images | Per-view depth maps, a dense point cloud |
| Surface | Dense points or depth | Triangle mesh |
| Texture | Mesh and posed images | UV-mapped colour, materials |
| Radiance field | Posed images, sparse points | A model that renders novel views |

The radiance-field branch leaves the classical path after pose estimation. NeRF and 3D gaussian splatting do not build a surface; they fit a function or a cloud of translucent blobs so that rendering them from the known camera poses reproduces the photographs. They need the same poses the classical branch needs, which is why structure from motion stays at the centre of both.

### What this means for the engine

The pipeline is a directed graph of stages whose outputs are typed artefacts, and the reconstruction data model holds every one of them with its units, frame and producing step. Poses are the hinge: both branches consume them, so pose quality is the first thing the engine measures and reports. Stages are separable, which is what lets the coordinator place feature extraction on one machine and dense stereo on another.

---

## 2. The camera

### The pinhole model

A camera maps a 3D point to a 2D pixel. The simplest faithful model is the pinhole: all light passes through one point, the centre of projection, and lands on an image plane behind it. A point at $(X, Y, Z)$ in the camera frame, with $Z$ pointing forward along the optical axis, lands at

$$
x = f \frac{X}{Z}, \qquad y = f \frac{Y}{Z}
$$

on the image plane. The division by $Z$ is the whole story of perspective: distant things shrink, and a pixel fixes a direction but not a distance.

Two coordinate frames matter. The **world frame** is where the scene lives. The **camera frame** has its origin at the centre of projection, $Z$ forward, $X$ right, $Y$ down in the computer-vision convention. A rigid transform takes world points to camera points:

$$
\mathbf{X}_c = R\,\mathbf{X}_w + \mathbf{t}
$$

$R$ is a $3 \times 3$ rotation, $\mathbf{t}$ a translation. These are the **extrinsics**, written $[R \mid \mathbf{t}]$. They are a world-to-camera transform. The camera's centre in world coordinates is $\mathbf{C} = -R^\top \mathbf{t}$, and confusing $\mathbf{t}$ with $\mathbf{C}$ is a classic source of mirrored and displaced reconstructions. A pose handed to the engine by another system, a robot or ARKit, is often the opposite direction, camera-to-world, and the direction must be stated, never assumed.

### Intrinsics

The **intrinsic matrix** converts camera-frame rays to pixels:

$$
K = \begin{pmatrix} f_x & s & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{pmatrix},
\qquad
\lambda \begin{pmatrix} u \\ v \\ 1 \end{pmatrix} = K \,[R \mid \mathbf{t}] \begin{pmatrix} \mathbf{X}_w \\ 1 \end{pmatrix}
$$

$f_x, f_y$ are the focal length measured in **pixels**, $(c_x, c_y)$ is the principal point (where the optical axis meets the sensor, near the image centre but never exactly there), $s$ is skew (zero for any modern sensor), and $\lambda$ is the depth along the ray. Focal length in pixels, not millimetres, is what the geometry uses. Most pipelines set $f_x = f_y$ and fit one focal length.

The camera is therefore described by six extrinsic numbers per image and a handful of intrinsics per lens. Photos taken with the same lens at the same focal setting share intrinsics, which is a powerful constraint: it lets one set of intrinsics be estimated from hundreds of images. A zoom lens or a lens that focuses by changing its internal geometry breaks the sharing, because its effective focal length changes with focus and zoom.

### Initial focal length from EXIF

Optimisation needs a starting value, and EXIF supplies one. If the image is $W$ pixels wide and the sensor is $S_w$ millimetres wide, a lens of focal length $f_{mm}$ has

$$
f_{px} = f_{mm} \cdot \frac{W}{S_w}
$$

When the sensor width is unknown but the 35 mm-equivalent focal length $f_{35}$ is recorded, the same quantity follows from the 36 mm reference width: $f_{px} = f_{35} \cdot W / 36$ for the long side. The EXIF value is approximate: lenses breathe with focus, manufacturers round, and crops and in-camera processing change the effective sensor area. It is a prior to refine, not a measurement. Phones and action cameras often report a focal length after in-camera distortion correction, which means the image no longer follows the lens's raw geometry.

### Lens distortion

Real lenses bend straight lines. The standard correction works in normalised coordinates $(x, y) = (X/Z, Y/Z)$ with $r^2 = x^2 + y^2$. The **Brown–Conrady** model applies radial and tangential terms:

$$
\begin{aligned}
x_d &= x\,(1 + k_1 r^2 + k_2 r^4 + k_3 r^6) + 2 p_1 x y + p_2 (r^2 + 2x^2) \\
y_d &= y\,(1 + k_1 r^2 + k_2 r^4 + k_3 r^6) + p_1 (r^2 + 2y^2) + 2 p_2 x y
\end{aligned}
$$

The $k_i$ are radial coefficients (barrel and pincushion), the $p_i$ tangential coefficients (a lens element slightly off-axis). Pixels follow from $u = f_x x_d + c_x$, $v = f_y y_d + c_y$. The model is a polynomial in $r$, which behaves well up to moderate field angles and fails for very wide lenses, because the true relation between angle and image radius is not a polynomial in $\tan\theta$ and, at $\theta \to 90^\circ$, $\tan\theta$ diverges.

**Fisheye** models work with the angle $\theta$ between the ray and the optical axis instead. The ideal **equidistant** projection is $r = f\,\theta$: image radius grows linearly with angle, so a 180 degree field fits on a finite sensor. Real fisheye lenses deviate, and the **OpenCV fisheye** model, which follows the Kannala–Brandt form, adds a polynomial in $\theta$:

$$
r_d = f\,\theta_d, \qquad \theta_d = \theta\,(1 + k_1 \theta^2 + k_2 \theta^4 + k_3 \theta^6 + k_4 \theta^8)
$$

A GoPro in its wide modes is a fisheye in practice, and many of its "linear" modes are a software remap of a fisheye image. Using the wrong model leaves systematic residuals that the optimiser cannot absorb. Distortion parameters are estimated in the bundle adjustment, ideally from a set with strong geometry and a wide range of image positions for each feature, so that the edges of the frame are constrained.

### Rolling shutter

The pinhole model assumes the whole image is exposed in one instant. A **global shutter** does that. Most phones, action cameras and many mirrorless cameras in electronic-shutter mode use a **rolling shutter**, which exposes and reads rows one after another, so the top row and the bottom row see the world at times separated by roughly ten to thirty milliseconds, depending on the sensor. If the camera moves during that interval, each row has a slightly different pose, and the image is skewed, wobbled or bent: verticals lean in a pan, propellers bend.

For a still photo from a held phone the effect is small. For video it matters, because the camera is moving continuously by design and the frames are taken at speed. The geometry then holds only approximately: the rigid-camera model leaves residuals that grow with velocity, and a naive bundle adjustment either absorbs them as error or distorts the intrinsics to compensate. Mechanical shutters on DSLRs, such as the D850 in normal mode, are not subject to this in the same way. Electronic-shutter modes on mirrorless bodies, including the Alpha 1, read out row by row and carry the rolling-shutter effect to a degree that depends on sensor readout speed.

### What this means for the engine

Every camera in the model carries an explicit intrinsics record: the model name (pinhole, Brown–Conrady, OpenCV fisheye), the parameters, the image size, and whether those values are EXIF-derived guesses, calibrated or fixed. The pose direction (world-to-camera or camera-to-world) is a named field, never an implicit convention. GoPro input defaults to a fisheye model; a wrong default is a quality bug that looks like a registration failure. Rolling-shutter sources, which means every phone and every GoPro video, are flagged on ingest so that frame selection favours slow motion and the quality report can attribute residuals to it. Intrinsics sharing is a data-model concept: images are grouped by lens and focus state, and the engine does not silently share across a zoom.

---

## 3. Two-view geometry

### The epipolar constraint

Take two photographs of the same scene. A point seen in the first image lies somewhere along a ray. That ray, seen from the second camera, is a line in the second image: the **epipolar line**. The corresponding point in the second image must lie on it. This turns a 2D search for a match into a 1D search, and it supplies the test that rejects false matches.

All epipolar lines in an image pass through one point, the **epipole**, which is the image of the other camera's centre. The three-dimensional plane through both camera centres and the scene point is the **epipolar plane**.

### Essential and fundamental matrices

For calibrated cameras, with the pixel coordinates converted to normalised rays $\hat{\mathbf{x}} = K^{-1}\mathbf{x}$, the constraint is

$$
\hat{\mathbf{x}}'^{\top} E\, \hat{\mathbf{x}} = 0, \qquad E = [\mathbf{t}]_\times R
$$

$R$ and $\mathbf{t}$ are the relative rotation and translation between the two cameras, and $[\mathbf{t}]_\times$ is the skew-symmetric matrix of cross-product with $\mathbf{t}$. The **essential matrix** $E$ has five degrees of freedom: three for rotation, two for the direction of translation. The magnitude of the translation is absent. Two images cannot say how far apart the cameras were in metres, only in which direction, and this is the first appearance of the scale ambiguity.

With unknown intrinsics, the same constraint holds in pixels:

$$
\mathbf{x}'^{\top} F\, \mathbf{x} = 0, \qquad F = K'^{-\top} E\, K^{-1}
$$

The **fundamental matrix** $F$ has rank 2 and seven degrees of freedom. It can be estimated from point correspondences alone, with at least seven, or eight in the simple linear method, and the calibrated case needs five. Decomposing $E$ gives four candidate $(R, \mathbf{t})$ pairs, of which exactly one places the points in front of both cameras, the cheirality check.

### Homography and degeneracy

If the observed points all lie on a plane, or the camera only rotates without translating, the mapping between the two images is a **homography** $H$, a $3 \times 3$ matrix with eight degrees of freedom that maps points directly to points rather than to lines. For a plane with unit normal $\mathbf{n}$ at distance $d$ from the first camera,

$$
H = K' \left( R - \frac{\mathbf{t}\,\mathbf{n}^\top}{d} \right) K^{-1}
$$

This is a **degenerate case** for estimating $E$ and $F$. All points on a plane satisfy the epipolar constraint for a whole family of fundamental matrices, so $F$ is not determined. Pure rotation, with no baseline, is worse: the points carry no depth information at all, since any depth is consistent with the same image motion. Robust pipelines therefore fit both $H$ and $F$ or $E$ to each pair and use the score to classify the pair: planar or rotation-only pairs do not initialise a reconstruction. A flat floor, a wall, a tabletop and a handheld pan are the practical triggers.

### Triangulation and the baseline trade-off

Given two cameras and a matched pixel pair, the two rays meet at the 3D point, in principle. With noise they do not, so the point is chosen to minimise reprojection error or, as a quick initialisation, the linear DLT solution. How accurately depth comes out depends on the angle between the rays, the **parallax** angle. For a baseline $B$ between cameras, focal length $f$ in pixels and a matching error of $\sigma_d$ pixels, the depth uncertainty at distance $Z$ is approximately

$$
\sigma_Z \approx \frac{Z^2}{f\,B}\,\sigma_d
$$

Depth error grows with the square of distance and shrinks with baseline. A wide baseline gives accurate triangulation, but the views look different, so features are harder to match, occlusions grow and the overlap shrinks. A narrow baseline matches easily and triangulates badly. Capture is a balancing act between those two, which section 11 turns into numbers.

### What this means for the engine

The engine classifies every verified pair by the model that explains it (homography, essential, fundamental, or failed) and carries the triangulation angle as pair metadata. Initialisation of a reconstruction picks a pair with a wide enough angle and enough inliers, and refuses planar and rotation-only pairs. A scene dominated by a floor or a wall, a room scanned by turning on the spot, is a known weak case that the quality report names as such rather than reporting a mysterious failure. The per-point triangulation angle is stored, because depth confidence is a function of it.

---

## 4. Features and matching

### Keypoints and descriptors

To match photographs the engine needs to find points that can be recognised again from another angle. A **keypoint** is a location with local structure that stays identifiable under changes of viewpoint, scale and lighting: a corner, a blob, a texture patch. A **descriptor** is a vector summarising the patch around it, so that two descriptors close in the vector space show the same physical point.

**SIFT** is the classical workhorse: scale-space blob detection, orientation assignment and a 128-dimensional histogram-of-gradients descriptor. It is robust, well understood and slow-ish, and it remains the default in COLMAP. **Learned** detectors and descriptors, such as **SuperPoint** and **ALIKED**, are neural networks trained to produce repeatable keypoints and descriptors that match under harder conditions: wider baselines, lighting change, low texture. They are paired with learned matchers that reason about all the keypoints of two images at once. **Dense matchers** such as **RoMa** skip the sparse keypoint step and predict a correspondence for essentially every pixel with a confidence, which helps where sparse keypoints are scarce, at higher compute cost and with the need to select which matches to keep.

### Matching, the ratio test and verification

The simplest matcher takes each descriptor and finds its nearest neighbour in the other image. Nearest neighbours are often wrong, especially in repetitive texture. The **ratio test** compares the distance to the nearest neighbour with the distance to the second nearest and keeps the match only when the first is clearly smaller, commonly with a ratio around 0.8. A good match has one clear winner; an ambiguous one has two similar candidates.

Surviving matches still include outliers, so each pair goes through **geometric verification**. **RANSAC** repeatedly picks a minimal random sample of matches, fits the model from it (a fundamental matrix, an essential matrix or a homography), counts how many other matches agree within a pixel threshold and keeps the model with the most inliers. The probability of drawing an all-inlier sample falls as the sample size grows and as the inlier fraction falls, so low inlier ratios need many iterations, which is why a smaller minimal solver such as the five-point essential matrix helps. A pair with too few inliers is discarded. What leaves this stage is not a bag of matches but a **verified two-view geometry**: inlier matches plus the model that explains them.

### Pair selection

With $n$ images there are $n(n-1)/2$ pairs. Matching every pair, **exhaustive matching**, is $O(n^2)$ and is perfect for tens to a few hundred images and ruinous for thousands. The alternatives:

| Strategy | How it picks pairs | Good for | Cost |
|---|---|---|---|
| Exhaustive | Every pair | Small, unordered sets | $O(n^2)$ |
| Sequential | Each image with its neighbours in capture order | Video, ordered walks | $O(n \cdot w)$ for window $w$ |
| Vocabulary tree or retrieval | Each image with the $k$ most similar by global descriptor | Large unordered sets | $O(n \cdot k)$ plus indexing |
| Spatial | Images whose GPS or pose priors are close | Drones, robots, ARKit | $O(n \cdot k)$ with a spatial index |
| Hybrid | Sequential plus loop-closure retrieval | Long videos | near linear |

Retrieval ranks images by visual similarity using a vocabulary of quantised descriptors or a learned global embedding. Spatial selection trusts a prior: a drone's GPS position or a robot's pose says which images can possibly overlap, with no image analysis at all. The risk of any non-exhaustive strategy is a missed pair, which can leave the pose graph disconnected or weakly linked. Sequential matching is also blind to loop closure, because the first and last image of a ring are far apart in the sequence.

### What this means for the engine

Pair selection is a pluggable policy, chosen from the capture type and the priors available, and the engine records which policy produced each pair. Matching cost scales with the pair count, so pair selection is the main lever on the whole pipeline's time and the natural unit for fan-out across workers. Verified two-view geometries are stored as first-class artefacts: they can be merged across workers, cached and reused when an image is added. The quality state exposes the pair graph, so an agent can see that two halves of a scene share only two links and ask for more overlap there.

---

## 5. Structure from motion

### From pairs to a reconstruction

**Structure from motion** (SfM) takes the verified matches and produces camera poses, intrinsics and a sparse 3D point cloud. The central data structure is the **track**: one physical point seen as a chain of matched keypoints across several images. A track seen in two images supports a triangulation; a track seen in ten pins the point and the cameras far more tightly. Long, consistent tracks are the raw material of an accurate reconstruction.

Two families of solver exist.

**Incremental SfM**, the approach of COLMAP, builds the model one image at a time. It initialises from a well-conditioned pair, triangulates their shared points, then repeatedly selects the next image that sees many already-triangulated points, **registers** it by solving a perspective-n-point (PnP) problem against the known 3D points, triangulates new points, and periodically runs bundle adjustment to keep errors from compounding. It is accurate and tolerant of bad data, because the model is checked and corrected at every step. It is also sequential in nature, does repeated bundle adjustment on a growing model and tends to slow down heavily as scenes grow. It can drift, and it can lock onto a wrong initialisation.

**Global SfM** estimates all poses together. **GLOMAP** is the recent practical example. It first solves **rotation averaging**: from the pairwise relative rotations, find the absolute rotation of every camera so that they agree as well as possible, which is robust because rotations are well constrained by two-view geometry. It then runs **global positioning**: find camera positions and point positions jointly, given the rotations, from the feature tracks, without the usual intermediate triangulation step. A final bundle adjustment refines the result. Global methods are much faster on large sets and have no incremental drift, because every constraint is used at once. They are less forgiving of a poisoned pair graph: a wrong relative rotation can corrupt the averaged solution, and quality of the input matches matters more.

| | Incremental (COLMAP) | Global (GLOMAP) |
|---|---|---|
| Order | One image at a time | All at once |
| Speed on large sets | Slows as the model grows | Much faster |
| Robustness to bad pairs | High, corrected by repeated BA | Lower, depends on pair filtering |
| Failure style | Drift, wrong initialisation, split models | A global solve that is wrong everywhere |
| Output | Possibly several disconnected models | One model where the graph is connected |

### Failure modes

SfM fails in recognisable ways, each tied to the geometry or the matching:

- **Repetitive texture.** Brick walls, tiles, windows and fences produce many plausible but false matches. Ratio tests reject some; those that survive can pass geometric verification and join the wrong parts of the scene.
- **Symmetry.** A symmetrical building or a ring of identical objects can yield a reconstruction in which two sides are fused or a loop closes on the wrong face.
- **Low texture.** Blank walls, sky, calm water, matte single-colour objects give no keypoints. The images may not register at all, or register on the background.
- **Reflective and transparent surfaces.** The visible pattern is a view of something else and moves differently from the surface. Glass, polished paint, chrome and still water yield matches that obey the geometry of the reflected world, not the surface.
- **Moving subjects.** People, fish, grass in the wind and waving kelp violate the assumption of a static scene. A rigid reconstruction cannot explain them, and they pollute matching and then dense reconstruction.
- **Insufficient parallax.** A pure rotation or very small baseline gives no depth, as section 3 shows.
- **Mixed lenses and zooms** that are treated as one camera.

A reconstruction can end up in several **components**: separate models that never joined, each with its own arbitrary frame and scale. Reporting only the largest one hides a failed capture.

### What this means for the engine

The engine supports both solvers behind one interface, with global SfM as the fast path and incremental as the robust one, and it can run a global solve and verify it with a short incremental or bundle-adjustment pass. Every run reports the registration rate, the number of components and the images that did not register, because these are the answer to "did it work?". Masks, which exclude moving subjects and the sky from feature extraction, are first-class inputs. The failure-mode list above is the source for the capture guidance the engine gives to a person or a robot: low-texture rooms get a request for more oblique views and overlap, mirrors and glass get flagged.

---

## 6. Bundle adjustment

### The objective

**Bundle adjustment** (BA) is the refinement at the heart of every pipeline. It adjusts all the camera poses, optionally the intrinsics, and all the 3D points at once so that the predicted pixel positions of the points match the observed ones as closely as possible. The name comes from the bundles of rays that connect each camera centre to its points, adjusted until they all fit.

Let $\pi(K_i, R_i, \mathbf{t}_i, \mathbf{X}_j)$ project point $j$ into image $i$, and let $\mathbf{x}_{ij}$ be the observed pixel. The objective is the sum of squared **reprojection errors**:

$$
\min_{\{R_i, \mathbf{t}_i, K_i\},\{\mathbf{X}_j\}} \; \sum_{(i,j)\in \mathcal{O}} \rho\!\left( \left\| \pi(K_i, R_i, \mathbf{t}_i, \mathbf{X}_j) - \mathbf{x}_{ij} \right\|^2 \right)
$$

where $\mathcal{O}$ is the set of observations. Under Gaussian pixel noise this is the maximum-likelihood estimate, which is why reprojection error, measured in pixels, is both the quantity optimised and the headline quality number.

### Robust losses

Some observations are wrong: a false match that survived verification or a moving object. A squared loss gives a wrong observation enormous leverage. The robust function $\rho$ flattens the penalty for large residuals. A **Huber** loss grows linearly beyond a threshold, a **Cauchy** loss grows logarithmically, and a **soft L1** loss sits between. Outlier tracks are also removed explicitly by filtering observations whose error exceeds a threshold, then re-running the adjustment.

### Solving it

The problem is non-linear least squares, solved by **Levenberg–Marquardt**: at each step linearise the residuals around the current estimate, with Jacobian $J$ and residual vector $\mathbf{r}$, and solve the damped normal equations

$$
(J^\top J + \mu\,D)\,\boldsymbol{\delta} = -J^\top \mathbf{r}
$$

The damping $\mu$ interpolates between Gauss–Newton, fast near a solution, and gradient descent, safe far away. The step is accepted if the cost falls, and the damping is adjusted accordingly.

For a thousand-image reconstruction with a million points the full system is far too large to solve densely, but it has structure. Each observation touches one camera and one point, so $J^\top J$ is block-sparse: camera blocks and point blocks, with cross terms only where a point is seen by a camera. The point-point block is **block diagonal**, one small $3 \times 3$ block per point, and cheap to invert. The **Schur complement** eliminates all the points analytically, leaving a much smaller **reduced camera system** whose size depends on the number of cameras only. Solve it, then back-substitute for the points. This is why BA scales to large sets, and why a camera count of a few thousand is comfortable while the point count can be in the millions.

### Gauge freedom: what images alone cannot tell

The objective depends only on pixel coordinates. Move, rotate and uniformly scale the whole scene, cameras and points together, and every projection stays exactly the same: a toy-sized scene photographed from toy-sized distances gives the same pictures as a building. A reconstruction from images alone is therefore defined only **up to a similarity transform**, $\mathrm{Sim}(3)$, which has seven degrees of freedom:

| Freedom | DoF | What it means |
|---|---|---|
| Rotation | 3 | Which way is up, which way is north |
| Translation | 3 | Where the origin is |
| Scale | 1 | Whether a unit is a millimetre or a kilometre |

This is **gauge freedom**. The optimiser handles it by fixing the gauge arbitrarily: pinning the first camera, fixing one camera's translation and one distance, or by using a damping that makes the system solvable. Whatever it picks, the choice is arbitrary and has nothing to do with the world. A model in this state has **arbitrary scale**: its internal unit is meaningless until something fixes it.

### Fixing scale and frame

Something external must supply the seven numbers. The sources, in rough order of strength:

- **Known poses.** A robot's odometry or SLAM output, an iPhone's ARKit track, a motion-capture or total-station rig. These carry metric scale and a frame directly.
- **GPS or GNSS.** Drone and camera GPS give camera positions in a geographic frame. Consumer GPS is metres off in absolute terms, and noisy from image to image, so it fixes the similarity transform well over a large area and says little about fine detail. Survey-grade RTK and PPK are much better.
- **Scale bars and markers.** Printed ArUco or AprilTag markers, or a scale bar with two targets at a known separation, give metric scale and, with several markers, frame. They are the underwater and small-object workhorse.
- **Known distances.** A measured dimension of the object, such as the length of a wheelbase or the width of a doorway, fixes scale only.
- **Learned metric estimators.** Feed-forward networks predict metric scale from appearance (section 7). Useful, not guaranteed, and needing verification.
- **Gravity.** An accelerometer fixes the up direction of a phone's pose, which removes two rotational degrees of freedom.

With external information there are two ways to use it. As a **fixed constraint**, the poses or positions are held exactly and the rest is solved around them. As a **prior**, they enter the objective as extra residuals weighted by their uncertainty: the optimiser may move the poses a little if the images disagree strongly enough. Priors are the default for anything that is measured with noise, such as GPS and ARKit, and fixed constraints suit exact data such as a simulator's poses. Treating noisy poses as exact corrupts the reconstruction, because pixel evidence is usually far more precise than the prior over short ranges. Treating exact poses as noisy loses the scale and frame that they provide for free. A common sequence is to run image-only BA, fit a similarity transform from the estimated camera centres to the prior positions, then run a final BA with the priors included.

### Uncertainty

BA gives more than a best estimate. At the optimum, the inverse of the (gauge-fixed) normal matrix $J^\top J$, scaled by the residual variance, approximates the **covariance** of all the parameters: how tightly each pose and each point is determined. Points seen at small parallax have elongated covariance along the viewing ray. Cameras at the end of a chain with little overlap are uncertain. Two numbers matter in practice: the covariance of each point and the uncertainty of each pose, and both are far more informative than a single global reprojection error, which can look excellent on a geometrically weak model.

### What this means for the engine

Every model states its scale as one of two values: metric, with the source of the scale named, or arbitrary. It is never left implicit, and the frame (section 14) is stated alongside. The provenance record names which of the sources above supplied the gauge and how. The BA stage takes poses as priors with explicit covariances or as fixed, never silently as one or the other. Final models carry per-image pose uncertainty and per-point covariance or a summary of it, and the viewer and the agent read them. A model from images alone is flagged as "arbitrary scale" until a scale bar, a known distance or a metric estimator resolves it, and a metric estimate that has not been verified is labelled as an estimate.

---

## 7. Learned feed-forward reconstruction

### What they are

A new family of models skips the pipeline. **DUSt3R** and its successor **MASt3R** take image pairs and regress a **pointmap**: for every pixel, a 3D point in a shared coordinate frame. **VGGT**, **MapAnything** and **Pi3** extend this to many images at once, in a single forward pass of a transformer, predicting camera poses, intrinsics, depth maps and pointmaps. There is no feature extraction, no matching, no RANSAC and no incremental registration. The network has learned, from large datasets, what scenes look like and how views relate, and it outputs a geometric answer directly.

What comes out varies by model: per-view depth, per-view pointmaps, camera extrinsics and intrinsics, and sometimes confidence maps. Some predict metric scale, because they were trained on metric data and learned how large things typically are; others return a normalised, arbitrary scale. MapAnything can also take extra inputs when available, such as known intrinsics or poses, and use them.

### Strengths

They are fast: seconds for tens of views, on a GPU. They work on conditions that defeat the classical pipeline, such as very little texture, small overlap and few views, because the network brings strong priors about scenes. They are therefore good **initialisers**: a rough pose and depth for every image that a classical pipeline can start from, replacing the expensive matching and registration stages. And they are plausible **metric-scale estimators**: a single number that says how big the scene probably is, when nothing else does.

### Limits

Resolution is limited. These networks process images at modest sizes, of order a few hundred to around five hundred pixels on the long side, so the output geometry is coarse next to a twenty-megapixel photograph. Memory and compute grow with the number of views, because the model attends across all of them, so a few dozen to a few hundred views is the practical regime, not thousands. Accuracy is that of a learned prior, not a measurement: errors are smooth and plausible rather than obviously wrong, and nothing in the output says where it is wrong. They are trained on particular kinds of scenes and degrade out of distribution: underwater imagery, strong refraction and unusual optics are not their home ground. They do not model the camera's lens beyond a simple model.

### Why classical BA still verifies them

A feed-forward output is a hypothesis. Bundle adjustment, run on the full-resolution images with matched features and the real lens model, tests the hypothesis against the pixels: if the predicted poses are right, reprojection error falls to a fraction of a pixel; if not, the error stays high and the failure is visible. The sensible use is as a first pass whose result is checked and refined classically, with the measured scale error against a known dimension deciding whether the metric estimate can be trusted.

Licences vary across these models, and several sets of weights are non-commercial. A model's code licence and its weights' licence can differ, and both must be checked before a model enters a default configuration.

### What this means for the engine

Learned reconstruction is an optional stage that produces the same artefact types as the classical path: poses, intrinsics, depth. It feeds bundle adjustment as an initialisation or a prior and is never the final authority. The comparison of learned and classical output, on registration rate, reprojection error and scale error against a known dimension, is a standing measurement. Each model is registered with its licence class, and non-commercial weights are labelled and kept out of the default stack. Input to these models is downscaled, and the engine records that the result came from reduced-resolution images.

---

## 8. Dense reconstruction

### The idea

SfM yields a sparse cloud, thousands to hundreds of thousands of points, enough to place cameras but too sparse to see surfaces. **Dense reconstruction**, or **multi-view stereo** (MVS), estimates depth for nearly every pixel, given the now-known poses. It turns calibrated cameras into a dense 3D model of the scene's visible surfaces.

### Depth maps by photometric consistency

The principle is **photometric consistency**: if a pixel in a reference image sits on a surface at depth $d$, then projecting that 3D point into neighbouring images lands on pixels that look alike. A wrong depth lands on unrelated pixels that do not. For each reference pixel, the algorithm searches over depth for the hypothesis that makes the neighbouring views agree best, usually using the similarity of a small patch around the pixel, for example normalised cross-correlation, rather than single pixels, because single pixels are noisy.

The brute-force version is a **plane sweep**: step through candidate depths, warp the neighbouring images onto each fronto-parallel plane and score the agreement. It is simple and parallel but costs time and memory proportional to the number of depth candidates, and a fronto-parallel assumption fails on slanted surfaces.

**PatchMatch stereo** is the more efficient and more accurate approach, and it is the basis of COLMAP's dense stage. Each pixel holds a hypothesis of depth and surface normal. The hypotheses are initialised randomly, then iteratively improved by two ideas: neighbouring pixels likely belong to the same surface, so a good hypothesis propagates to its neighbours, and random perturbation of a hypothesis refines it. After a few sweeps over the image, good depth and normals emerge without exhaustively testing every depth. The method in COLMAP additionally selects, per pixel, which neighbouring views to use, because occlusion means that only some of them see the point (the paper's name for this is pixelwise view selection).

### Filtering and fusion

Raw depth maps contain errors: occlusions, textureless regions, reflections. Each depth map is filtered, keeping pixels whose depth agrees with the depth maps of other views when projected, a **geometric consistency** check, and whose photometric score is good. The survivors from all views are **fused**: points are lifted to 3D, merged where several views agree on the same location and written out as a dense, coloured point cloud, usually with normals.

### Resolution and memory

Dense cost scales with the number of pixels processed and the number of views used per pixel. Halving the resolution cuts the work by roughly four, and the point count of the result likewise. A fifty-megapixel image set processed at full resolution is expensive in GPU memory and time, and the benefit has a ceiling: the geometry cannot be more accurate than the pose and the calibration allow. Depth maps are usually computed at a reduced resolution that matches the accuracy of the poses, then fused.

COLMAP's dense stereo needs a GPU: CUDA on NVIDIA, or a HIP build on AMD; its documentation describes no CPU or Metal path. This is a property of its implementation, not of the algorithm; the algorithm is portable, and other implementations exist for other backends.

### Why good poses matter

Dense matching assumes the epipolar geometry is exact. A pose error of a fraction of a pixel turns into a depth error and a smear, and a lens model that is wrong at the edge of the frame turns into a systematic shape error: flat surfaces that bow. The dense stage amplifies pose problems and rarely corrects them. Dense reconstruction after a poor registration yields a convincing-looking but wrong surface.

### What this means for the engine

Dense MVS is a placement-constrained stage. The COLMAP implementation needs CUDA, so the coordinator schedules it only to workers that advertise it, and an Apple silicon or AMD machine does the earlier stages and the later ones but not this one unless another implementation is used. Depth maps are separable per view, which makes them the natural unit to fan out, with fusion as the merge step. The engine records the resolution at which dense was run, and refuses to run dense on a model whose reprojection error or registration is poor, saying so rather than producing a convincing wrong surface. Robot and ARKit depth, from LiDAR or RGB-D, can substitute for or seed the photometric depth maps in the fusion.

---

## 9. Surfaces and textures

### From points to a surface

A point cloud has no connectivity, so it cannot be rendered solidly, simulated or placed in a game. A **surface** reconstruction turns points into a triangle mesh.

**Poisson surface reconstruction** treats the oriented points, positions plus normals, as samples of the gradient of an indicator function, 1 inside the object and 0 outside, and solves a Poisson equation for the function whose gradient best fits them. The surface is its level set at 0.5. The method is global, produces watertight surfaces, is robust to noise and smooths over holes, and works on an adaptive octree so that detail concentrates where points are dense. The costs are that normals must be good, that it hallucinates surface across gaps, creating bubble-like blobs where there are none, and that it needs a trim step: the per-vertex sample density is used to remove surface far from any data.

**Delaunay-based meshing** builds a tetrahedralisation of the points, labels each tetrahedron inside or outside using the camera-to-point visibility, since the space between a camera and a point it saw must be empty, and extracts the boundary. It uses visibility information that Poisson ignores, which handles thin structures and open scenes better, at higher complexity.

**TSDF fusion**, the truncated signed distance function, merges depth maps directly into a voxel grid. Each voxel stores the signed distance to the nearest surface, truncated near the surface and averaged across views, and a mesh comes out of the zero level set, extracted with marching cubes. It works naturally with depth from RGB-D sensors, LiDAR and robots, and runs incrementally as frames arrive. Resolution is limited by the voxel size, and memory grows with volume rather than surface, which suits rooms and objects better than city blocks without a sparse or hashed grid.

### Cleanup, decimation and level of detail

Raw meshes have noise, floating fragments, holes and tens of millions of triangles. Cleanup removes small disconnected components and non-manifold edges, fills holes and smooths lightly. **Decimation** reduces the triangle count by collapsing edges with the least geometric error, which preserves shape while cutting the count by orders of magnitude. A set of meshes at decreasing triangle counts, a **level-of-detail** (LOD) chain, serves a game engine, which draws near objects in detail and far objects cheaply. Geometry detail that decimation removes can be moved into **normal maps** baked from the high-resolution mesh onto the low-resolution one.

### Texture

A mesh gets colour by **UV unwrapping**: cutting the surface into charts that are flattened into a 2D texture atlas, with each triangle assigned a place in the atlas. Colour is then projected from the photographs. Each triangle is seen by several cameras, and the choice and combination of them is the substance of texturing. Selecting one best view per triangle, by viewing angle, distance and sharpness, gives crisp results with visible **seams** at the boundaries between views. Blending several views hides seams but blurs any misalignment. Multi-band blending, which blends low frequencies broadly and high frequencies narrowly, and explicit seam levelling are the usual remedies.

Seams are overwhelmingly a consequence of the photographs disagreeing: **exposure differences**, white-balance shifts, vignetting, changing sun and clouds. Geometry-driven blending cannot fix inputs whose colours disagree, which is why consistent development of the whole set (section 12) is a precondition and not a polish step.

### PBR and de-lighting

A texture from photographs is **baked lighting**: it contains the shadows, highlights and colour cast of the moment of capture. A game engine wants **physically based rendering** (PBR) materials, with separate maps for albedo (the base colour, free of lighting), normal, roughness and metalness, which the engine relights. Recovering albedo requires **de-lighting**: removing shading, shadows and, where possible, specular highlights from the captured texture. Diffuse capture conditions (section 11) and cross-polarised light, which removes specular reflection at capture time, make this tractable. De-lighting from a single bad capture is an approximation, and roughness and metalness are generally estimated or authored rather than measured.

### What this means for the engine

Surface reconstruction is selectable, with Poisson as the default for closed objects, a visibility-based method for open or thin scenes and TSDF for depth-sensor input, and each mesh records its method and parameters. Meshes carry a LOD chain and, for game targets, baked normal maps. Texturing consumes the developed, consistent images, and the engine warns when exposure or white balance varies across the set. A textured model states whether its colour is baked lighting or de-lit albedo, and a game-asset export is a distinct, named profile with polygon budget, texture size and scale.

---

## 10. Radiance fields and gaussian splatting

### NeRF in one paragraph

A **neural radiance field** represents a scene as a function, a small neural network, that takes a 3D position and a viewing direction and returns a colour and a density. To render a pixel, the method casts a ray through the scene, samples points along it, queries the network and composites the colours front to back weighted by density, which is differentiable volume rendering. Training adjusts the network so that renderings from the known camera poses match the photographs. The result renders novel views with striking realism, including view-dependent effects, but is slow to train and render in its original form and has no explicit surface.

### 3D gaussian splatting

**3D gaussian splatting** (3DGS) keeps the idea of fitting a scene to photographs but replaces the network with an explicit set of millions of 3D gaussian blobs, each of which carries:

- a **mean** $\boldsymbol{\mu}$, its centre in 3D,
- a **covariance** $\Sigma$, describing its extent and orientation, parameterised as a scale vector $\mathbf{s}$ and a rotation $R$ so that $\Sigma = R\,\mathrm{diag}(\mathbf{s})^2 R^\top$ stays positive semi-definite,
- an **opacity** $\alpha$,
- a **colour** expressed in **spherical harmonics** (SH), a basis for functions on the sphere, so that colour changes with viewing direction; the standard setup uses degree 3, 16 coefficients per colour channel.

Rendering is **differentiable rasterisation**, not ray marching. Each gaussian is projected to the image as a 2D ellipse, using the camera transform and the local linearisation of the projection:

$$
\Sigma' = J\,W\,\Sigma\,W^\top J^\top
$$

with $W$ the world-to-camera rotation and $J$ the Jacobian of the perspective projection at the gaussian's centre. The 2D gaussians are sorted by depth, tiled and alpha-composited front to back:

$$
C = \sum_{i} c_i\,\alpha_i \prod_{j<i} (1 - \alpha_j)
$$

where $\alpha_i$ is the opacity times the 2D gaussian's falloff at the pixel. Every step is differentiable, so a photometric loss between the rendering and the photograph, an L1 term combined with a structural similarity term, produces gradients for the means, scales, rotations, opacities and SH coefficients of every gaussian. This is fast enough to render in real time and to train in minutes to tens of minutes.

### Initialisation, densification and pruning

Training starts from the **sparse points of SfM**, one gaussian per point, with small isotropic scale and colour from the point. This is why 3DGS needs good poses and a reasonable sparse cloud: the poses define the photographic constraints, and the points seed the geometry. An optimisation from random initialisation works on easy scenes and fails on hard ones.

The fixed set of seeds is not enough, so training performs **adaptive density control**. Gaussians whose positional gradient is large, meaning that the area is under-reconstructed, are **cloned** if small, to fill in missing geometry, or **split** if large, to refine detail. Gaussians with near-zero opacity, or that have become huge, are **pruned**. Opacity is periodically reset towards zero so that gaussians that do not earn their keep fade out and are removed. The count therefore grows and shrinks to fit the scene.

### Strengths and weaknesses

Splats are good at what meshes find hard: **view-dependent appearance**, such as glints, sheen and reflections, through the SH colour; **thin and fuzzy things**, such as hair, foliage, wire and kelp, which a surface cannot represent; and soft, volumetric content. They render in real time on ordinary GPUs and look photographic.

They are bad at what metrology needs. A splat is a set of blobs that reproduces the photographs from the training viewpoints. It has **no clean geometry**: the gaussians do not lie on a surface, floaters hang in the air, and the depth rendered from a splat is a composite. Appearance can be correct while the position is wrong, because a view-dependent colour can cheat geometry. It is a poor basis for measurement, collision and engine-ready assets, and its quality away from the training views is unconstrained.

**Meshes from splats** is an open area. Methods such as **2DGS** (two-dimensional gaussian surfels, which have a well-defined normal and intersect rays at a single depth) and **PGSR** (planar-based gaussian splatting with geometric regularisation) change the representation or add geometry losses so that surfaces can be extracted. Results are improving, but the field has no settled recipe that matches classical dense reconstruction for accuracy.

### What this means for the engine

A splat is a rendering artefact of the model, not a geometric one, and the engine labels it so: it is never the source of a measurement or a scale, and exports of splats say that. Splat training consumes the poses and sparse points from the same SfM and BA run as the mesh path, so both representations share one frame and scale. Quality for splats uses held-out view metrics (section 15) because there is no ground-truth geometry to compare against. Mesh-from-splat extraction is an experimental option, compared against classical mesh output and not trusted by default. Training needs a GPU backend, which is a placement constraint like dense MVS.

---

## 11. Capture

All the processing above amplifies the capture. The photographs set a ceiling on quality that no algorithm raises.

### Overlap, parallax and angles

Neighbouring views overlap by **60 to 80 percent**: enough that each point appears in several images and that features match, with enough baseline between them for useful parallax. Aerial mapping, where the flight is planned, often goes higher: around 80 percent forward and 70 percent side overlap. Less overlap leaves holes and weak links; much more adds data without adding geometry, because the baseline shrinks.

The scene must be seen from **varied angles**: parallax is what carries depth. Walking in an arc around an object, rather than rotating on the spot, gives baseline. Several rings at different heights, and some oblique views, constrain a shape better than one flat ring. Corners, concavities and undersides need dedicated views, since a surface seen only at grazing angles reconstructs poorly. Close-ups for detail should be tied into a wider set with intermediate distances, so that the zooming-in is registered and not left as an island.

### Distance and ground sampling distance

The size on the object that one pixel covers is the **ground sampling distance** (GSD):

$$
\mathrm{GSD} = \frac{p \cdot Z}{f}
$$

with $p$ the pixel pitch on the sensor, $Z$ the distance to the surface and $f$ the focal length, in the same units. A camera with a pixel pitch of 4.4 µm and a 24 mm lens at 10 m has a GSD of about 1.8 mm. For a drone, $Z$ is the flying height. The achievable accuracy is typically a small multiple of the GSD, and the distance is therefore a design parameter: halve the distance, or double the focal length, to halve the GSD.

### Sharpness

Matching and texturing depend on sharp pixels. **Shutter speed** must beat both subject motion and hand shake, and a common guide is a reciprocal of the focal length or faster, with image stabilisation helping for the camera but not for the subject. **Aperture** trades depth of field against **diffraction**: stopping down widens the sharp zone, but the Airy disk grows, with a diameter of about $2.44\,\lambda\,N$ for wavelength $\lambda$ and f-number $N$. At f/11 and 550 nm that is about 15 µm, several pixels on a high-resolution sensor, so there is a sweet spot, often f/5.6 to f/8 on a full-frame camera. **Depth of field** matters for close work: a macro subject needs the whole object inside the sharp zone, or focus stacking. A shot that is out of focus on the object produces few keypoints and a soft texture. High ISO is better than blur, and noise is better than motion.

### Exposure, white balance and lighting

**Lock exposure and white balance** for a capture so that the images agree: aperture, shutter speed and ISO fixed in manual, or at least exposure compensation disciplined, and a fixed white balance. Automatic changes between frames cause the colour seams and brightness steps that appear in the texture. Shooting RAW makes the rest recoverable (section 12).

**Light** should be diffuse: overcast sky, a shaded area, a lightbox. Hard shadows move as the camera moves, which violates the assumption that the scene looks the same from every angle, and they bake into textures. **Specular highlights** slide across a glossy surface as the camera moves and so do not belong to the surface; photometric matching and surface reconstruction both fail there. **Cross-polarisation**, with a polariser on the light and a perpendicular one on the lens, removes the specular reflection and leaves the diffuse colour, which helps shiny objects and de-lighting. Moving lights, or a moving shadow of the photographer, create a different illumination in every frame.

### Turntables and masking

For small objects, the camera can stay still and the object rotate on a turntable. A caution: the background then does not move with the object, so the background features, which are static, agree with a camera that has not moved while the object features agree with one that has. Mixed motion confuses the SfM. The remedy is **masking**: segmenting the object so that features come only from it, or a featureless background and a surface with targets or texture. A turntable with a patterned base can supply features on the turntable itself, which rotates with the object. Masks are also how people, vehicles and other moving subjects are kept out of a scene.

### Video versus stills

Video is easy to capture and delivers continuous coverage, but it has costs: lower resolution than stills, compression, motion blur from long exposures at low frame rates and rolling shutter (section 2). Adjacent frames are nearly identical, so using all of them adds cost and little baseline. **Frame selection** keeps frames that are sharp, by a blur measure such as the variance of the Laplacian, and sufficiently separated in motion that the baseline is useful, usually by sampling on camera displacement or optical flow instead of a fixed frame interval. Stills are preferable where resolution and quality matter, and video where coverage and speed do.

### What this means for the engine

The engine states what good capture needs and judges a capture after the fact, so these numbers drive the quality report: overlap and parallax per region, estimated GSD per image, a blur score per image, exposure and white-balance variance across the set. It ingests video through frame selection by sharpness and motion, and records the policy. It treats diffuse-light, locked-exposure sets as the reference case and flags deviations. Its capture advice to a person or a robot names the weakest region and the view that would improve it.

---

## 12. RAW and colour

### What RAW is

A camera sensor counts photons per pixel. A **RAW** file stores those counts almost as they were read, so the data is **linear**: double the light, double the value. Each pixel sits under a colour filter, red, green or blue, arranged in a **Bayer mosaic**, usually with twice as many green as red or blue, so each pixel measures one colour only. **Demosaicing** interpolates the two missing colours at every pixel to give a full-colour image. The file also carries a black level, a white (saturation) level and often a camera-specific colour matrix and an as-shot white balance, as metadata.

A camera JPEG has been through a pipeline that the RAW has not: demosaic, white balance, a colour transform, a tone curve, sharpening, noise reduction and 8-bit compression. Those steps are not reversible, and they are not the same from one shot to the next, because auto white balance and scene-dependent tone mapping vary.

### White balance, exposure and tone

**White balance** scales the red, green and blue channels so that a neutral object comes out neutral under the light it was lit by. The channels are multiplied by gains; the sensor's native response is then converted to a standard colour space by a matrix. **Exposure** is a multiplier on the linear values, a change of one stop being a factor of two. These are cheap, exact operations in linear space, and they are where RAW wins, because the headroom of 12 to 14 bits is preserved.

Displays and files are not linear. The **tone curve** compresses the linear values into the range of the output, and the **gamma** encoding of sRGB, close to a power of 1/2.2, spends bits where human vision is more sensitive, in the shadows. Image-processing operations such as blending, resizing and averaging are physically meaningful in linear light and subtly wrong in gamma-encoded values, which is one reason to do the calculation in linear space and apply the curve last.

### Why consistency matters

Feature matching tolerates some variation, but descriptors work best when the same point looks alike across images, and large brightness and colour differences cost matches. Texturing is far less tolerant: the final colour of a surface is a blend of several photographs, and where the photographs disagree, the blend shows steps and seams. **Splats** are the most exposed. A gaussian splat fits the photographs as given, so a set in which exposure and white balance drift trains a scene with colour and brightness that depend on the view, "baked" into the gaussians' appearance, or floaters that explain the differences. Auto exposure and auto white balance in the camera, or a per-image Lightroom adjustment, make each image internally pleasing and the set mutually inconsistent.

The remedy is to **develop the whole set with one recipe**: one white balance for the set (or one computed from a reference), one exposure, one tone curve, applied to linear data, with only a deliberate per-image exposure correction when the capture's own exposure changed. The goal is for a given surface point to give nearly the same value in every image that sees it.

### Colour checkers

A **colour checker**, a card with known patches, photographed in the scene's light gives ground truth for white balance and, with several patches, for a colour correction matrix from camera to a standard space. A grey card alone fixes white balance and exposure. One shot of the card per lighting condition is enough to calibrate a set shot in constant light. Under changing light, such as sun and cloud, or at changing depth underwater, the card can only calibrate the moment it was photographed.

### What this means for the engine

The imaging stage decodes RAW to linear data, sets one white balance and exposure for the whole set, applies one tone curve and writes the developed images that all later stages read. The developed images are artefacts with their recipe recorded, so that a result can be traced back to the develop settings. The engine measures and reports exposure and white-balance variance across a set and warns before texturing or splat training. A colour checker or grey card image in the set is detected and used. Developed images are kept at the highest bit depth the downstream stage accepts, and the 8-bit JPEG path is a fallback, not the reference.

---

## 13. Underwater

Underwater imagery breaks three assumptions of the previous sections at once: the camera geometry, the colour and the clarity of the medium.

### Refraction at the port

A housing puts a window, the **port**, between the camera and the water. Light bends where it crosses between media of different refractive index, as **Snell's law** says:

$$
n_1 \sin\theta_1 = n_2 \sin\theta_2
$$

with $n \approx 1.00$ for air and about $1.33$ for water; seawater is slightly higher.

A **flat port** is a plane window. A ray leaving the water bends towards the normal as it enters the air behind the glass, so objects appear closer and larger, and the field of view narrows, by roughly the factor 1.33 for a camera whose pupil sits near the port. The key point for geometry is that the bend depends on the angle at which the ray meets the port, and the rays do not meet at a single centre of projection any longer. The camera plus flat port is a **non-single-viewpoint** camera: the rays in water, traced back, are tangent to a caustic rather than passing through one point. Distortion is then a function of **distance to the object** as well as of image position. A radial distortion polynomial, tuned for one distance, absorbs part of the effect but not all of it: the model is only approximate, and the residual grows with the viewing angle and changes with distance. It is the basis for the common observation that flat-port underwater models bow, even when the reprojection error looks tolerable. A correct treatment models the refraction explicitly, with the port's distance from the camera, its thickness and normal, and traces rays through it.

A **dome port** is a spherical window. If the camera's **entrance pupil** is at the centre of the sphere, every ray from the water meets the dome at normal incidence and passes undeviated; the dome then acts as a lens that forms a virtual image of the scene, closer than the object, that the lens focuses on. The projection is then close to pinhole with the original field of view, and the distortion terms can absorb the residual. In practice, the centring is imperfect and the virtual image is close, so lenses must focus near, and the model remains approximate for a misaligned dome. Domes are the preferred geometry for photogrammetry.

### Colour: attenuation

Water absorbs light, and it absorbs different wavelengths at different rates: **red** is attenuated first, within a few metres, then orange and yellow, leaving blue and green. A photograph at depth is blue-green and loses saturation with distance from the subject, since the path from light to subject to camera is long. Colour loss depends on the **range** from camera to subject, not on depth alone, and on the water's properties, which vary with place, season and plankton. A strobe restores colour near the camera; it lights the subject at a distance of metres and cannot light the reef at ten.

### Backscatter and caustics

Particles in the water scatter light back into the lens. **Backscatter** is the veiling haze, or the white specks of a strobe lighting suspended particles near the lens. It is added to the image in addition to the subject signal, and it reduces contrast, and it grows with range until it saturates at the colour of the water. In shallow, sunlit water the surface waves focus light into moving bright networks on the seabed, **caustics**, that move from frame to frame: they are lighting that is not part of the scene, and they break the static-scene assumption in the same way as moving shadows.

### The Sea-thru model

Akkaynak and Treibitz modelled underwater image formation per colour channel $c$ as the sum of two components that behave differently with the range $z$:

$$
I_c = J_c\,e^{-\beta_c^{D} z} + B_c^{\infty}\left(1 - e^{-\beta_c^{B} z}\right)
$$

$J_c$ is the unattenuated colour of the surface, the one the image should show. The first term is the **direct signal**, which decays exponentially with range at a rate $\beta^D_c$. The second is **backscatter**, which rises with range and saturates at a veiling light $B^\infty_c$ with its own coefficient $\beta^B_c$. The two coefficients differ — the revised image formation model of Akkaynak and Treibitz (CVPR 2018) showed that backscatter is governed by a different coefficient from the direct signal, and the authors' earlier work, cited there, that the coefficients depend on range, the scene and the imaging conditions rather than on the water alone. Sea-thru (CVPR 2019) applies that model to images with known range. Earlier simple models used one coefficient per channel for both terms.

The formula inverts if range is known: subtract the backscatter, divide by the attenuation, and recover $J$. This is why **geometry comes first and colour second**. A reconstruction produces a depth, a range from the camera, for every pixel, through the poses and the dense or mesh geometry. A single image has no such range. With it, the correction becomes a physically grounded per-pixel operation instead of a global colour filter. The estimation of coefficients, from colour charts or from the scene's own statistics, is part of the method and is not trivial.

### Scale underwater

Scale cannot come from GPS, which does not penetrate water. It comes from **scale bars** placed in the scene, from **fixed-spacing lasers** that project two or more dots a known distance apart onto the subject, from **coded markers** such as AprilTags, from a known dimension of a structure, or from a vehicle's own pose sources: a diver's depth gauge, an ROV's navigation. Because refraction distorts the apparent size, a scale bar that is measured through a flat port inherits the same error unless the refraction is modelled.

### What this means for the engine

The camera model for an underwater set includes the port type, with a flat-port refraction model as a distinct option from pinhole plus distortion, and the engine records which was used. The quality report separates "residuals consistent with an unmodelled flat port" from other failures. The imaging stage does not apply a global white balance to an underwater set as though it were air, and range-dependent colour correction runs after reconstruction, using per-pixel range from the geometry, and writes its coefficients to the provenance. Scale for underwater models comes from scale bars, lasers, markers or a known dimension, and the model states which, because the GPS path is closed. Moving subjects (fish, kelp) and caustics are masked or flagged.

---

## 14. Frames, units and georeferencing

### Frames and handedness

Every coordinate belongs to a **frame**: a choice of origin and axes. The engine uses **right-handed** frames: with $X$ to the right and $Y$ forward, $Z$ points up, and the rotation that takes one to another has determinant $+1$. A mirrored frame, which has determinant $-1$, is not a rotation and silently flips the model. Conventions differ among the tools the engine touches. Computer vision camera frames, as used by COLMAP and OpenCV, put $Z$ forward, $X$ right and $Y$ down. Robotics conventions put $X$ forward, $Y$ left and $Z$ up. Graphics and game engines vary: some are $Y$-up, some $Z$-up and some are left-handed. Every import and export converts between them and states the convention.

All lengths are in **metres** inside the engine, and a model that has only arbitrary scale says so; it never carries a unit that is not true. Angles are in radians internally.

### Camera pose and robot pose

A **camera pose** is the transform between the camera frame and a world frame. A **robot pose** is the transform of the robot's body frame, whose origin is often at the base or the centre of the wheel axle, in a map or world frame. A camera mounted on a robot is related to the body by a fixed **extrinsic calibration**, so the camera pose is the robot pose composed with that mount transform:

$$
T_{\text{world}\leftarrow\text{camera}} = T_{\text{world}\leftarrow\text{body}}\; T_{\text{body}\leftarrow\text{camera}}
$$

Forgetting the mount transform, or applying it in the wrong order or direction, is the usual reason that robot-supplied poses give a model that is offset or rotated by a constant. The notation $T_{a\leftarrow b}$ is used throughout, since it makes composition a matter of matching adjacent subscripts.

### World and map frames

A reconstruction has an internal frame, fixed by the gauge (section 6), and a **world** or **map** frame, which is the frame of the robot's map, of the site or of the geographic system. The transform from one to the other is the similarity transform that the georeferencing step estimates. Both frames, and the transform between them, are stored; neither replaces the other, so that a model can be re-aligned without re-running the reconstruction.

### Geographic coordinates

Drone work brings **geographic coordinates**. **WGS84** is the global reference system used by GPS: latitude, longitude and height on a reference ellipsoid. Latitude and longitude are angles, not distances, and a degree of longitude shrinks with latitude, so they are poor coordinates for geometry. Two conversions follow. **ECEF** is a global Cartesian frame centred on the Earth's centre. A **local ENU** frame (east, north, up) is a Cartesian frame tangent to the ellipsoid at a chosen origin and is a right-handed frame in metres, appropriate for a site of up to a few kilometres. Reconstruction runs in a local frame, and the transform to WGS84 is attached as metadata.

Heights need care. GPS heights are **ellipsoidal**, above the WGS84 ellipsoid; maps and elevations are usually **orthometric**, above a geoid model of mean sea level; the two differ by tens of metres in places. Drone EXIF may record altitude relative to the take-off point, or a barometric altitude, rather than either. The source and reference of every height must be known before it is used as a constraint.

### What this means for the engine

Every artefact states its frame, its handedness and its units, and the data model stores transforms with a named source and target frame, never a bare matrix. Import and export adapters carry the convention conversions and are tested against known geometry. The robot seam depends on getting the mount transform and the pose direction right, which is why the contract between the engine and a robot states them. Georeferenced models are stored in a local ENU frame with the WGS84 origin recorded, and the height reference of any input altitude is a required field. A model in a non-metric, arbitrary frame says so instead of pretending.

---

## 15. Measuring quality

A reconstruction that looks right can be wrong, and a number that looks excellent can describe a weak model. Quality is therefore a set of measurements, read together.

### Reprojection error

The **reprojection error** is the pixel distance between each observed keypoint and the projection of its triangulated point. Report the **mean**, which BA minimises, and the **distribution**: median, a high percentile and the share of observations above a threshold. A mean of 0.5 px with a long tail of bad tracks is a different model from a mean of 0.5 px with a tight spread. A low reprojection error does not prove accuracy: a model with too few points, a short baseline or too flexible a camera model fits its own observations well and still has the wrong shape. Its scale is also tied to the image resolution, so error is compared at equal resolution.

### Registration, tracks and coverage

- **Registration rate**: the share of input images that received a pose. The first measure of whether the capture worked. Report which images failed.
- **Components**: how many disconnected models resulted, and the share of images in the largest.
- **Track length**: the mean and distribution of the number of images per 3D point. Longer tracks mean tighter geometry.
- **Points per image**: sparse points visible per image; a low value flags a weak or low-texture image.
- **Coverage**: where in the scene and in the image the observations lie, and where in space the cameras are. Gaps in angular coverage predict holes and weak geometry. Observations clustered in the middle of the frame under-constrain the lens distortion.
- **Triangulation angle** and the resulting **uncertainty** of the points and poses (section 6).

### Accuracy against the world

Internal consistency is not accuracy. Accuracy needs an external reference.

- **Scale error against a known dimension**: measure a length in the model and compare it to the real one, as a percentage. This is the simplest honest test, and it is the right test of a metric-scale estimate.
- **Control points versus check points**: **control points** are targets with known coordinates that enter the adjustment and fix the frame. **Check points** are targets with known coordinates that are withheld from the adjustment and compared with the model afterwards. Error at the check points is the independent measure of accuracy; error at the control points is not, because the optimiser has already fitted them. A model with excellent control residuals and poor check residuals is over-fitted or biased.
- **Comparison with reference geometry**: for robot data with ground truth, the distance between the model and the known scene geometry, within a stated tolerance.

### Splats: held-out views

A splat has no geometry to measure, so its quality is photometric. Hold out some of the registered images from training, render the model from their poses and compare the rendering with the photograph:

- **PSNR**, peak signal-to-noise ratio, the pixel-wise error on a log scale, higher is better, which is simple and misses structural differences.
- **SSIM**, structural similarity, which compares local luminance, contrast and structure.
- **LPIPS**, a learned perceptual distance based on deep-network features, where lower is better, and closer to human judgement of blur and texture.

The three are reported together on views the training never saw. They measure how well the model reproduces photographs, and say nothing about geometric accuracy.

### What this means for the engine

Quality is state, not a log line: each of the measurements above is stored per reconstruction, per image and per region, and surfaced through the interface, the API and the MCP server alike. The headline for a model is a short table that always includes registration rate, component count, reprojection error as mean and tail, the scale source and, when available, an error against a known dimension or check points. Check points are a distinct input type from control points, and the engine refuses to report accuracy from points that it also fitted. Splat metrics are labelled as photometric and are never presented as accuracy.

---

## 16. Glossary

**Albedo.** The base colour of a surface with lighting removed.

**Alpha compositing.** Combining semi-transparent layers front to back, weighted by opacity.

**Arbitrary scale.** A reconstruction whose unit has no relation to metres, as produced from images alone.

**ArUco, AprilTag.** Printed square fiducial markers with an ID, detectable in images and used for scale, pose and frame.

**Backscatter.** Light scattered by particles in a medium back into the camera, veiling the image.

**Baseline.** The distance between two camera centres.

**Bayer mosaic.** The pattern of red, green and blue filters over a sensor's pixels.

**Brown–Conrady model.** A lens distortion model with radial and tangential polynomial terms.

**Bundle adjustment (BA).** Joint refinement of poses, intrinsics and points by minimising reprojection error.

**Camera frame.** The coordinate frame fixed to the camera, with the origin at the centre of projection.

**Caustics.** Bright, moving light patterns focused by a rippling water surface.

**Check point.** A point with known coordinates withheld from adjustment and used to test accuracy.

**Component.** One connected reconstruction among possibly several from the same image set.

**Control point.** A point with known coordinates that enters the adjustment and fixes the frame.

**Covariance.** A matrix describing the uncertainty of an estimate and the correlation among its parts.

**Cross-polarisation.** Polarisers on light and lens, at right angles, that remove specular reflection.

**Decimation.** Reducing a mesh's triangle count while preserving shape.

**De-lighting.** Removing baked lighting from a texture to recover albedo.

**Demosaicing.** Interpolating a full-colour image from the Bayer mosaic.

**Dense reconstruction.** Estimating depth or 3D points for nearly every pixel given poses.

**Descriptor.** A vector summarising the neighbourhood of a keypoint for matching.

**Dome port, flat port.** Spherical and planar windows of an underwater housing.

**Entrance pupil.** The apparent aperture of a lens as seen from the front; the effective centre of projection.

**Epipolar line, epipole, epipolar constraint.** The line in one image on which the match of a point in the other must lie; the image of the other camera's centre; the rule that expresses this.

**Essential matrix.** The $3 \times 3$ matrix of rank 2 relating normalised points in two calibrated views, with 5 degrees of freedom.

**Extrinsics.** The rotation and translation relating the world frame to the camera frame.

**Feature, keypoint.** A repeatable, distinctive image location.

**Fundamental matrix.** The $3 \times 3$ rank-2 matrix relating pixel points in two views, with 7 degrees of freedom.

**Gamma, tone curve.** The non-linear encoding that maps linear light to display values.

**Gauge freedom.** The part of a solution that the data cannot determine; here, the seven degrees of a similarity transform.

**Geometric verification.** Testing putative matches against a geometric model, typically with RANSAC.

**Global SfM.** Solving all poses together via rotation averaging and global positioning.

**Ground sampling distance (GSD).** The footprint of one pixel on the surface.

**Homography.** A $3 \times 3$ projective map between two images of a plane, or of a rotating camera.

**Incremental SfM.** Building a reconstruction by registering images one at a time.

**Intrinsics.** Camera parameters that do not depend on pose: focal length, principal point, distortion.

**Level of detail (LOD).** A set of versions of a mesh at different complexity.

**Levenberg–Marquardt.** The damped non-linear least-squares algorithm used in bundle adjustment.

**LPIPS, PSNR, SSIM.** Image-similarity metrics used to judge renderings.

**Marching cubes.** An algorithm that extracts a mesh from a level set on a voxel grid.

**Multi-view stereo (MVS).** Dense reconstruction from multiple calibrated views.

**NeRF.** A neural radiance field: a network mapping position and direction to colour and density.

**Normal map.** A texture storing surface-normal detail for a lower-resolution mesh.

**Orthometric height, ellipsoidal height.** Height above the geoid (mean sea level) and above the WGS84 ellipsoid.

**PatchMatch.** A randomised search that propagates good depth and normal hypotheses between neighbouring pixels.

**Photometric consistency.** The principle that a correct depth makes corresponding pixels look alike.

**PBR.** Physically based rendering; materials described by albedo, roughness, metalness and normals.

**Pointmap.** A per-pixel map of 3D points in a shared frame, as predicted by feed-forward models.

**Poisson reconstruction.** Surface extraction from oriented points by solving a Poisson equation.

**Principal point.** The image point where the optical axis meets the sensor.

**Prior.** Information about a quantity included in an estimate with a weight, as opposed to a hard constraint.

**RANSAC.** Random sample consensus: robust model fitting by repeated minimal sampling.

**Ratio test.** Keeping a match only when the best candidate is clearly closer than the second best.

**Reprojection error.** The pixel distance between an observation and the projection of its estimated 3D point.

**Robust loss.** A cost function that limits the influence of large residuals.

**Rolling shutter.** Row-by-row exposure, so that rows are captured at different times.

**Rotation averaging.** Estimating absolute rotations from pairwise relative ones.

**Schur complement.** The elimination of point parameters in bundle adjustment, leaving a smaller camera system.

**Sim(3).** The group of similarity transforms: rotation, translation and uniform scale, 7 degrees of freedom.

**Spherical harmonics.** A basis for functions on the sphere, used for view-dependent colour.

**Splat.** A 3D gaussian used as a rendering primitive; also the whole scene made of them.

**Structure from motion (SfM).** Recovering camera poses and sparse 3D points from images.

**Track.** A set of matched keypoints across images that corresponds to one 3D point.

**Triangulation.** Locating a 3D point from its projections in two or more calibrated views.

**TSDF.** Truncated signed distance function; a voxel representation used to fuse depth maps into a surface.

**UV unwrapping.** Mapping a 3D surface to 2D texture coordinates.

**White balance.** Per-channel gains that make neutral objects neutral under the scene's light.

**WGS84, ECEF, ENU.** The global geodetic datum used by GPS; the Earth-centred Cartesian frame; the local east-north-up frame.

---

## 17. Further reading

- Hartley, R. and Zisserman, A. *Multiple View Geometry in Computer Vision*, 2nd edition, Cambridge University Press, 2004. The reference for sections 2, 3 and 6.
- Szeliski, R. *Computer Vision: Algorithms and Applications*, 2nd edition, Springer, 2022. A broad modern survey.
- Schönberger, J. L. and Frahm, J.-M. "Structure-from-Motion Revisited", CVPR 2016. The incremental pipeline of COLMAP.
- Schönberger, J. L., Zheng, E., Frahm, J.-M. and Pollefeys, M. "Pixelwise View Selection for Unstructured Multi-View Stereo", ECCV 2016. The dense stage of COLMAP.
- Kazhdan, M., Bolitho, M. and Hoppe, H. "Poisson Surface Reconstruction", Eurographics Symposium on Geometry Processing, 2006.
- Mildenhall, B. et al. "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis", ECCV 2020.
- Kerbl, B., Kopanas, G., Leimkühler, T. and Drettakis, G. "3D Gaussian Splatting for Real-Time Radiance Field Rendering", ACM Transactions on Graphics (SIGGRAPH), 2023.
- Akkaynak, D. and Treibitz, T. "Sea-thru: A Method for Removing Water from Underwater Images", CVPR 2019.
- Pan, L., Baráth, D., Pollefeys, M. and Schönberger, J. L. "Global Structure-from-Motion Revisited", ECCV 2024. The GLOMAP paper.
