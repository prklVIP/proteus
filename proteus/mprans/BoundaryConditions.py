#cython: profile=True
#cython: wraparound=False
#cython: boundscheck=False
#cython: initializedcheck=False

import cython

"""
Module for creating boundary conditions. Imported in mprans.SpatialTools.py
"""
import sys
import numpy as np
from proteus import AuxiliaryVariables
from proteus.ctransportCoefficients import (smoothedHeaviside,
                                            smoothedHeaviside_integral)
from proteus import WaveTools as wt

class BC_RANS(BC_Base):
    """
    Class regrouping boundary conditions for two-phase flows
    """
    def __init__(self, shape=None, name=None, b_or=None, b_i=0., nd=None):
        super(BC_RANS, self).__init__(shape=shape, name=name, b_or=b_or, b_i=b_i, nd=nd)
        # _dirichlet
        self.p_dirichlet = BoundaryCondition()  # pressure
        self.u_dirichlet = BoundaryCondition()  # velocity u
        self.v_dirichlet = BoundaryCondition()  # velocity v
        self.w_dirichlet = BoundaryCondition()  # velocity w
        self.vof_dirichlet = BoundaryCondition()  # VOF
        self.k_dirichlet = BoundaryCondition()  # kappa
        self.dissipation_dirichlet = BoundaryCondition()  # dissipation
        # _advective
        self.p_advective = BoundaryCondition()
        self.u_advective = BoundaryCondition()
        self.v_advective = BoundaryCondition()
        self.w_advective = BoundaryCondition()
        self.vof_advective = BoundaryCondition()
        self.k_advective = BoundaryCondition()
        self.dissipation_advective = BoundaryCondition()
        # _diffusive
        self.u_diffusive = BoundaryCondition()
        self.v_diffusive = BoundaryCondition()
        self.w_diffusive = BoundaryCondition()
        self.k_diffusive = BoundaryCondition()
        self.dissipation_diffusive = BoundaryCondition()
        # moveMesh boundary conditions
        self.hx_dirichlet = BoundaryCondition()
        self.hy_dirichlet = BoundaryCondition()
        self.hz_dirichlet = BoundaryCondition()
        self.u_stress = BoundaryCondition()
        self.v_stress = BoundaryCondition()
        self.w_stress = BoundaryCondition()
        self.u_stress.uOfXT = 0.
        self.v_stress.uOfXT = 0.
        self.w_stress.uOfXT = 0.

    def reset(self):
        """
        Resets all BoundaryCondtion functions to None, apart from the BCs
        affecting: moving mesh
        """
        # self.BC_type = 'None'
        self.p_dirichlet.resetBC()
        self.u_dirichlet.resetBC()
        self.v_dirichlet.resetBC()
        self.w_dirichlet.resetBC()
        self.vof_dirichlet.resetBC()
        self.k_dirichlet.resetBC()
        self.dissipation_dirichlet.resetBC()
        self.p_advective.resetBC()
        self.u_advective.resetBC()
        self.v_advective.resetBC()
        self.w_advective.resetBC()
        self.vof_advective.resetBC()
        self.k_advective.resetBC()
        self.dissipation_advective.resetBC()
        self.u_diffusive.resetBC()
        self.v_diffusive.resetBC()
        self.w_diffusive.resetBC()
        self.k_diffusive.resetBC()
        self.dissipation_diffusive.resetBC()

    def setNonMaterial(self):
        """
        Sets non-material boundary conditions (diffusive flux and advective vof
        to 0.).
        """
        self.reset()
        self.BC_type = 'NonMaterial'
        self.vof_advective.setConstantBC(0.)
        self.u_diffusive.setConstantBC(0.)
        self.v_diffusive.setConstantBC(0.)
        self.w_diffusive.setConstantBC(0.)

    def setTank(self):
        b_or = self._b_or
        if b_or[0] == 1 or b_or[0] == -1:
            self.hx_dirichlet.setConstantBC(0.)
            self.u_stress.uOfXT = None
        elif b_or[1] == 1 or b_or[1] == -1:
            self.hy_dirichlet.setConstantBC(0.)
            self.v_stress.uOfXT = None
        elif len(b_or) > 2 and (b_or[2] == 1 or b_or[2] == -1):
            self.hz_dirichlet.setConstantBC(0.)
            self.w_stress.uOfXT = None

    def setFixedNodes(self):
        """
        For moving domains: fixes nodes/boundary
        """
        self.hx_dirichlet.setConstantBC(0.)
        self.hy_dirichlet.setConstantBC(0.)
        self.hz_dirichlet.setConstantBC(0.)
        self.u_stress.uOfXT = 0
        self.v_stress.uOfXT = 0
        self.w_stress.uOfXT = 0

    def setNoSlip(self):
        """
        Sets no slip conditions at the boundary
        """
        self.reset()
        self.BC_type = 'NoSlip'
        self.u_dirichlet.setConstantBC(0.)
        self.v_dirichlet.setConstantBC(0.)
        self.w_dirichlet.setConstantBC(0.)
        self.p_advective.setConstantBC(0.)
        self.vof_advective.setConstantBC(0.)
        self.k_dirichlet.setConstantBC(0.)
        self.dissipation_diffusive.setConstantBC(0.)

    def setFreeSlip(self):
        """
        Sets free slip conditions at the boundary
        """
        self.reset()
        self.BC_type = 'FreeSlip'
        self.p_advective.setConstantBC(0.)
        self.u_advective.setConstantBC(0.)
        self.v_advective.setConstantBC(0.)
        self.w_advective.setConstantBC(0.)
        self.vof_advective.setConstantBC(0.)
        self.k_dirichlet.setConstantBC(0.)
        self.u_diffusive.setConstantBC(0.)
        self.v_diffusive.setConstantBC(0.)
        self.w_diffusive.setConstantBC(0.)
        self.dissipation_diffusive.setConstantBC(0.)

    def setAtmosphere(self, orientation=None, vof_air=1.):
        """
        Sets atmosphere boundary conditions (water can come out)
        (!) pressure dirichlet set to 0 for this BC

        Parameters
        ----------
        orientation: Optional[array_like]
            orientation of the boundary. Optional if orientation was already
            passed when creating the BC_RANS class instance.
        vof_air: Optional[float]
            VOF value of air (default is 1.)
        """
        self.BC_type = 'OpenAir'
        if orientation is None and self._b_or is not None:
            orientation = self._b_or
        self.reset()
        self.p_dirichlet.setConstantBC(0.)
        if self._b_or[0] == 1. or self._b_or[0] == -1.:
            self.u_dirichlet.setConstantBC(0.)
        else:
            self.u_dirichlet.resetBC()
        if self._b_or[1] == 1. or self._b_or[1] == -1.:
            self.v_dirichlet.setConstantBC(0.)
        else:
            self.v_dirichlet.resetBC()
        if self._b_or[2] == 1. or self._b_or[2] == -1.:
            self.w_dirichlet.setConstantBC(0.)
        else:
            self.w_dirichlet.resetBC()
        self.vof_dirichlet.setConstantBC(vof_air)  # air
        self.u_diffusive.setConstantBC(0.)
        self.v_diffusive.setConstantBC(0.)
        self.w_diffusive.setConstantBC(0.)
        self.k_diffusive.setConstantBC(0.)
        self.dissipation_diffusive.setConstantBC(0.)



    def setMoveMesh(self, last_pos, h=(0., 0., 0.), rot_matrix=None):
        """
        Sets boundary conditions for moving the mesh with a rigid body

        Parameters
        ----------
        last_pos: array_like
            last position of rigig body
        h: array_like
            displacement of the body
        rot_matrix:
            rotation matrix describing displament due to rotation between last
            position and new position (3x3 array)

        (!) if set manually, the input arrays should be updated externally
            without loosing their memory address
        """
        if rot_matrix is None:
            rot_matrix = np.array([[1., 0., 0.],
                                   [0., 1., 0.],
                                   [0., 0., 1.]])
        self.body_python_rot_matrix = rot_matrix
        self.body_python_last_pos = last_pos
        self.body_python_h = h
        self.hx_dirichlet.uOfXT = lambda x, t: self.__cpp_MoveMesh_hx(x, t)
        self.hy_dirichlet.uOfXT = lambda x, t: self.__cpp_MoveMesh_hy(x, t)
        self.hz_dirichlet.uOfXT = lambda x, t: self.__cpp_MoveMesh_hz(x, t)

    def __cpp_MoveMesh_h(self, x, t):
        x_0 = cython.declare(cython.double[3]) 
        new_x_0 = cython.declare(cython.double[3]) 
        hx = cython.declare(cython.double[3]) 
        x_0[0] = x[0]-self.body_python_last_pos[0]
        x_0[1] = x[1]-self.body_python_last_pos[1]
        x_0[2] = x[2]-self.body_python_last_pos[2]
        new_x_0 = np.dot(x_0, self.body_python_rot_matrix)
        hx[0] = new_x_0[0]-x_0[0]+self.body_python_h[0]
        hx[1] = new_x_0[1]-x_0[1]+self.body_python_h[1]
        hx[2] = new_x_0[2]-x_0[2]+self.body_python_h[2]
        return hx

    def __cpp_MoveMesh_hx(self, x, t):
        return self.__cpp_MoveMesh_h(x, t)[0]

    def __cpp_MoveMesh_hy(self, x, t):
        return self.__cpp_MoveMesh_h(x, t)[1]

    def __cpp_MoveMesh_hz(self, x, t):
        return self.__cpp_MoveMesh_h(x, t)[2]

    def setUnsteadyTwoPhaseVelocityInlet(self, wave, vert_axis=None, wind_speed=None,
                                         smoothing=0., vof_air=1., vof_water=0.):
        """
        Imposes a velocity profile on the fluid with input wave and wind
        conditions.

        Parameters
        ----------
        wave: proteus.WaveTools
            class describing a wave (from proteus.WaveTools)
        vert_axis: Optional[int]
            index of vertical position vector (x:0, y:1, z:2), must always be
            aligned with gravity. If not set, will be 1 in 2D (y), 2 in 3D (z).
        wind_speed: Optional[array_like]
        vof_air: Optional[float]
            VOF value of air (default is 1.)
        vof_water: Optional[float]
            VOF value of water (default is 0.)

        Below the sea water level: fluid velocity to wave speed.
        Above the sea water level: fluid velocity set to wind speed.
        (!) Boundary condition relies on specific variables defined in Context:
            he (mesh element size) and ecH (number of elements for smoothing)
        """
        self.reset()
        if vert_axis is None:
            vert_axis = self.nd-1
        if wind_speed is None:
            wind_speed = np.zeros(3)
        self.waves = __cppClass_WavesCharacteristics(waves=wave, vert_axis=vert_axis, b_or=self._b_or, wind_speed=wind_speed, smoothing=smoothing, vof_water=vof_water, vof_air=vof_air)
        self.u_dirichlet.uOfXT = lambda x, t: self.__cpp_UnsteadyTwoPhaseVelocityInlet_u_dirichlet(x, t)
        self.v_dirichlet.uOfXT = lambda x, t: self.__cpp_UnsteadyTwoPhaseVelocityInlet_v_dirichlet(x, t)
        self.w_dirichlet.uOfXT = lambda x, t: self.__cpp_UnsteadyTwoPhaseVelocityInlet_w_dirichlet(x, t)
        self.vof_dirichlet.uOfXT = lambda x, t: self.__cpp_UnsteadyTwoPhaseVelocityInlet_vof_dirichlet(x, t)
        self.p_advective.uOfXT = lambda x, t: self.__cpp_UnsteadyTwoPhaseVelocityInlet_p_advective(x, t)

    def __cpp_UnsteadyTwoPhaseVelocityInlet_u_dirichlet(self, x, t):
        cython.declare(xx=cython.double[3])
        xx[0] = x[0]
        xx[1] = x[1]
        xx[2] = x[2]
        return self.waves.__cpp_calculate_velocity(xx, t)[0]
    def __cpp_UnsteadyTwoPhaseVelocityInlet_v_dirichlet(self, x, t):
        cython.declare(xx=cython.double[3])
        xx[0] = x[0]
        xx[1] = x[1]
        xx[2] = x[2]
        return self.waves.__cpp_calculate_velocity(xx, t)[1]
    def __cpp_UnsteadyTwoPhaseVelocityInlet_w_dirichlet(self, x, t):
        cython.declare(xx=cython.double[3])
        xx[0] = x[0]
        xx[1] = x[1]
        xx[2] = x[2]
        return self.waves.__cpp_calculate_velocity(xx, t)[2]
    def __cpp_UnsteadyTwoPhaseVelocityInlet_p_advective(self, x, t):
        cython.declare(xx=cython.double[3])
        xx[0] = x[0]
        xx[1] = x[1]
        xx[2] = x[2]
        return self.waves.__cpp_calculate_pressure(xx, t)
    def __cpp_UnsteadyTwoPhaseVelocityInlet_vof_dirichlet(self, x, t):
        cython.declare(xx=cython.double[3])
        xx[0] = x[0]
        xx[1] = x[1]
        xx[2] = x[2]
        return self.waves.__cpp_calculate_vof(xx, t)

    # FOLLOWING BOUNDARY CONDITION IS UNTESTED #
    def setTwoPhaseVelocityInlet(self, U, waterLevel, vert_axis=None, air=1.,
                                 water=0.):
        """
        Imposes a velocity profile lower than the sea level and an open
        boundary for higher than the sealevel.
        :param U: Velocity vector at the global system.
        :param waterLevel: water level at global coordinate system.
        :param vert_axis: index of vertical in position vector, must always be
                        aligned with gravity, by default set to 1].
        :param air: Volume fraction for air (1.0 by default).
        :param water: Volume fraction for water (0.0 by default).
        Below the seawater level, the condition returns the _dirichlet and
        p_advective condition according to the inflow velocity.
        Above the sea water level, the condition returns the gravity as zero,
        and sets _dirichlet condition to zero, only if there is a zero inflow
        velocity component.
        (!) This condition is best used for boundaries and gravity aligned with
            one of the main axes.
        """
    #     self.reset()
    #     self.BC_type = 'TwoPhaseVelocityInlet'

    #     U = np.array(U)
    #     if vert_axis is None:
    #         vert_axis = self.Shape.Domain.nd - 1

    #     def get_inlet_ux_dirichlet_cython(i):
    #         def get_inlet_ux_dirichlet():
    #             def ux_dirichlet(x, t):
    #                 if x[vert_axis] < waterLevel:
    #                     return U[i]
    #                 elif x[vert_axis] >= waterLevel and U[i] == 0:
    #                     return 0.
    #             return ux_dirichlet
    #         return get_inlet_ux_dirichlet

    #     def inlet_vof_dirichlet_cython():
    #         def inlet_vof_dirichlet(x, t):
    #             if x[vert_axis] < waterLevel:
    #                 return water
    #             elif x[vert_axis] >= waterLevel:
    #                 return air
    #         return inlet_vof_dirichlet

    #     def inlet_p_advective_cython():
    #         def inlet_p_advective(x, t):
    #             b_or = self._b_or[self._b_i]
    #             u_p = np.sum(U * b_or)
    #             # This is the normal velocity, based on the inwards boundary
    #             # orientation -b_or
    #             u_p = -u_p
    #             if x[vert_axis] < waterLevel:
    #                 return u_p
    #             elif x[vert_axis] >= waterLevel:
    #                 return None
    #         return inlet_p_advective

    #     self.u_dirichlet.init_cython = get_inlet_ux_dirichlet_cython(0)
    #     self.v_dirichlet.init_cython = get_inlet_ux_dirichlet_cython(1)
    #     if len(U) == 3:
    #             self.w_dirichlet.init_cython = get_inlet_ux_dirichlet_cython(2)
    #     self.vof_dirichlet.init_cython = inlet_vof_dirichlet_cython
    #     self.p_advective.init_cython = inlet_p_advective_cython

    # def setHydrostaticPressureOutlet(self, rho, g, refLevel, vof, pRef=0.0,
    #                                 vert_axis=-1):
    #     self.reset()
    #     a0 = pRef - rho*g[vert_axis]*refLevel
    #     a1 = rho*g[vert_axis]
    #    # This is the normal velocity, based on the boundary orientation

    #     def get_outlet_ux_dirichlet(i):
    #         def ux_dirichlet(x, t):
    #             b_or = self._b_or[self._b_i]
    #             if b_or[i] == 0:
    #                 return 0.
    #         return ux_dirichlet
    #     self.u_dirichlet.uOfXT = get_outlet_ux_dirichlet(0)
    #     self.v_dirichlet.uOfXT = get_outlet_ux_dirichlet(1)
    #     if len(g) == 3:
    #         self.w_dirichlet.uOfXT = get_outlet_ux_dirichlet(2)
    #     self.p_dirichlet.setLinearBC(a0, a1, vert_axis)
    #     self.vof_dirichlet.setConstantBC(vof)
    #     self.u_diffusive.setConstantBC(0.)
    #     self.v_diffusive.setConstantBC(0.)
    #     self.w_diffusive.setConstantBC(0.)
        pass

    # FOLLOWING BOUNDARY CONDITION IS UNTESTED #
    def setHydrostaticPressureOutletWithDepth(self, seaLevel, rhoUp, rhoDown, g,
                                              refLevel, pRef=0.0, vert_axis=None,
                                              air=1.0, water=0.0):
        """Imposes a hydrostatic pressure profile and open boundary conditions
        with a known otuflow depth
       :param rhoUp: Phase density of the upper part.
       :param rhoDown: Phase density of the lower part.
       :param g: Gravitational acceleration vector.
       :param refLevel: Level at which pressure = pRef.
       :param pRef: Reference value for the pressure at x[vert_axis]=refLevel,
                  be default set to 0.
       :param vert_axis: index of vertical in position vector, must always be
                       aligned with gravity, by default set to 1.
       :return: hydrostaticPressureOutlet except when the pressure and the
                vof are defined. Then it returns the pressure and vof profile
                based on the known depth.
       If the boundary is aligned with one of the main axes, sets the
       tangential velocity components to zero as well.
       (!) This condition is best used for boundaries and gravity aligned with
           one of the main axes.
       """
        # self.reset()

        # if vert_axis is None:
        #     vert_axis = self.Shape.Domain.nd - 1

        # def hydrostaticPressureOutletWithDepth_p_dirichlet(x, t):
        #     if x[vert_axis] < seaLevel:
        #         a0 = pRef-rhoUp*g[vert_axis]*(refLevel-seaLevel)-rhoDown*g[vert_axis]*seaLevel
        #         a1 = rhoDown*g[vert_axis]
        #         return a0 + a1*x[vert_axis]

        # def hydrostaticPressureOutletWithDepth_vof_dirichlet(x, t):
        #     if x[vert_axis] < seaLevel:
        #         return water

        # self.setHydrostaticPressureOutlet(rhoUp, g, refLevel, pRef, vert_axis)
        # self.p_dirichlet.uOfXT = hydrostaticPressureOutletWithDepth_p_dirichlet
        # self.vof_dirichlet.uOfXT = hydrostaticPressureOutletWithDepth_vof_dirichlet
        pass



# for regions



class RelaxationZone:
    """
    Holds information about a relaxation zone (wave generation/absorption
    or porous zone)

    Parameters
    ----------
    zone_type: string
        type of zone, can be set to 'absorption', 'generation', or 'porous'
    center: array_like
        coordinates of center of the zone
    orientation: array_like
        orientation for absorption/generation zones: from boundary to tank
    epsFact_solid: float
        half the zone length
    waves: Optional[proteus.WaveTools]
        class instance of a wave from proteus.WaveTools (must be set for
        generation zone)
    shape: Optional[proteus.SpatialTools.Shape]
        shape class instance containing region
    dragAlpha: Optional[float]
        parameter for porous zones (default: 0.5/1.005e-6)
    dragBeta: Optional[float]
        parameter for porous zones (default: 0.)
    porosity: Optional[float]
        parameter for porous zone (default: 1.)
    """

    def __cinit__(self, zone_type, center, orientation, epsFact_solid,
                  waves=None, shape=None, wind_speed=np.array([0.,0.,0.]),
                  dragAlpha=0.5/1.005e-6, dragBeta=0., porosity=1., vert_axis=None, smoothing=0.,
                  he=0., ecH=3., vof_water=0., vof_air=1.):
        self.Shape = shape
        self.nd = self.Shape.Domain.nd
        self.zone_type = zone_type
        self.center = center
        self.orientation = orientation
        if vert_axis is None:
            vert_axis = self.Shape.Domain.nd-1
        if waves is not None:
            self.waves = __cppClass_WavesCharacteristics(waves=waves, wind_speed=wind_speed, vert_axis=vert_axis, smoothing=smoothing, vof_water=vof_water, vof_air=vof_air)
        self.epsFact_solid = epsFact_solid
        self.dragAlpha = dragAlpha
        self.dragBeta = dragBeta
        self.porosity = porosity
        self.zero_vel = np.zeros(3)


    def calculate_init(self):
        if self.zone_type == 'generation':
            #self.u = &self.waves.u
            #self.eta = &self.waves.eta
            self.uu = self.__cpp_calculate_vel_wave
            self.phi = self.__cpp_calculate_phi_solid
        elif self.zone_type == 'absorption':
            self.uu = self.__cpp_calculate_vel_zero
            self.phi = self.__cpp_calculate_phi_solid
        elif self.zone_type == 'porous':
            self.uu = self.__cpp_calculate_vel_zero
            self.phi = self.__cpp_calculate_phi_solid_porous

    def calculate_phi(self, x):
        return self.phi(self, x)

    @cython.boundscheck(False)
    @cython.wraparound(False)
    @cython.initializedcheck(False)
    def __cpp_calculate_phi_solid(self, x):
        """
        Used for RelaxationZone only
        """
        cython.declare(d=cython.double[3], o=cython.double[3])
        d[0] = self.center[0]-x[0]
        d[1] = self.center[1]-x[1]
        d[2] = self.center[2]-x[2]
        o[0] = self.orientation[0]
        o[1] = self.orientation[1]
        o[2] = self.orientation[2]
        phi = o[0]*d[0]+o[1]*d[1]+o[2]*d[2]
        return phi

    def __cpp_calculate_phi_solid_porous(self, x):
        return self.epsFact_solid

    def calculate_vel(self, x, t):
        return self.uu(self, x, t)

    def  __cpp_calculate_vel_zero(self, x, t):
        return self.zero_vel

    def  __cpp_calculate_vel_wave(self, x, t):
        return self.waves.__cpp_calculate_velocity(x, t)


class RelaxationZoneWaveGenerator():
    """
    Prescribe a velocity penalty scaling in a material zone via a
    Darcy-Forchheimer penalty

    Parameters
    ----------
    zones: dict
        dictionary with key as the region flag and values as a RelaxationZone
        class
    nd: int
        number of dimensions of domain
    """

    def __init__(self, zones, nd):
        self.zones = zones
        self.nd = nd

    def attachModel(self, model, ar):
        self.model = model
        self.ar = ar
        return self

    def attachAuxiliaryVariables(self,avDict):
        pass

    def calculate_init(self):
        max_key = 0
        for key, zone in self.zones.iteritems():
            zone.calculate_init()
            if key > max_key:
                max_key = key
        self.max_flag = max_key
        self.zones_array = np.empty(self.max_flag+1, dtype=object)
        for key, zone in self.zones.iteritems():
            self.zones_array[key] = zone

    def calculate(self):
        self.__cpp_iterate()

    def __cpp_iterate(self):
        nl = len(self.model.levelModelList)
        for l in range(nl):  # usually only 1
            # initialisation of variables before costly loop
            m = self.model.levelModelList[l]
            nE = m.coefficients.q_phi.shape[0]
            nk = m.coefficients.q_phi.shape[1]
            t = m.timeIntegration.t
            qx = m.q['x']
            q_phi_solid = m.coefficients.q_phi_solid
            q_velocity_solid = m.coefficients.q_velocity_solid
            mTypes = m.mesh.elementMaterialTypes
            # costly loop
            for eN in range(nE):
                mType = mTypes[eN]
                if mType < self.max_flag:
                    zone = self.zones_array[mType]
                    if zone is not None:
                      for k in range(nk):
                          x[0] = qx[eN, k, 0]
                          x[1] = qx[eN, k, 1]
                          x[2] = qx[eN, k, 2]
                          #print qx.__array_interface__['data'] == m.q['x'].__array_interface__['data']
                          #print x.__array_interface__['data'] == m.q['x'][eN, k].__array_interface__['data']
                          phi = zone.calculate_phi(x)
                          q_phi_solid[eN, k] = phi
                          u = zone.calculate_vel(x, t)
                          q_velocity_solid[eN, k, 0] = u[0]
                          q_velocity_solid[eN, k, 1] = u[1]
                          if self.nd > 2:
                              q_velocity_solid[eN, k, 2] = u[2]
            m.q['phi_solid'] = q_phi_solid
            m.q['velocity_solid'] = q_velocity_solid

class __cppClass_WavesCharacteristics:
    def __init__(self, waves, vert_axis, wind_speed=None, b_or=None, smoothing=0., vof_water=0., vof_air = 1.):
        self.WT = waves  # wavetools wave
        self.vert_axis = vert_axis
        self.zero_vel = np.zeros(3)
        self._b_or = b_or
        self.smoothing = smoothing
        self.vof_air = vof_air
        self.vof_water = vof_water
        if wind_speed is None:
            self.wind_speed = self.zero_vel
        else:
            self.wind_speed = wind_speed

    def  __cpp_calculate_velocity(self, x, t):
        cython.declare(u=cython.double[3])
        cython.declare(xx=cython.double[3])
        cython.declare(x_max=cython.double[3])
        xx[0] = x[0]
        xx[1] = x[1]
        xx[2] = x[2]
        phi = self.__cpp_calculate_phi(x, t)
        H = self.__cpp_calculate_smoothing_H(phi)
        if 0 <= H < 0.5:
            waterSpeed = self.WT.u(xx, t)
        elif 0.5 < H < 1.:
            x_max[0] = x[0]
            x_max[1] = x[1]
            x_max[2] = x[2]
            x_max[self.vert_axis] = x[self.vert_axis]-phi
            waterSpeed = self.WT.u(x_max, t)
        else:
            waterSpeed = self.zero_vel
        u[0] = H*self.wind_speed[0] + (1-H)*waterSpeed[0]
        u[1] = H*self.wind_speed[1] + (1-H)*waterSpeed[1]
        u[2] = H*self.wind_speed[2] + (1-H)*waterSpeed[2]
        # print('u: ', u[0], u[1], u[2])
        return u

    def __cpp_calculate_pressure(self, x, t):
        # This is the normal velocity, based on the outwards boundary
        # orientation b_or
        # needs to be equal to -ux_dirichlet
        ux = self.__cpp_calculate_velocity(x, t)
        b0, b1, b2 = self._b_or[0], self._b_or[1], self._b_or[2]
        u0, u1, u2 = ux[0], ux[1], ux[2]
        return b0*u0+b1*u1+b2*u2

    def __cpp_calculate_phi(self, x, t):
        cython.declare(xx=cython.double[3])
        xx[0] = x[0]
        xx[1] = x[1]
        xx[2] = x[2]
        level = self.WT.mwl + self.WT.eta(xx,t)
        return x[self.vert_axis]-level

    def __cpp_calculate_vof(self, x, t):
        phi = self.__cpp_calculate_phi(x, t)
        H = self.__cpp_calculate_smoothing_H(phi)
        return H

    def __cpp_calculate_smoothing_H(self, phi):
        if phi >= self.smoothing:
            H = 1.
        elif self.smoothing > 0 and -self.smoothing < phi < self.smoothing:
            H = smoothedHeaviside(self.smoothing, phi)
        elif phi <= -self.smoothing:
            H = 0.
        return H


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.initializedcheck(False)
def __x_to_cpp(x):
    cython.declare(xx=double[3])
    xx[0] = x[0]
    xx[1] = x[1]
    xx[2] = x[2]
    return xx
