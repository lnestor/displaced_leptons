import awkward as ak
import numpy as np

MIN_DELTA_PHI = 1e-3
MIN_DETERMINANT = 0.1
MAX_JUMP = 20

def calculate(l1, l2, max_iterations=5):
    phi1_0 = phi1 = (l1["track_phi"] + 2 * np.pi) % (2 * np.pi) - np.pi
    phi2_0 = phi2 = (l2["track_phi"] + 2 * np.pi) % (2 * np.pi) - np.pi

    sin1, cos1 = np.sin(phi1), np.cos(phi1)
    sin2, cos2 = np.sin(phi2), np.cos(phi2)


    tan1 = -np.tan(l1["track_lambda"])
    tan2 = -np.tan(l2["track_lambda"])

    r1 = l1["pt"] / (l1["charge"] * l1["bField_z"])
    r2 = l2["pt"] / (l2["charge"] * l2["bField_z"])

    a = l2["track_vx"] - l1["track_vx"] + r1 * sin1 - r2 * sin2
    b = l2["track_vy"] - l1["track_vy"] - r1 * cos1 + r2 * cos2
    c1 = r2 * tan2**2
    c2 = -r1 * tan1**2
    d1 = -r1 * tan1 * tan2
    d2 = r2 * tan1 * tan2
    e1 = tan2 * (l2["track_vz"] - l1["track_vz"] - r2 * phi2 * tan2 + r1 * phi1 * tan1)
    e2 = tan1 * (l2["track_vz"] - l1["track_vz"] - r2 * phi2 * tan2 + r1 * phi1 * tan1)

    valid_poca = ak.ones_like(phi1, dtype=bool)
    converged = ak.zeros_like(phi1, dtype=bool)

    for i in range(max_iterations):
        sin1, cos1 = np.sin(phi1), np.cos(phi1)
        sin2, cos2 = np.sin(phi2), np.cos(phi2)

        a11 = r2 * (-sin2 * (a - r1 * sin1) + cos2 * (b + r1 * cos1) + c1)
        a22 = -r1 * (-sin1 * (a + r2 * sin2) + cos1 * (b - r2 * cos2) + c2)
        a12 = r2 * (-r1 * cos2 * cos1 - r1 * sin2 * sin1 + d1)
        a21 = -r1 * (r2 * cos2 * cos1 + r2 * sin2 * sin1 + d2)
        det = a11 * a22 - a12 * a21

        res1 = r2 * (cos2 * (a - r1 * sin1) + sin2 * (b + r1 * cos1) + c1 * phi2 + d1 * phi1 + e1)
        res2 = -r1 * (cos1 * (a + r2 * sin2) + sin1 * (b - r2 * cos2) + c2 * phi1 + d2 * phi2 + e2)

        delta_phi1 = (res2 * a11 - res1 * a21) / det
        delta_phi2 = (res1 * a22 - res2 * a12) / det

        valid_this_iter = (
            (a11 >= 0)
            & (a22 >= 0)
            & (abs(det) >= MIN_DETERMINANT)
            & np.isfinite(delta_phi1)
            & np.isfinite(delta_phi2)
        )
        valid_poca = valid_poca & (converged | valid_this_iter)

        phi1 = ak.where(valid_poca & ~converged, phi1 - delta_phi1, phi1)
        phi2 = ak.where(valid_poca & ~converged, phi2 - delta_phi2, phi2)

        converged = converged | ((abs(delta_phi1) < MIN_DELTA_PHI) & (abs(delta_phi2) < MIN_DELTA_PHI))

    valid_poca = (
        valid_poca
        & converged
        & (abs(r1 * (phi1 - phi1_0)) <= MAX_JUMP)
        & (abs(r2 * (phi2 - phi2_0)) <= MAX_JUMP)
    )

    p1 = ak.zip({
        "x": l1["track_vx"] + r1 * (np.sin(phi1) - np.sin(phi1_0)),
        "y": l1["track_vy"] + r1 * (-np.cos(phi1) + np.cos(phi1_0)),
        "z": l1["track_vz"] + r1 * tan1 * (phi1 - phi1_0)
    })

    p2 = ak.zip({
        "x": l2["track_vx"] + r2 * (np.sin(phi2) - np.sin(phi2_0)),
        "y": l2["track_vy"] + r2 * (-np.cos(phi2) + np.cos(phi2_0)),
        "z": l2["track_vz"] + r2 * tan2 * (phi2 - phi2_0)
    })

    return ak.mask(p1, valid_poca), ak.mask(p2, valid_poca)
