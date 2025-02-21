#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                       Code generated with SymPy 1.12                       *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_2142121554470553610) {
   out_2142121554470553610[0] = delta_x[0] + nom_x[0];
   out_2142121554470553610[1] = delta_x[1] + nom_x[1];
   out_2142121554470553610[2] = delta_x[2] + nom_x[2];
   out_2142121554470553610[3] = delta_x[3] + nom_x[3];
   out_2142121554470553610[4] = delta_x[4] + nom_x[4];
   out_2142121554470553610[5] = delta_x[5] + nom_x[5];
   out_2142121554470553610[6] = delta_x[6] + nom_x[6];
   out_2142121554470553610[7] = delta_x[7] + nom_x[7];
   out_2142121554470553610[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1877113646947671320) {
   out_1877113646947671320[0] = -nom_x[0] + true_x[0];
   out_1877113646947671320[1] = -nom_x[1] + true_x[1];
   out_1877113646947671320[2] = -nom_x[2] + true_x[2];
   out_1877113646947671320[3] = -nom_x[3] + true_x[3];
   out_1877113646947671320[4] = -nom_x[4] + true_x[4];
   out_1877113646947671320[5] = -nom_x[5] + true_x[5];
   out_1877113646947671320[6] = -nom_x[6] + true_x[6];
   out_1877113646947671320[7] = -nom_x[7] + true_x[7];
   out_1877113646947671320[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6260732612257231518) {
   out_6260732612257231518[0] = 1.0;
   out_6260732612257231518[1] = 0;
   out_6260732612257231518[2] = 0;
   out_6260732612257231518[3] = 0;
   out_6260732612257231518[4] = 0;
   out_6260732612257231518[5] = 0;
   out_6260732612257231518[6] = 0;
   out_6260732612257231518[7] = 0;
   out_6260732612257231518[8] = 0;
   out_6260732612257231518[9] = 0;
   out_6260732612257231518[10] = 1.0;
   out_6260732612257231518[11] = 0;
   out_6260732612257231518[12] = 0;
   out_6260732612257231518[13] = 0;
   out_6260732612257231518[14] = 0;
   out_6260732612257231518[15] = 0;
   out_6260732612257231518[16] = 0;
   out_6260732612257231518[17] = 0;
   out_6260732612257231518[18] = 0;
   out_6260732612257231518[19] = 0;
   out_6260732612257231518[20] = 1.0;
   out_6260732612257231518[21] = 0;
   out_6260732612257231518[22] = 0;
   out_6260732612257231518[23] = 0;
   out_6260732612257231518[24] = 0;
   out_6260732612257231518[25] = 0;
   out_6260732612257231518[26] = 0;
   out_6260732612257231518[27] = 0;
   out_6260732612257231518[28] = 0;
   out_6260732612257231518[29] = 0;
   out_6260732612257231518[30] = 1.0;
   out_6260732612257231518[31] = 0;
   out_6260732612257231518[32] = 0;
   out_6260732612257231518[33] = 0;
   out_6260732612257231518[34] = 0;
   out_6260732612257231518[35] = 0;
   out_6260732612257231518[36] = 0;
   out_6260732612257231518[37] = 0;
   out_6260732612257231518[38] = 0;
   out_6260732612257231518[39] = 0;
   out_6260732612257231518[40] = 1.0;
   out_6260732612257231518[41] = 0;
   out_6260732612257231518[42] = 0;
   out_6260732612257231518[43] = 0;
   out_6260732612257231518[44] = 0;
   out_6260732612257231518[45] = 0;
   out_6260732612257231518[46] = 0;
   out_6260732612257231518[47] = 0;
   out_6260732612257231518[48] = 0;
   out_6260732612257231518[49] = 0;
   out_6260732612257231518[50] = 1.0;
   out_6260732612257231518[51] = 0;
   out_6260732612257231518[52] = 0;
   out_6260732612257231518[53] = 0;
   out_6260732612257231518[54] = 0;
   out_6260732612257231518[55] = 0;
   out_6260732612257231518[56] = 0;
   out_6260732612257231518[57] = 0;
   out_6260732612257231518[58] = 0;
   out_6260732612257231518[59] = 0;
   out_6260732612257231518[60] = 1.0;
   out_6260732612257231518[61] = 0;
   out_6260732612257231518[62] = 0;
   out_6260732612257231518[63] = 0;
   out_6260732612257231518[64] = 0;
   out_6260732612257231518[65] = 0;
   out_6260732612257231518[66] = 0;
   out_6260732612257231518[67] = 0;
   out_6260732612257231518[68] = 0;
   out_6260732612257231518[69] = 0;
   out_6260732612257231518[70] = 1.0;
   out_6260732612257231518[71] = 0;
   out_6260732612257231518[72] = 0;
   out_6260732612257231518[73] = 0;
   out_6260732612257231518[74] = 0;
   out_6260732612257231518[75] = 0;
   out_6260732612257231518[76] = 0;
   out_6260732612257231518[77] = 0;
   out_6260732612257231518[78] = 0;
   out_6260732612257231518[79] = 0;
   out_6260732612257231518[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_337609772483159483) {
   out_337609772483159483[0] = state[0];
   out_337609772483159483[1] = state[1];
   out_337609772483159483[2] = state[2];
   out_337609772483159483[3] = state[3];
   out_337609772483159483[4] = state[4];
   out_337609772483159483[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8000000000000007*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_337609772483159483[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_337609772483159483[7] = state[7];
   out_337609772483159483[8] = state[8];
}
void F_fun(double *state, double dt, double *out_8806306134723177886) {
   out_8806306134723177886[0] = 1;
   out_8806306134723177886[1] = 0;
   out_8806306134723177886[2] = 0;
   out_8806306134723177886[3] = 0;
   out_8806306134723177886[4] = 0;
   out_8806306134723177886[5] = 0;
   out_8806306134723177886[6] = 0;
   out_8806306134723177886[7] = 0;
   out_8806306134723177886[8] = 0;
   out_8806306134723177886[9] = 0;
   out_8806306134723177886[10] = 1;
   out_8806306134723177886[11] = 0;
   out_8806306134723177886[12] = 0;
   out_8806306134723177886[13] = 0;
   out_8806306134723177886[14] = 0;
   out_8806306134723177886[15] = 0;
   out_8806306134723177886[16] = 0;
   out_8806306134723177886[17] = 0;
   out_8806306134723177886[18] = 0;
   out_8806306134723177886[19] = 0;
   out_8806306134723177886[20] = 1;
   out_8806306134723177886[21] = 0;
   out_8806306134723177886[22] = 0;
   out_8806306134723177886[23] = 0;
   out_8806306134723177886[24] = 0;
   out_8806306134723177886[25] = 0;
   out_8806306134723177886[26] = 0;
   out_8806306134723177886[27] = 0;
   out_8806306134723177886[28] = 0;
   out_8806306134723177886[29] = 0;
   out_8806306134723177886[30] = 1;
   out_8806306134723177886[31] = 0;
   out_8806306134723177886[32] = 0;
   out_8806306134723177886[33] = 0;
   out_8806306134723177886[34] = 0;
   out_8806306134723177886[35] = 0;
   out_8806306134723177886[36] = 0;
   out_8806306134723177886[37] = 0;
   out_8806306134723177886[38] = 0;
   out_8806306134723177886[39] = 0;
   out_8806306134723177886[40] = 1;
   out_8806306134723177886[41] = 0;
   out_8806306134723177886[42] = 0;
   out_8806306134723177886[43] = 0;
   out_8806306134723177886[44] = 0;
   out_8806306134723177886[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_8806306134723177886[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_8806306134723177886[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_8806306134723177886[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_8806306134723177886[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_8806306134723177886[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_8806306134723177886[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_8806306134723177886[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_8806306134723177886[53] = -9.8000000000000007*dt;
   out_8806306134723177886[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_8806306134723177886[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_8806306134723177886[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8806306134723177886[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8806306134723177886[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_8806306134723177886[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_8806306134723177886[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_8806306134723177886[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8806306134723177886[62] = 0;
   out_8806306134723177886[63] = 0;
   out_8806306134723177886[64] = 0;
   out_8806306134723177886[65] = 0;
   out_8806306134723177886[66] = 0;
   out_8806306134723177886[67] = 0;
   out_8806306134723177886[68] = 0;
   out_8806306134723177886[69] = 0;
   out_8806306134723177886[70] = 1;
   out_8806306134723177886[71] = 0;
   out_8806306134723177886[72] = 0;
   out_8806306134723177886[73] = 0;
   out_8806306134723177886[74] = 0;
   out_8806306134723177886[75] = 0;
   out_8806306134723177886[76] = 0;
   out_8806306134723177886[77] = 0;
   out_8806306134723177886[78] = 0;
   out_8806306134723177886[79] = 0;
   out_8806306134723177886[80] = 1;
}
void h_25(double *state, double *unused, double *out_3223695039837964036) {
   out_3223695039837964036[0] = state[6];
}
void H_25(double *state, double *unused, double *out_5553746004255008924) {
   out_5553746004255008924[0] = 0;
   out_5553746004255008924[1] = 0;
   out_5553746004255008924[2] = 0;
   out_5553746004255008924[3] = 0;
   out_5553746004255008924[4] = 0;
   out_5553746004255008924[5] = 0;
   out_5553746004255008924[6] = 1;
   out_5553746004255008924[7] = 0;
   out_5553746004255008924[8] = 0;
}
void h_24(double *state, double *unused, double *out_4565396018398548899) {
   out_4565396018398548899[0] = state[4];
   out_4565396018398548899[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1222822487337066443) {
   out_1222822487337066443[0] = 0;
   out_1222822487337066443[1] = 0;
   out_1222822487337066443[2] = 0;
   out_1222822487337066443[3] = 0;
   out_1222822487337066443[4] = 1;
   out_1222822487337066443[5] = 0;
   out_1222822487337066443[6] = 0;
   out_1222822487337066443[7] = 0;
   out_1222822487337066443[8] = 0;
   out_1222822487337066443[9] = 0;
   out_1222822487337066443[10] = 0;
   out_1222822487337066443[11] = 0;
   out_1222822487337066443[12] = 0;
   out_1222822487337066443[13] = 0;
   out_1222822487337066443[14] = 1;
   out_1222822487337066443[15] = 0;
   out_1222822487337066443[16] = 0;
   out_1222822487337066443[17] = 0;
}
void h_30(double *state, double *unused, double *out_8859455055569771719) {
   out_8859455055569771719[0] = state[4];
}
void H_30(double *state, double *unused, double *out_5424407057111768854) {
   out_5424407057111768854[0] = 0;
   out_5424407057111768854[1] = 0;
   out_5424407057111768854[2] = 0;
   out_5424407057111768854[3] = 0;
   out_5424407057111768854[4] = 1;
   out_5424407057111768854[5] = 0;
   out_5424407057111768854[6] = 0;
   out_5424407057111768854[7] = 0;
   out_5424407057111768854[8] = 0;
}
void h_26(double *state, double *unused, double *out_4585615750478934252) {
   out_4585615750478934252[0] = state[7];
}
void H_26(double *state, double *unused, double *out_1812242685380952700) {
   out_1812242685380952700[0] = 0;
   out_1812242685380952700[1] = 0;
   out_1812242685380952700[2] = 0;
   out_1812242685380952700[3] = 0;
   out_1812242685380952700[4] = 0;
   out_1812242685380952700[5] = 0;
   out_1812242685380952700[6] = 0;
   out_1812242685380952700[7] = 1;
   out_1812242685380952700[8] = 0;
}
void h_27(double *state, double *unused, double *out_4703623144412310996) {
   out_4703623144412310996[0] = state[3];
}
void H_27(double *state, double *unused, double *out_3249643745311343943) {
   out_3249643745311343943[0] = 0;
   out_3249643745311343943[1] = 0;
   out_3249643745311343943[2] = 0;
   out_3249643745311343943[3] = 1;
   out_3249643745311343943[4] = 0;
   out_3249643745311343943[5] = 0;
   out_3249643745311343943[6] = 0;
   out_3249643745311343943[7] = 0;
   out_3249643745311343943[8] = 0;
}
void h_29(double *state, double *unused, double *out_605319846132939132) {
   out_605319846132939132[0] = state[1];
}
void H_29(double *state, double *unused, double *out_5934638401426161038) {
   out_5934638401426161038[0] = 0;
   out_5934638401426161038[1] = 1;
   out_5934638401426161038[2] = 0;
   out_5934638401426161038[3] = 0;
   out_5934638401426161038[4] = 0;
   out_5934638401426161038[5] = 0;
   out_5934638401426161038[6] = 0;
   out_5934638401426161038[7] = 0;
   out_5934638401426161038[8] = 0;
}
void h_28(double *state, double *unused, double *out_8741447661636394975) {
   out_8741447661636394975[0] = state[0];
}
void H_28(double *state, double *unused, double *out_3499911290007119161) {
   out_3499911290007119161[0] = 1;
   out_3499911290007119161[1] = 0;
   out_3499911290007119161[2] = 0;
   out_3499911290007119161[3] = 0;
   out_3499911290007119161[4] = 0;
   out_3499911290007119161[5] = 0;
   out_3499911290007119161[6] = 0;
   out_3499911290007119161[7] = 0;
   out_3499911290007119161[8] = 0;
}
void h_31(double *state, double *unused, double *out_6583171557153045696) {
   out_6583171557153045696[0] = state[8];
}
void H_31(double *state, double *unused, double *out_5584391966131969352) {
   out_5584391966131969352[0] = 0;
   out_5584391966131969352[1] = 0;
   out_5584391966131969352[2] = 0;
   out_5584391966131969352[3] = 0;
   out_5584391966131969352[4] = 0;
   out_5584391966131969352[5] = 0;
   out_5584391966131969352[6] = 0;
   out_5584391966131969352[7] = 0;
   out_5584391966131969352[8] = 1;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_2142121554470553610) {
  err_fun(nom_x, delta_x, out_2142121554470553610);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1877113646947671320) {
  inv_err_fun(nom_x, true_x, out_1877113646947671320);
}
void car_H_mod_fun(double *state, double *out_6260732612257231518) {
  H_mod_fun(state, out_6260732612257231518);
}
void car_f_fun(double *state, double dt, double *out_337609772483159483) {
  f_fun(state,  dt, out_337609772483159483);
}
void car_F_fun(double *state, double dt, double *out_8806306134723177886) {
  F_fun(state,  dt, out_8806306134723177886);
}
void car_h_25(double *state, double *unused, double *out_3223695039837964036) {
  h_25(state, unused, out_3223695039837964036);
}
void car_H_25(double *state, double *unused, double *out_5553746004255008924) {
  H_25(state, unused, out_5553746004255008924);
}
void car_h_24(double *state, double *unused, double *out_4565396018398548899) {
  h_24(state, unused, out_4565396018398548899);
}
void car_H_24(double *state, double *unused, double *out_1222822487337066443) {
  H_24(state, unused, out_1222822487337066443);
}
void car_h_30(double *state, double *unused, double *out_8859455055569771719) {
  h_30(state, unused, out_8859455055569771719);
}
void car_H_30(double *state, double *unused, double *out_5424407057111768854) {
  H_30(state, unused, out_5424407057111768854);
}
void car_h_26(double *state, double *unused, double *out_4585615750478934252) {
  h_26(state, unused, out_4585615750478934252);
}
void car_H_26(double *state, double *unused, double *out_1812242685380952700) {
  H_26(state, unused, out_1812242685380952700);
}
void car_h_27(double *state, double *unused, double *out_4703623144412310996) {
  h_27(state, unused, out_4703623144412310996);
}
void car_H_27(double *state, double *unused, double *out_3249643745311343943) {
  H_27(state, unused, out_3249643745311343943);
}
void car_h_29(double *state, double *unused, double *out_605319846132939132) {
  h_29(state, unused, out_605319846132939132);
}
void car_H_29(double *state, double *unused, double *out_5934638401426161038) {
  H_29(state, unused, out_5934638401426161038);
}
void car_h_28(double *state, double *unused, double *out_8741447661636394975) {
  h_28(state, unused, out_8741447661636394975);
}
void car_H_28(double *state, double *unused, double *out_3499911290007119161) {
  H_28(state, unused, out_3499911290007119161);
}
void car_h_31(double *state, double *unused, double *out_6583171557153045696) {
  h_31(state, unused, out_6583171557153045696);
}
void car_H_31(double *state, double *unused, double *out_5584391966131969352) {
  H_31(state, unused, out_5584391966131969352);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
