# GPU rental spec for RC-P7 (2026-11-24)

Decision input for the owner. RC-P7 ([brief](../concept/RC-brief.md), "RC-P7 — Distribution on a large set") needs one rented GPU beside the GB10 and the X3. This note states what that machine must be, compares providers on prices read from their own pages today, recommends two options with a cost cap, and lists the launch and teardown steps. Nothing is rented and no account exists yet.

Tags: `[V]` the figure was read on the provider's own page or price API on 2026-11-24 (the URL is inline). `[unverified]` the figure comes from a search snippet, a third-party page, memory or an estimate, or the provider's page did not load. Estimates are marked as such.

## 1. What P7 needs from the rented machine

### The job

RC-P7's criterion is dense depth per view split across the GB10, the X3 and one rented GPU, plus registration cut into clusters solved on different machines. The rented machine takes one slice of each.

- **Input:** COLMAP's Graham Hall, 1,273 images, six archive parts totalling 11.78 GB [V] (`graham-hall.zip` 1.29 GB plus `.z01` to `.z05` at 2.10 GB each; sizes from the HTTP headers of the release assets listed on <https://demuc.de/colmap/datasets/>). The page gives no pixel size.
- **Dense slice:** about one third of the views, roughly 425, through `pycolmap.patch_match_stereo` (CUDA), photometric then geometric pass. The slice is the unit the split assigns; the share per machine is set by the coordinator, so the rented GPU may get more or less.
- **Registration cluster (optional on this node):** one overlapping cluster of roughly 400 images: GPU SIFT extraction, matching, then COLMAP incremental or GLOMAP mapping. This stage runs mostly on the CPU and fits the same node.
- **Not needed:** gsplat. RC-P7 measures depth and registration, so the gsplat figure below only sizes the node if the owner later adds a splat to the same rental.

### GPU class and VRAM

| Stage | Measured on the GB10 in RC-P2 | Consequence |
|---|---|---|
| `patch_match_stereo`, 2000 px | up to 1,483 MiB of GPU memory, 86.6% average GPU utilisation | 8 GB would run it at 2000 px |
| gsplat, 7,000 steps, 2000 px | 4.95 GB peak torch memory, 6.6 GB process memory | 12 GB is enough |
| Full resolution (6048 x 4032 class) | not measured | unknown; PatchMatch memory grows with image area |

Requirement: an NVIDIA GPU with at least 16 GB of VRAM and a CUDA 12 or CUDA 13 driver. 24 GB (RTX 4090, L4, A10, A5000) leaves room for a full-resolution run; 48 GB (L40S, A6000) removes the question. No Blackwell requirement: x86_64 and Ada or Ampere cards are enough, and the PyPI/conda wheels cover them.

Speed is the unknown. The GB10 took 30.8 s per view (1,168.7 s for 38 views at 2000 px, RC-P2). No rented card has been timed. Estimate: a 4090 or L40S runs 1x to 3x the GB10's rate, so 10 to 31 s per view; 425 views take 1.2 to 3.7 h. The first 20 views on the rented node replace this estimate with a measurement.

### CPU, RAM, disk

| Item | Requirement | Basis |
|---|---|---|
| vCPU | 8 or more | feature extraction, fusion and mapping run on the CPU |
| RAM | 32 GB minimum, 64 GB preferred | the dense run raised host memory by 10 GB on the GB10, gsplat by 13 GB (RC-P2); mapping a 400-image cluster needs more |
| Disk | 200 GB | archives 11.8 GB, extracted images about the same, dense workspace estimate below |

Dense workspace: RC-P2's 38-view workspace is 3.1 GB at 2000 px, 82 MB per view (undistorted image, photometric and geometric depth, normals, consistency graph). Estimate for 425 views: 35 GB; for all 1,273: 104 GB. Keep the 200 GB disk so a larger share fits without a restart.

### Network

The node pulls the images straight from the GitHub release, so the home uplink carries almost nothing.

| Transfer | Direction | Size (estimate) | Time |
|---|---|---|---|
| Graham Hall archives | GitHub to node | 11.8 GB [V] | minutes on a datacenter link |
| Slice list, camera database, sparse model, scripts | X3 to node | under 1 GB | seconds |
| Geometric depth maps for 425 views (float32, 2000 x 1295 is 10.4 MB each, uncompressed) | node to X3 | about 4.4 GB; about 13 GB for all 1,273 | 50 Mbit/s: 12 min (4.4 GB) or 35 min (13 GB); 500 Mbit/s: 1 to 3.5 min |
| Registration cluster model | node to X3 | under 1 GB | seconds |

The X3's real uplink and downlink are not measured; the times above are arithmetic on the stated link speeds. If the dense step returns normals and photometric maps as well, the download is about 3x larger. Return only the geometric depth maps and the fused slice.

### OS and image

- Ubuntu 22.04 or 24.04 on x86_64, NVIDIA driver with CUDA 12 or 13.
- Either a VM with root (Docker allowed), or a container pod. A VM runs `tailscaled` with a TUN device. A container pod usually has no TUN device and needs `tailscaled --tun=userspace-networking`, which makes the node reachable by SSH from the tailnet but not a route for other traffic `[unverified]`.
- Software: pycolmap with CUDA (RC-P1 and RC-P2 used conda-forge `pycolmap=4.2.1`, `has_cuda` True, on aarch64). Whether the x86_64 conda-forge build of the same version has a CUDA variant, and whether the `colmap/colmap` Docker image matches that version, are `[unverified]`; the first launch step checks `pycolmap.has_cuda`.

### Hours

| Phase | Estimate |
|---|---|
| Boot, Tailscale, environment, dataset download and extraction | 0.5 to 1 h |
| Dense depth, 425 views | 1.2 to 3.7 h (section above) |
| Registration cluster (SIFT, exhaustive match, mapping, about 400 images) | 0.2 to 0.5 h; RC-P1 matched 38 images in 5 to 10 s and matching scales with pairs, so 400 images is about 100x; mapping scales worse |
| Transfer back and checks | 0.2 to 0.5 h |
| Total | 2 to 5 h; plan 5 h |

### Access pattern

SSH from the X3. Preferred: the node joins the owner's tailnet with an ephemeral, tagged auth key and the X3 reaches it by its tailnet name; no public SSH port is exposed. Fallback: plain SSH to the provider's public IP with a key, restricted to the X3's address where the provider has a firewall. The coordinator on the X3 pushes work over SSH and pulls results with `rsync`.

## 2. Provider comparison

Prices as of 2026-11-24, in the provider's currency, on-demand, one GPU, Linux, excluding VAT unless stated.

| Provider | Relevant GPUs and price per hour | Billing | Egress | Storage | Custom image / Docker | Spot | EU region | Sign-up |
|---|---|---|---|---|---|---|---|---|
| RunPod ([pricing](https://www.runpod.io/pricing)) | Community / Secure [V]: RTX 4090 $0.34 / $0.89; L4 $0.44 / $0.69; L40S $0.79 / $1.09; A100 PCIe $1.19 / $2.09; H100 PCIe $1.99 / $2.89; A5000 $0.16 / $0.27; A6000 $0.33 / $0.69 | per second [V] | none: "no fees for data ingress or egress" ([docs](https://docs.runpod.io/pods/pricing)) [V] | container disk $0.10/GB/mo; volume $0.10 running, $0.20 stopped; network volume $0.07 under 1 TB [V] | pods are containers from any image; Docker inside a pod is not available `[unverified]` | not in the docs read [V]; a spot tier exists on the console `[unverified]` | datacenters in EU `[unverified]` | prepaid credit, balance zero stops pods; default $80/h spend limit [V] |
| Vast.ai ([pricing](https://vast.ai/pricing)) | marketplace; per-host prices. The RTX 4090 page showed no offers at fetch time ([page](https://vast.ai/pricing/gpu/RTX-4090)) [V]; "from $0.309" is a search snippet `[unverified]` | per second [V] | charged per byte, rate set by host, not stated on the pricing page ([docs](https://docs.vast.ai/documentation/instances/pricing)) [V] | charged while stopped; delete the instance to stop it [V] | Docker image template, container instances [V] | interruptible, "often 50%+ cheaper" [V] | filter by host country `[unverified]` | prepaid credit |
| Lambda ([pricing](https://lambda.com/pricing)) | A6000 $1.09; A100 $1.99; GH200 $2.59; H100 SXM $4.89; no 4090 or L40S listed [V] | one-minute increments ([docs](https://docs.lambda.com/public-cloud/billing/)) [V] | none: "you are not charged for ingress or egress" [V] | filesystem billed per GiB-month in one-hour increments, "$0.20 per GiB per month" given as an example, not a current price [V] | VMs with SSH; Docker preinstalled `[unverified]` | none seen `[unverified]` | `europe-central-1`, Germany ([docs](https://docs.lambda.com/public-cloud/on-demand/)) [V]; capacity per region not checked | card; instance quota and capacity availability `[unverified]` |
| DigitalOcean GPU Droplets (Paperspace's GPU line; [pricing](https://www.digitalocean.com/pricing/gpu-droplets)) | RTX 4000 Ada $0.76; RTX 6000 Ada $1.57; L40S $1.57; H100 $4.41 [V] | per second, five-minute minimum [V]; powered-off droplets still bill [V] | `[unverified]` | `[unverified]` | VM with SSH, GPU-ready images `[unverified]` | spot and 12-month reserved listed [V] | EU GPU region `[unverified]` | account with card; GPU access may need approval `[unverified]` |
| Hetzner GPU servers ([matrix](https://www.hetzner.com/dedicated-rootserver/matrix-gpu/)) | GEX45 RTX PRO 4000 24 GB: EUR 0.34 plus EUR 209 setup; GEX63 RTX PRO 6000 96 GB: EUR 1.60 plus EUR 999 setup; GEX131: EUR 2.40 plus EUR 1,499 setup [V] | hourly, with a one-off setup fee [V] | unlimited traffic included [V] | local disks `[unverified]` | Ubuntu, Debian installed on dedicated hardware [V] | none | Helsinki; Falkenstein for GEX131 [V] | the setup fee makes a few-hour run cost EUR 209 or more; not suitable |
| Google Cloud ([pricing](https://cloud.google.com/products/compute/pricing/accelerator-optimized)) | g2-standard-8 (1x L4, 24 GB, 8 vCPU, 32 GiB): $0.8536; a2-highgpu-1g (1x A100 40 GB, 12 vCPU, 85 GiB): $3.673 [V]. The first price column of the page is quoted; the region of each column was not extracted `[unverified]` | per second, one-minute minimum `[unverified]` | `[unverified]` | `[unverified]` | custom images and Docker supported `[unverified]` | Spot VMs listed; spot value on the page for a2-highgpu-1g is $2.00 in the second column `[unverified]` | `europe-west4` is listed for G2 ([search result](https://cloud.google.com/compute/gpus-pricing)) `[unverified]` | GPU quota starts at zero and needs a request `[unverified]` |
| AWS ([price list, eu-north-1](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20261123171005/eu-north-1/index.json)) | Stockholm, Linux, shared [V]: g4dn.xlarge (T4 16 GB) $0.558; g6.xlarge (L4 24 GB, 4 vCPU, 16 GiB) $0.8536; g5.xlarge (A10G 24 GB) $1.067; g6.2xlarge (L4, 8 vCPU, 32 GiB) $1.0369; g6e.xlarge (L40S 48 GB, 4 vCPU, 32 GiB) $1.974 | per second, 60-second minimum ([page](https://aws.amazon.com/ec2/pricing/on-demand/)) [V] | 100 GB per month free to the internet; the per-GB price beyond it was not read [V] | EBS price not read `[unverified]` | AMIs, Deep Learning AMIs `[unverified]` | Spot exists `[unverified]` | Stockholm and Frankfurt in the price index [V] | GPU instance vCPU quota starts at zero and needs a request `[unverified]` |
| Azure ([retail price API](https://prices.azure.com/api/retail/prices)) | West Europe, Linux, pay-as-you-go [V]: NC4as_T4_v3 (T4 16 GB, 4 vCPU) $0.658; NV36ads_A10_v5 (A10 24 GB, 36 vCPU) $4.16; NC24ads_A100_v4 (A100 80 GB, 24 vCPU) $4.775 | per second `[unverified]` | `[unverified]` | `[unverified]` | custom images supported `[unverified]` | Spot VMs exist `[unverified]` | West Europe [V] | GPU quota request `[unverified]` |
| Scaleway ([pricing](https://www.scaleway.com/en/pricing/gpu)) | L4-1-24G EUR 0.79; L40S-1-48G EUR 1.40; H100-1-80G EUR 2.52 `[unverified]` (search snippet of the pricing page; the page returned 403 to the fetch tool). `H100-1-80G` and `H100-SXM` types exist in the public product API for `fr-par-2` [V] | per minute `[unverified]` | `[unverified]` | `[unverified]` | VMs with SSH; Docker `[unverified]` | none seen `[unverified]` | Paris and Warsaw `[unverified]` | EU company, card; GPU quota `[unverified]` |
| OVHcloud ([GPU page](https://www.ovhcloud.com/en/public-cloud/gpu/)) | L4, L40S, H100 offered; "from approximately $0.60/hour" for entry options; no per-GPU price read [V]; USD 200 trial credit for new accounts [V] | per hour (price page, [V]) | `[unverified]` | `[unverified]` | VMs, Docker `[unverified]` | none seen `[unverified]` | `[unverified]` | card, identity check `[unverified]` |
| Verda (formerly DataCrunch; [RTX PRO 6000 page](https://verda.com/rtx-pro-6000)) | RTX PRO 6000 96 GB: $3.04 on demand, $1.52 spot [V]; V100 16 GB $0.256 ([instances page](https://verda.com/gpu-instances)) [V]. A search snippet quoted $1.89 for the RTX PRO 6000 and L40S; it conflicts with the page and is not used | `[unverified]` | `[unverified]` | block storage and shared filesystems offered [V] | instance boots in about 30 s; console, CLI, Terraform, SkyPilot [V] | spot contracts [V] | European operator; datacenter locations `[unverified]` | self-service, no sales call [V] |
| Genesis Cloud | pricing page failed the TLS handshake in the fetch tool; nothing read | `[unverified]` | `[unverified]` | `[unverified]` | `[unverified]` | `[unverified]` | `[unverified]` | `[unverified]` |

Reading the table:

- Two providers charge no data transfer (RunPod, Lambda), which matters because the depth maps return to the X3: 4 to 13 GB each way costs nothing there.
- Hetzner's setup fee rules it out for a run of hours.
- AWS, Google Cloud and Azure cost 2x to 6x the marketplace price for comparable VRAM and add quota requests; they stay as the fallback when an organisation account is required.
- RunPod's Community versus Secure gap is 2.6x for the 4090 ($0.34 versus $0.89). Community hosts are third-party machines.

## 3. Recommendation

**Cheapest sensible: RunPod, RTX 4090 24 GB, Community Cloud, $0.34 per hour [V].** Per-second billing, no egress fee, any container image, 24 GB covers a full-resolution trial. Fall back to Secure Cloud at $0.89 per hour if the Community pod is slow to start or reclaimed. Cost for a 5-hour run:

| Item | Cost |
|---|---|
| Compute, 5 h at $0.34 | $1.70 (Secure: $4.45) |
| Disk, 200 GB container disk at $0.10/GB/month, about 6 h | about $0.17 |
| Egress and ingress | $0 |
| Total | about $2 (Secure: about $5) |

Cap: load $10 of prepaid credit and no more; the pod stops itself at a zero balance [V]. Teardown when the run ends regardless of the balance.

**More reliable: Scaleway L40S-1-48G, EUR 1.40 per hour `[unverified]`, Paris or Warsaw.** A full VM with root (TUN device, Docker, plain Tailscale), 48 GB of VRAM, an EU operator and EU data location. The price rests on a search snippet because the pricing page refused the fetch tool; the owner confirms it in the console before launch. If Scaleway's GPU quota or stock blocks the launch, AWS `g6e.xlarge` in `eu-north-1` (L40S, $1.974 per hour [V]) is the fallback with a verified price.

| Item | Cost |
|---|---|
| Compute, 5 h at EUR 1.40 | EUR 7.00 |
| Block storage, 200 GB for 6 h | under EUR 1 `[unverified]` |
| Egress | not read `[unverified]`; the depth maps are about 4 to 13 GB |
| Total | about EUR 8 |

Cap: EUR 20, set as a billing alert and enforced by deleting the instance at the 8-hour mark.

The cheap option gives the first measurement. The reliable one covers the case where Community hardware misbehaves (disk speed, reclaim) and distorts the wall-clock number P7 records.

## 4. Launch checklist

Owner actions are marked (owner). No account, key or resource is created by the agent.

1. **Account (owner).** Create the provider account (RunPod first). Use the email of record and turn on two-factor authentication.
2. **Payment (owner).** RunPod: add prepaid credit of $10. Scaleway: add a card and set a billing alert at EUR 20. Do not enable auto top-up.
3. **SSH key (owner).** Add the public key of the X3's `~/.ssh/id_ed25519.pub` in the provider console. The private key stays on the X3.
4. **Tailscale auth key (owner).** In the Tailscale admin console create an auth key that is **ephemeral**, **reusable off**, **pre-approved**, tagged (for example `tag:rental`), with an expiry of 24 h. The owner creates it and pastes it into the node shell; the agent never receives it, and it is never committed. Add an ACL entry that lets the X3 reach `tag:rental` and nothing in the other direction.
5. **Image.** RunPod: template `runpod/pytorch` with a CUDA 12.x tag (check the tag in the console), container disk 200 GB, GPU RTX 4090 Community. Scaleway: Ubuntu 24.04 GPU image with the NVIDIA driver, a 200 GB volume. Confirm with `nvidia-smi` that the driver reports CUDA 12 or 13.
6. **Join the tailnet (on the node).**
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up --auth-key="$TS_AUTHKEY" --hostname=recce-p7-rental --advertise-tags=tag:rental --ssh=false
   ```
   In a container pod with no TUN device: `tailscaled --tun=userspace-networking --socket=/tmp/tailscaled.sock &` then `tailscale --socket=/tmp/tailscaled.sock up ...` with the same flags. Check from the X3: `tailscale ping recce-p7-rental` and `ssh root@recce-p7-rental nvidia-smi`.
7. **Environment (on the node).** Install micromamba and create the P1 environment: `micromamba create -p ~/p7env -c conda-forge python=3.12 pycolmap=4.2.1 numpy`. Run `~/p7env/bin/python -c "import pycolmap; print(pycolmap.has_cuda)"`. If it prints `False`, stop and record it; do not build COLMAP by hand without asking (the node costs money while idle).
8. **Data.** On the node, pull the archives directly:
   ```bash
   mkdir -p ~/p7/graham && cd ~/p7/graham
   for f in graham-hall.zip graham-hall.z0{1..5}; do
     curl -fLO https://github.com/colmap/colmap/releases/download/3.11.1/$f; done
   zip -FF graham-hall.zip --out graham-hall-combined.zip && unzip -q graham-hall-combined.zip
   ```
   From the X3, send the slice list, scripts and sparse model: `rsync -avz --partial ~/.cache/recce/runs/p7/handoff/ root@recce-p7-rental:~/p7/handoff/`.
9. **Run.** Start the dense slice detached (`long-job` skill) and sample the GPU every 5 s as in RC-P2 (`sample_gpu.sh`). Time the first 20 views and compare with the 10 to 31 s per view estimate; if the rate is worse than the GB10's 30.8 s, stop and report before spending more hours.
10. **Pull results.** `rsync -avz --partial --info=progress2 root@recce-p7-rental:~/p7/out/ ~/.cache/recce/runs/p7/rental/`. Record the byte count and the elapsed time.
11. **Teardown.** Copy the results and the logs first, then delete the instance. RunPod: terminate the pod (a stopped pod with a volume still bills for the disk; stopped volume disk costs $0.20/GB/month [V]) and delete any network volume. Scaleway: delete the instance and its volumes and its flexible IP. The ephemeral Tailscale node disappears from the admin console after it goes offline; remove it by hand if it stays listed and revoke the auth key.
12. **Verify nothing keeps billing.** Provider console: instances list empty, volumes list empty, IP list empty; the balance on RunPod (or the cost view on Scaleway) checked again after one hour and shows no movement. Tailscale admin: no `tag:rental` machine, auth key revoked.

### What P7 records

| Measure | Where it comes from |
|---|---|
| Wall-clock per phase (boot, setup, download, dense depth, registration, return) | timestamps in the run log |
| Seconds per view on the rented GPU, against the GB10's 30.8 s and the X3's figure | first 20 views and the whole slice |
| Transfer time and bytes, each direction, with the measured X3 link speed | `rsync` summary |
| Billed cost: compute, storage, egress, from the provider's invoice or balance, not the estimate | console |
| Idle time between rental start and the first dense view | log timestamps |
| GPU name, driver, CUDA, pycolmap build, `has_cuda` | `nvidia-smi`, `pip`/`conda list` |
| The result against the fastest single machine, and the break-even set size if splitting does not pay (the brief's closing sentence of RC-P7) | RC-P7 results table |

## 5. Not covered

- **Real speed of any rented card.** No GPU in this note was timed on PatchMatch. The 10 to 31 s per view range is an assumption of 1x to 3x the GB10; it can be wrong in both directions.
- **Full-resolution memory.** RC-P2 measured 2000 px only. Graham Hall's pixel size is not on the dataset page, so the full-resolution VRAM and time are unknown.
- **x86_64 CUDA pycolmap.** Not checked that a CUDA build of pycolmap 4.2.1 exists for x86_64 on conda-forge, or that the `colmap/colmap` image matches it.
- **Prices not read on a provider page:** Vast.ai per-GPU prices (listing empty for the 4090 at fetch time), Scaleway (page returned 403; snippet only), OVHcloud per-GPU prices, Verda L40S and A100 prices (a snippet conflicts with the page), Genesis Cloud (TLS failure), and all of DigitalOcean's, Google Cloud's and Azure's egress and storage prices. Google Cloud's region per price column was not extracted.
- **Availability and stock.** Whether an RTX 4090 Community pod, a Scaleway L40S, a Lambda GPU in `europe-central-1` or a Hetzner server is free today was not checked; stock changes by the minute.
- **Quotas and sign-up friction.** GPU quota requests, identity checks and approval waits at Google Cloud, AWS, Azure, Scaleway and OVHcloud were not tested; no account was created.
- **Tailscale inside RunPod pods.** The userspace-networking route is the documented Tailscale mode for containers without TUN but was not run on RunPod.
- **Spot and interruptible reliability.** Reclaim rates were not measured; the plan avoids spot for the timed run.
- **The X3's internet uplink and downlink.** Not measured; every transfer time is arithmetic on a stated speed.
- **The X3 HIP path (RC-P2) and the GB10 schedule.** The split's other two machines are outside this note; the rented GPU's share depends on them.
- **Tax.** Prices exclude VAT unless the page said otherwise; the Lambda page states exclusion [V], the others were not checked.
