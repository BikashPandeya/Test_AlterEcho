import numpy as np
import pytest

from app.services.terrain_service import calculate_local_relief, calculate_roughness, calculate_slope, physical_window_pixels


def test_flat_raster_has_zero_slope_and_relief():
    raster = np.full((7, 7), 42.0)
    assert np.nanmax(calculate_slope(raster, 10, 10)) == pytest.approx(0)
    assert np.nanmax(calculate_local_relief(raster, 3)) == pytest.approx(0)
    assert np.nanmax(calculate_roughness(raster, 3)) == pytest.approx(0)


def test_plane_has_expected_slope():
    x = np.arange(7) * 10.0
    raster = np.tile(x, (7, 1))
    assert np.nanmedian(calculate_slope(raster, 10, 10)) == pytest.approx(45.0)


def test_nodata_mask_is_preserved():
    raster = np.arange(25, dtype=float).reshape(5, 5)
    mask = np.ones_like(raster, dtype=bool)
    mask[2, 2] = False
    assert np.isnan(calculate_slope(raster, 1, 1, mask)[2, 2])
    assert np.isnan(calculate_local_relief(raster, 3, mask)[2, 2])


def test_hill_has_relief_and_roughness_and_physical_window_is_odd():
    y, x = np.mgrid[-5:6, -5:6]
    hill = 100 * np.exp(-(x * x + y * y) / 12)
    assert np.nanmax(calculate_local_relief(hill, 5)) > 0
    assert np.nanmax(calculate_roughness(hill, 5)) > 0
    assert physical_window_pixels(1000, 60) == 17

