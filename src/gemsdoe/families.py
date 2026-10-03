"""Feature-family registry for the fractional factorial design (single source of truth).

The five factors follow the owner's brief ("candidate feature families already identified"):

A  potential-field gradients   gravity + magnetics (gradients, tilt, analytic signal, ridge worms)
B  DEM curvature / scarp       detrended elevation (+100 m curvature/TPI/relief) and 3DEP-LiDAR scarp descriptors
C  strain / seismicity         geodetic strain-rate invariants + earthquake density bands
D  thermal / geochemical       radiometrics (tc, K, Th, U and ratios), conductivity, GDR 1391 springs / wells
E  catalogue geometry          distance / orientation / density of the VISIBLE known faults only

Assignment decisions are working interpretations, not verified band semantics (see ``registry/irregularities.json``):
* ``tc`` is placed in D based on a predecessor-reported internal correlation with USGS GeoDAWN total-count radiometrics (Spearman 0.9999), although the raster's embedded description reportedly calls it a magnetic tilt/curvature derivative. GEMSDOE29 has not recomputed that correlation.
* ``cond_surf`` / ``depth_to_base_surf`` (MT conductance model) are placed in D as fluid / clay-alteration
  proxies; the brief names no family for them.
"""

from __future__ import annotations

FAMILIES = {
    "A": dict(
        name="potential_field_gradients",
        label="Potential-field gradients (gravity + magnetics)",
        base=[
            "mag_anom", "rtp", "tmi", "tmi_hg", "tmi_vg",
            "iso_grav_anom", "iso_grav_anom_slope", "iso_grav_anom_hg", "iso_grav_anom_vg",
        ],
        derived=[
            "A_mag_as", "A_mag_tilt", "A_grav_as", "A_grav_tilt",
            "A_mag_hg_ridge", "A_grav_hg_ridge", "A_mag_hg_ctx",
        ],
    ),
    "B": dict(
        name="dem_curvature_scarp",
        label="DEM curvature / scarp (100 m DEM + 3DEP LiDAR descriptors)",
        base=["det_elev", "det_elev_slope"],
        derived=[
            "B_lap1", "B_lap2", "B_tpi5", "B_tpi11", "B_relief5", "B_slope_grad",
            "B_crest", "B_trough", "B_slope_ctx",
            "L_ex_max", "L_ex_mean", "L_step_max", "L_lapneg_max", "L_lappos_max",
            "L_downface_max", "L_upface_max", "L_cross_max", "L_relief", "L_coh100",
            "L_strike_c2", "L_strike_s2", "L_valid",
        ],
    ),
    "C": dict(
        name="strain_seismicity",
        label="Strain rate / seismicity",
        base=["geod_2ndinv", "geod_shearrate", "geod_dilaterate", "deq_n100a15", "ieq_n100a15"],
        derived=["C_2ndinv_grad", "C_shear_grad"],
    ),
    "D": dict(
        name="thermal_geochemical",
        label="Thermal / geochemical (radiometrics, conductivity, GDR 1391 springs & wells)",
        base=["tc", "cond_surf", "depth_to_base_surf"],
        derived=[
            "D_cond_grad", "D_depth_base_grad",
            "D_K", "D_Th", "D_U", "D_ThK", "D_UK", "D_UTh", "D_ThK_edge", "D_UK_edge",
            "D_gdr_dist_hot", "D_gdr_kde2km", "D_gdr_tmax5km", "D_gdr_quartz5km",
        ],
    ),
    "E": dict(
        name="catalogue_geometry",
        label="Catalogue geometry (visible known faults only)",
        base=[],
        derived=["E_dist", "E_cos2", "E_sin2", "E_dens5", "E_dens20", "E_dens50", "E_coh20"],
    ),
}
FACTORS = ["A", "B", "C", "D", "E"]


def family_columns(letter: str) -> list[str]:
    f = FAMILIES[letter]
    return list(f["base"]) + list(f["derived"])
