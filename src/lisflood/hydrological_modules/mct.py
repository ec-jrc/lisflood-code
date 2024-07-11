import numpy as np


def MCTRouting_single(
    V00, q10, q01, q00, ql, q0mm, Cm0, Dm0, dt, xpix, s0, Balv, ANalv, Nalv
):
    """
    This function implements Muskingum-Cunge-Todini routing method for a single pixel.
    References:
        Todini, E. (2007). A mass conservative and water storage consistent variable parameter Muskingum-Cunge approach. Hydrol. Earth Syst. Sci.
        (Chapter 5)
        Reggiani, P., Todini, E., & Meißner, D. (2016). On mass and momentum conservation in the variable-parameter Muskingum method. Journal of Hydrology, 543, 562–576. https://doi.org/10.1016/j.jhydrol.2016.10.030
        (Appendix B)

    :param V00: channel storage volume at t (beginning of computation step)
    :param q10: O(t) - outflow (x+dx) at time t
    :param q01: I(t+dt) - inflow (x) at time t+dt
    :param q00: I(t) - inflow (x) at time t
    :param ql: lateral flow over time dt [m3/s]
    :param q0mm: I - average inflow during step dt
    :param Cm0: Courant number at time t
    :param Dm0: Reynolds number at time t
    :param dt: time interval step
    :param xpix: channel length
    :param s0: channel slope
    :param Balv: channel bankfull width
    :param ANalv: angle of the riverbed side [rad]
    :param Nalv: channel Manning roughness coefficient
    :return:
    q11: Outflow (x+dx) at O(t+dt)
    V11: channel storage volume at t+dt
    Cm1: Courant number at t+1 for state file
    Dm1: Reynolds number at t+1 for state file
    """

    eps = 1e-06

    # Calc O' first guess for the outflow at time t+dt
    # O'(t+dt)=O(t)+(I(t+dt)-I(t))
    q11 = q10 + (q01 - q00)

    # check for negative and zero discharge values
    # zero outflow is not allowed
    if q11 < eps:  # cmcheck <=0
        q11 = eps

    # calc reference discharge at time t
    # qm0 = (I(t)+O(t))/2
    # qm0 = (q00 + q10) / 2.

    # Calc O(t+dt)=q11 at time t+dt using MCT equations
    for i in range(2):  # repeat 2 times for accuracy

        # reference I discharge at x=0
        qmx0 = (q00 + q01) / 2.0
        if qmx0 < eps:  # cmcheck ==0
            qmx0 = eps
        hmx0 = hoq(qmx0, s0, Balv, ANalv, Nalv)

        # reference O discharge at x=1
        qmx1 = (q10 + q11) / 2.0
        if qmx1 < eps:  # cmcheck ==0
            qmx1 = eps
        hmx1 = hoq(qmx1, s0, Balv, ANalv, Nalv)

        # Calc riverbed slope correction factor
        cor = 1 - (1 / s0 * (hmx1 - hmx0) / xpix)
        sfx = s0 * cor
        if sfx < (0.8 * s0):
            sfx = 0.8 * s0  # In case of instability raise from 0.5 to 0.8

        # Calc reference discharge time t+dt
        # Q(t+dt)=(I(t+dt)+O'(t+dt))/2
        qm1 = (q01 + q11) / 2.0
        # cm
        if qm1 < eps:  # cmcheck ==0
            qm1 = eps
        # cm
        hm1 = hoq(qm1, s0, Balv, ANalv, Nalv)
        dummy, Ax1, Bx1, Px1, ck1 = qoh(hm1, s0, Balv, ANalv, Nalv)
        if ck1 <= eps:
            ck1 = eps

        # Calc correcting factor Beta at time t+dt
        Beta1 = ck1 / (qm1 / Ax1)
        # calc corrected cell Reynolds number at time t+dt
        Dm1 = qm1 / (sfx * ck1 * Bx1 * xpix) / Beta1
        # corrected Courant number at time t+dt
        Cm1 = ck1 * dt / xpix / Beta1

        # Calc MCT parameters
        den = 1 + Cm1 + Dm1
        c1 = (-1 + Cm1 + Dm1) / den
        c2 = (1 + Cm0 - Dm0) / den * (Cm1 / Cm0)
        c3 = (1 - Cm0 + Dm0) / den * (Cm1 / Cm0)
        c4 = (2 * Cm1) / den

        # cmcheck
        # Calc outflow q11 at time t+1
        # Mass balance equation without lateral flow
        # q11 = c1 * q01 + c2 * q00 + c3 * q10
        # Mass balance equation that takes into consideration the lateral flow
        q11 = c1 * q01 + c2 * q00 + c3 * q10 + c4 * ql

        if q11 < eps:  # cmcheck <=0
            q11 = eps

        #### end of for loop

    # # cmcheck
    # calc_t = xpix / ck1
    # if calc_t < dt:
    #     print('xpix/ck1 < dt')

    # k1 = dt / Cm1
    # x1 = (1. - Dm1) / 2.

    # Calc the corrected mass-conservative expression for the reach segment storage at time t+dt
    # The lateral inflow ql is only explicitly accounted for in the mass balance equation, while it is not in the equation expressing
    # the storage as a weighted average of inflow and outflow.The rationale of this approach lies in the fact that the outflow
    # of the reach implicitly takes the  effect of the lateral inflow into account.
    if q11 == 0:
        V11 = V00 + (q00 + q01 - q10 - q11) * dt / 2
    else:
        V11 = (1 - Dm1) * dt / (2 * Cm1) * q01 + (1 + Dm1) * dt / (2 * Cm1) * q11
        # V11 = k1 * (x1 * q01 + (1. - x1) * q11) # MUST be the same as above!

    ### calc integration on the control volume (pixel)
    # calc average discharge outflow q1m for MCT channels during routing sub step dt
    # Calculate average outflow using water balance for MCT channel grid cell over sub-routing step
    q1mm = q0mm + ql + (V00 - V11) / dt

    # cmcheck
    # q1m cannot be smaller than eps or it will cause instability
    if q1mm < eps:
        q1mm = eps
        V11 = V00 + (q0mm + ql - q1mm) * dt

    # q11 Outflow at O(t+dt)
    # q1m average outflow in time dt
    # V11 water volume at t+dt
    # Cm1 Courant number at t+dt for state files
    # Dm1 Reynolds numbers at t+dt for state files
    return q11, q1mm, V11, Cm1, Dm1


def hoq(q, s0, Balv, ANalv, Nalv):
    """Water depth h from discharge q.
    Given a generic cross-section (rectangular, triangular or trapezoidal) and a steady-state discharge q=Q*, it computes
    water depth (y), wet contour (Bx), wet area (Ax) and wave celerity (cel) using Newton-Raphson method.
    Reference:
    Reggiani, P., Todini, E., & Meißner, D. (2016). On mass and momentum conservation in the variable-parameter Muskingum method.
    Journal of Hydrology, 543, 562–576. https://doi.org/10.1016/j.jhydrol.2016.10.030

    :param q: steady-state river discharge [m3/s]
    :param s0: river bed slope (tan B)
    :param Balv : width of the riverbed [m]
    :param ChanSdXdY : slope dx/dy of riverbed side
    :param ANalv : angle of the riverbed side [rad]
    :param Nalv : channel mannings coefficient n for the riverbed [s/m1/3]

    :return:
    y: water depth referred to the bottom of the riverbed [m]
    """

    alpha = 5.0 / 3.0  # exponent (5/3)
    eps = 1.0e-06
    max_tries = 1000

    rs0 = np.sqrt(s0)
    usalpha = 1.0 / alpha

    # cotangent(angle of the riverbed side - dXdY)
    if ANalv < np.pi / 2:
        # triangular or trapezoid cross-section
        c = cotan(ANalv)
    else:
        # rectangular corss-section
        c = 0.0

    # sin(angle of the riverbed side - dXdY)
    if ANalv < np.pi / 2:
        # triangular or trapezoid cross-section
        s = np.sin(ANalv)
    else:
        # rectangular cross-section
        s = 1.0

    # water depth first approximation y0 based on steady state q
    if Balv == 0:
        # triangular cross-section
        y = (Nalv * q / rs0) ** (3.0 / 8.0) * (2 / s) ** 0.25 / c ** (5.0 / 8.0)
    else:
        # rectangular cross-section and first approx for trapezoidal cross-section
        y = (Nalv * q / (rs0 * Balv)) ** usalpha

    if (Balv != 0) and (ANalv < np.pi / 2):
        # trapezoid cross-section
        y = (Nalv * q / rs0) ** usalpha * (Balv + 2.0 * y / s) ** 0.4 / (Balv + c * y)

    for tries in range(1, max_tries):
        # calc Q(y) for the different tries of y
        q0, Ax, Bx, Px, cel = qoh(y, s0, Balv, ANalv, Nalv)
        # Ax: wet area[m2]
        # Bx: cross-section width at water surface[m]
        # Px: cross-section wet contour [m]
        # cel: wave celerity[m/s]

        # this is the function we want to find the 0 for f(y)=Q(y)-Q*
        fy = q0 - q
        # calc first derivative of f(y)  f'(y)=Bx(y)*cel(y)
        dfy = Bx * cel
        # calc update for water depth y
        dy = fy / dfy
        # update yt+1=yt-f'(yt)/f(yt)
        y = y - dy
        # stop loop if correction becomes too small
        if np.abs(dy) < eps:
            break

    return y


def qoh(y, s0, Balv, ANalv, Nalv):
    """Discharge q from water depth h.
    Given a generic river cross-section (rectangular, triangular and trapezoidal)
    and a water depth (y [m]) referred to the bottom of the riverbed, it uses Manning’s formula to calculate:
    q: steady-state discharge river discharge [m3/s]
    a: wet area [m2]
    b: cross-section width at water surface [m]
    p: cross-section wet contour [m]
    cel: wave celerity [m/s]
    Reference: Reggiani, P., Todini, E., & Meißner, D. (2016). On mass and momentum conservation in the variable-parameter Muskingum method. Journal of Hydrology, 543, 562–576. https://doi.org/10.1016/j.jhydrol.2016.10.030

    :param y: river water depth [m]
    :param s0: river bed slope (tan B)
    :param Balv : width of the riverbed [m]
    :param ANalv : angle of the riverbed side [rad]
    :param Nalv : channel mannings coefficient n for the riverbed [s/m1/3]

    :return:
    q,a,b,p,cel
    """

    alpha = 5.0 / 3.0  # exponent (5/3)

    rs0 = np.sqrt(s0)
    alpham = alpha - 1.0

    # np.where(ANalv < np.pi/2, triang. or trapeiz., rectangular)
    # cotangent(angle of the riverbed side - dXdY)
    c = np.where(
        ANalv < np.pi / 2,
        # triangular or trapezoid cross-section
        cotan(ANalv),
        # rectangular cross-section
        0.0,
    )
    # sin(angle of the riverbed side - dXdY)
    s = np.where(
        ANalv < np.pi / 2,
        # triangular or trapezoid cross-section
        np.sin(ANalv),
        # rectangular corss-section
        1.0,
    )

    a = (Balv + y * c) * y  # wet area [m2]
    b = Balv + 2.0 * y * c  # cross-section width at water surface [m]
    p = Balv + 2.0 * y / s  # cross-section wet contour [m]
    q = rs0 / Nalv * a**alpha / p**alpham  # steady-state discharge [m3/s]
    cel = (q / 3.0) * (5.0 / a - 4.0 / (p * b * s))  # wave celerity [m/s]

    return q, a, b, p, cel


def hoV(V, xpix, Balv, ANalv):
    """Water depth h from volume V.
    Given a generic river cross-section (rectangular, triangular and trapezoidal) and a river channel volume V,
    it calculates the water depth referred to the bottom of the riverbed [m] (y).
    Reference: Reggiani, P., Todini, E., & Meißner, D. (2016). On mass and momentum conservation in the variable-parameter Muskingum method. Journal of Hydrology, 543, 562–576. https://doi.org/10.1016/j.jhydrol.2016.10.030

    :param V : volume of water in channel riverbed
    :param xpix : dimension along the flow direction  [m]
    :param Balv : width of the riverbed [m]
    :param ANalv : angle of the riverbed side [rad]

    :return:
    y : channel water depth [m]
    """
    eps = 1e-6

    c = np.where(
        ANalv < np.pi / 2,  # angle of the riverbed side dXdY [rad]
        cotan(ANalv),  # triangular or trapezoidal cross-section
        0.0,
    )  # rectangular cross-section

    a = V / xpix  # wet area [m2]

    # np.where(c < 1.d-6, rectangular, triangular or trapezoidal)
    y = np.where(
        np.abs(c) < eps,
        a / Balv,  # rectangular cross-section
        (-Balv + np.sqrt(Balv**2 + 4 * a * c)) / (2 * c),
    )  # triangular or trapezoidal cross-section

    return y


def qoV(V, xpix, s0, Balv, ANalv, Nalv):
    """Discharge q from river channel volume V.
    Given a generic river cross-section (rectangular, triangular and trapezoidal)
    and a water volume (V [m3]), it uses Manning’s formula to calculate the corresponding discharge (q [m3/s]).
    Reference: Reggiani, P., Todini, E., & Meißner, D. (2016). On mass and momentum conservation in the variable-parameter Muskingum method. Journal of Hydrology, 543, 562–576. https://doi.org/10.1016/j.jhydrol.2016.10.030

    :param V : volume of water in channel riverbed
    :param xpix : dimension along the flow direction  [m]
    :param s0: river bed slope (tan B)
    :param Balv : width of the riverbed [m]
    :param ANalv : angle of the riverbed side [rad]
    :param Nalv : channel mannings coefficient n for the riverbed [s/m1/3]

    :return:
    y : channel water depth [m]
    """
    y = hoV(V, xpix, Balv, ANalv)
    q, a, b, p, cel = qoh(y, s0, Balv, ANalv, Nalv)
    return q


def cotan(x):
    """There is no cotangent function in numpy"""
    return np.cos(x) / np.sin(x)


def rad_from_dxdy(dxdy):
    """Calculate radians"""
    rad = np.arctan(1 / dxdy)
    # angle = np.rad2deg(rad)
    return rad
