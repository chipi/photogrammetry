You are writing the debrief of one 3D reconstruction (run id `courtyard/full`): a short report a
person reads after the run, in plain words. Use only the tools you have. The scene frame is metres.

Write three sections, two to four claims each:

1. **What holds**: registration, reprojection, the regions seen best, the measured products.
2. **What is weak**: the regions that need photos, and why, from their metrics; anything the run
   does not know (scale, for example).
3. **What to shoot next**: up to three new photos, each tied to a weak region.

Rules:

- Every number in a claim must come from a tool result, and the claim lists it as a handle:
  the tool, the arguments you called it with, the field path in its result (dot-separated keys,
  list indices as numbers, `#` for the length of a list), and the value. A claim with no handle
  is allowed only if it has no number and says plainly that it is a judgement.
- Write a percentage as the share times 100 (a share of 0.377 is "38%").
- Say when a number was checked against the laser scan, which the field does not have.
- A claim about a region names it (`region`) and up to three photos that hold it (`photos`, names
  from `get_region`'s `images_seeing`).
- Place a label (`place_label`) on each region you call weak, at its `centre`, and a ghost camera
  (`place_camera`) for each new photo you propose, looking at the region's `centre`. Put the
  camera where the photographer can stand (`list_cameras` with the region id gives the cameras
  that already see it): near those cameras, on the side of the region's largest empty arc
  (`azimuth_gap`), at about the same height as them.

End with one JSON object and nothing after it:

```json
{
  "title": "...",
  "sections": [
    {
      "heading": "What holds",
      "claims": [
        {
          "text": "...",
          "region": "R021",
          "photos": ["dslr_images/DSC_0286.JPG"],
          "handles": [
            {"tool": "get_region", "args": {"run": "courtyard/full", "region_id": "R021"},
             "field": "median_triangulation_angle_deg", "value": 4.1}
          ]
        }
      ]
    }
  ]
}
```
