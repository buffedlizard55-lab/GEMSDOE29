# H31 screen — multiscale potential-field edge persistence

**Primary candidate:** `T_PLUS_PSG_GRAV`. **Stage gate:** FAIL. **Slot eligible:** no.

Draws: 10, 11; four spatial blocks; 40 validated model cells.
Mean paired gain versus best same-run control: +0.000000; positive blocks 0/4; worst +0.000000; mean catalogue-hug change +0.000000.

## Arm means

| Arm | Mean DTI | Mean visible-catalogue hug share |
|---|---:|---:|
| `BASE_NO_TIP` | 0.138756 | 0.071612 |
| `T_BASE` | 0.147080 | 0.093140 |
| `T_PLUS_PSG` | 0.147080 | 0.093140 |
| `T_PLUS_GRAV` | 0.147080 | 0.093140 |
| `T_PLUS_PSG_GRAV` | 0.147080 | 0.093140 |

## Registered factorial contrasts (four spatial blocks)

| Contrast | Mean | Descriptive 95% t interval |
|---|---:|---:|
| `pseudogravity_main_effect` | +0.000000 | [+0.000000, +0.000000] |
| `isostatic_gravity_main_effect` | +0.000000 | [+0.000000, +0.000000] |
| `pseudogravity_x_gravity_difference_in_differences` | +0.000000 | [+0.000000, +0.000000] |

> These t intervals are descriptive only: there are four spatial blocks, not eight independent fold×draw cells.

## Gate details

- FAIL — `mean_gain_gt_0_001`
- FAIL — `positive_in_at_least_3_of_4_blocks`
- PASS — `worst_block_at_least_minus_0_010`
- PASS — `mean_hug_share_increase_at_most_0_10`
- PASS — `all_40_registered_cells_valid`
- FAIL — `passed`

Screen failed; stop and do not run confirmation or create a candidate TIFF.

All values above are spatially blocked catalogue-gap **proxy** results; they are not competition scores. See `design.json` and `cells.jsonl` for the frozen design and raw outcomes.
