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
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_4436222918597397805) {
   out_4436222918597397805[0] = delta_x[0] + nom_x[0];
   out_4436222918597397805[1] = delta_x[1] + nom_x[1];
   out_4436222918597397805[2] = delta_x[2] + nom_x[2];
   out_4436222918597397805[3] = delta_x[3] + nom_x[3];
   out_4436222918597397805[4] = delta_x[4] + nom_x[4];
   out_4436222918597397805[5] = delta_x[5] + nom_x[5];
   out_4436222918597397805[6] = delta_x[6] + nom_x[6];
   out_4436222918597397805[7] = delta_x[7] + nom_x[7];
   out_4436222918597397805[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5455437002668972894) {
   out_5455437002668972894[0] = -nom_x[0] + true_x[0];
   out_5455437002668972894[1] = -nom_x[1] + true_x[1];
   out_5455437002668972894[2] = -nom_x[2] + true_x[2];
   out_5455437002668972894[3] = -nom_x[3] + true_x[3];
   out_5455437002668972894[4] = -nom_x[4] + true_x[4];
   out_5455437002668972894[5] = -nom_x[5] + true_x[5];
   out_5455437002668972894[6] = -nom_x[6] + true_x[6];
   out_5455437002668972894[7] = -nom_x[7] + true_x[7];
   out_5455437002668972894[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_210375879520347438) {
   out_210375879520347438[0] = 1.0;
   out_210375879520347438[1] = 0.0;
   out_210375879520347438[2] = 0.0;
   out_210375879520347438[3] = 0.0;
   out_210375879520347438[4] = 0.0;
   out_210375879520347438[5] = 0.0;
   out_210375879520347438[6] = 0.0;
   out_210375879520347438[7] = 0.0;
   out_210375879520347438[8] = 0.0;
   out_210375879520347438[9] = 0.0;
   out_210375879520347438[10] = 1.0;
   out_210375879520347438[11] = 0.0;
   out_210375879520347438[12] = 0.0;
   out_210375879520347438[13] = 0.0;
   out_210375879520347438[14] = 0.0;
   out_210375879520347438[15] = 0.0;
   out_210375879520347438[16] = 0.0;
   out_210375879520347438[17] = 0.0;
   out_210375879520347438[18] = 0.0;
   out_210375879520347438[19] = 0.0;
   out_210375879520347438[20] = 1.0;
   out_210375879520347438[21] = 0.0;
   out_210375879520347438[22] = 0.0;
   out_210375879520347438[23] = 0.0;
   out_210375879520347438[24] = 0.0;
   out_210375879520347438[25] = 0.0;
   out_210375879520347438[26] = 0.0;
   out_210375879520347438[27] = 0.0;
   out_210375879520347438[28] = 0.0;
   out_210375879520347438[29] = 0.0;
   out_210375879520347438[30] = 1.0;
   out_210375879520347438[31] = 0.0;
   out_210375879520347438[32] = 0.0;
   out_210375879520347438[33] = 0.0;
   out_210375879520347438[34] = 0.0;
   out_210375879520347438[35] = 0.0;
   out_210375879520347438[36] = 0.0;
   out_210375879520347438[37] = 0.0;
   out_210375879520347438[38] = 0.0;
   out_210375879520347438[39] = 0.0;
   out_210375879520347438[40] = 1.0;
   out_210375879520347438[41] = 0.0;
   out_210375879520347438[42] = 0.0;
   out_210375879520347438[43] = 0.0;
   out_210375879520347438[44] = 0.0;
   out_210375879520347438[45] = 0.0;
   out_210375879520347438[46] = 0.0;
   out_210375879520347438[47] = 0.0;
   out_210375879520347438[48] = 0.0;
   out_210375879520347438[49] = 0.0;
   out_210375879520347438[50] = 1.0;
   out_210375879520347438[51] = 0.0;
   out_210375879520347438[52] = 0.0;
   out_210375879520347438[53] = 0.0;
   out_210375879520347438[54] = 0.0;
   out_210375879520347438[55] = 0.0;
   out_210375879520347438[56] = 0.0;
   out_210375879520347438[57] = 0.0;
   out_210375879520347438[58] = 0.0;
   out_210375879520347438[59] = 0.0;
   out_210375879520347438[60] = 1.0;
   out_210375879520347438[61] = 0.0;
   out_210375879520347438[62] = 0.0;
   out_210375879520347438[63] = 0.0;
   out_210375879520347438[64] = 0.0;
   out_210375879520347438[65] = 0.0;
   out_210375879520347438[66] = 0.0;
   out_210375879520347438[67] = 0.0;
   out_210375879520347438[68] = 0.0;
   out_210375879520347438[69] = 0.0;
   out_210375879520347438[70] = 1.0;
   out_210375879520347438[71] = 0.0;
   out_210375879520347438[72] = 0.0;
   out_210375879520347438[73] = 0.0;
   out_210375879520347438[74] = 0.0;
   out_210375879520347438[75] = 0.0;
   out_210375879520347438[76] = 0.0;
   out_210375879520347438[77] = 0.0;
   out_210375879520347438[78] = 0.0;
   out_210375879520347438[79] = 0.0;
   out_210375879520347438[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_467846126367206141) {
   out_467846126367206141[0] = state[0];
   out_467846126367206141[1] = state[1];
   out_467846126367206141[2] = state[2];
   out_467846126367206141[3] = state[3];
   out_467846126367206141[4] = state[4];
   out_467846126367206141[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_467846126367206141[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_467846126367206141[7] = state[7];
   out_467846126367206141[8] = state[8];
}
void F_fun(double *state, double dt, double *out_3146439140780538523) {
   out_3146439140780538523[0] = 1;
   out_3146439140780538523[1] = 0;
   out_3146439140780538523[2] = 0;
   out_3146439140780538523[3] = 0;
   out_3146439140780538523[4] = 0;
   out_3146439140780538523[5] = 0;
   out_3146439140780538523[6] = 0;
   out_3146439140780538523[7] = 0;
   out_3146439140780538523[8] = 0;
   out_3146439140780538523[9] = 0;
   out_3146439140780538523[10] = 1;
   out_3146439140780538523[11] = 0;
   out_3146439140780538523[12] = 0;
   out_3146439140780538523[13] = 0;
   out_3146439140780538523[14] = 0;
   out_3146439140780538523[15] = 0;
   out_3146439140780538523[16] = 0;
   out_3146439140780538523[17] = 0;
   out_3146439140780538523[18] = 0;
   out_3146439140780538523[19] = 0;
   out_3146439140780538523[20] = 1;
   out_3146439140780538523[21] = 0;
   out_3146439140780538523[22] = 0;
   out_3146439140780538523[23] = 0;
   out_3146439140780538523[24] = 0;
   out_3146439140780538523[25] = 0;
   out_3146439140780538523[26] = 0;
   out_3146439140780538523[27] = 0;
   out_3146439140780538523[28] = 0;
   out_3146439140780538523[29] = 0;
   out_3146439140780538523[30] = 1;
   out_3146439140780538523[31] = 0;
   out_3146439140780538523[32] = 0;
   out_3146439140780538523[33] = 0;
   out_3146439140780538523[34] = 0;
   out_3146439140780538523[35] = 0;
   out_3146439140780538523[36] = 0;
   out_3146439140780538523[37] = 0;
   out_3146439140780538523[38] = 0;
   out_3146439140780538523[39] = 0;
   out_3146439140780538523[40] = 1;
   out_3146439140780538523[41] = 0;
   out_3146439140780538523[42] = 0;
   out_3146439140780538523[43] = 0;
   out_3146439140780538523[44] = 0;
   out_3146439140780538523[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_3146439140780538523[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_3146439140780538523[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3146439140780538523[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3146439140780538523[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_3146439140780538523[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_3146439140780538523[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_3146439140780538523[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_3146439140780538523[53] = -9.8100000000000005*dt;
   out_3146439140780538523[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_3146439140780538523[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_3146439140780538523[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3146439140780538523[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3146439140780538523[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_3146439140780538523[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_3146439140780538523[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_3146439140780538523[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3146439140780538523[62] = 0;
   out_3146439140780538523[63] = 0;
   out_3146439140780538523[64] = 0;
   out_3146439140780538523[65] = 0;
   out_3146439140780538523[66] = 0;
   out_3146439140780538523[67] = 0;
   out_3146439140780538523[68] = 0;
   out_3146439140780538523[69] = 0;
   out_3146439140780538523[70] = 1;
   out_3146439140780538523[71] = 0;
   out_3146439140780538523[72] = 0;
   out_3146439140780538523[73] = 0;
   out_3146439140780538523[74] = 0;
   out_3146439140780538523[75] = 0;
   out_3146439140780538523[76] = 0;
   out_3146439140780538523[77] = 0;
   out_3146439140780538523[78] = 0;
   out_3146439140780538523[79] = 0;
   out_3146439140780538523[80] = 1;
}
void h_25(double *state, double *unused, double *out_3524127915259881655) {
   out_3524127915259881655[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3733424518165712586) {
   out_3733424518165712586[0] = 0;
   out_3733424518165712586[1] = 0;
   out_3733424518165712586[2] = 0;
   out_3733424518165712586[3] = 0;
   out_3733424518165712586[4] = 0;
   out_3733424518165712586[5] = 0;
   out_3733424518165712586[6] = 1;
   out_3733424518165712586[7] = 0;
   out_3733424518165712586[8] = 0;
}
void h_24(double *state, double *unused, double *out_5258226883159248845) {
   out_5258226883159248845[0] = state[4];
   out_5258226883159248845[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2842147288425805515) {
   out_2842147288425805515[0] = 0;
   out_2842147288425805515[1] = 0;
   out_2842147288425805515[2] = 0;
   out_2842147288425805515[3] = 0;
   out_2842147288425805515[4] = 1;
   out_2842147288425805515[5] = 0;
   out_2842147288425805515[6] = 0;
   out_2842147288425805515[7] = 0;
   out_2842147288425805515[8] = 0;
   out_2842147288425805515[9] = 0;
   out_2842147288425805515[10] = 0;
   out_2842147288425805515[11] = 0;
   out_2842147288425805515[12] = 0;
   out_2842147288425805515[13] = 0;
   out_2842147288425805515[14] = 1;
   out_2842147288425805515[15] = 0;
   out_2842147288425805515[16] = 0;
   out_2842147288425805515[17] = 0;
}
void h_30(double *state, double *unused, double *out_2922709757646518101) {
   out_2922709757646518101[0] = state[4];
}
void H_30(double *state, double *unused, double *out_3183265823325904169) {
   out_3183265823325904169[0] = 0;
   out_3183265823325904169[1] = 0;
   out_3183265823325904169[2] = 0;
   out_3183265823325904169[3] = 0;
   out_3183265823325904169[4] = 1;
   out_3183265823325904169[5] = 0;
   out_3183265823325904169[6] = 0;
   out_3183265823325904169[7] = 0;
   out_3183265823325904169[8] = 0;
}
void h_26(double *state, double *unused, double *out_2078963510014327544) {
   out_2078963510014327544[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7474927837039768810) {
   out_7474927837039768810[0] = 0;
   out_7474927837039768810[1] = 0;
   out_7474927837039768810[2] = 0;
   out_7474927837039768810[3] = 0;
   out_7474927837039768810[4] = 0;
   out_7474927837039768810[5] = 0;
   out_7474927837039768810[6] = 0;
   out_7474927837039768810[7] = 1;
   out_7474927837039768810[8] = 0;
}
void h_27(double *state, double *unused, double *out_9006985404715807625) {
   out_9006985404715807625[0] = state[3];
}
void H_27(double *state, double *unused, double *out_1008502511525479258) {
   out_1008502511525479258[0] = 0;
   out_1008502511525479258[1] = 0;
   out_1008502511525479258[2] = 0;
   out_1008502511525479258[3] = 1;
   out_1008502511525479258[4] = 0;
   out_1008502511525479258[5] = 0;
   out_1008502511525479258[6] = 0;
   out_1008502511525479258[7] = 0;
   out_1008502511525479258[8] = 0;
}
void h_29(double *state, double *unused, double *out_1979199904744855666) {
   out_1979199904744855666[0] = state[1];
}
void H_29(double *state, double *unused, double *out_704860215344071775) {
   out_704860215344071775[0] = 0;
   out_704860215344071775[1] = 1;
   out_704860215344071775[2] = 0;
   out_704860215344071775[3] = 0;
   out_704860215344071775[4] = 0;
   out_704860215344071775[5] = 0;
   out_704860215344071775[6] = 0;
   out_704860215344071775[7] = 0;
   out_704860215344071775[8] = 0;
}
void h_28(double *state, double *unused, double *out_6835353348185046340) {
   out_6835353348185046340[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5787259232413602349) {
   out_5787259232413602349[0] = 1;
   out_5787259232413602349[1] = 0;
   out_5787259232413602349[2] = 0;
   out_5787259232413602349[3] = 0;
   out_5787259232413602349[4] = 0;
   out_5787259232413602349[5] = 0;
   out_5787259232413602349[6] = 0;
   out_5787259232413602349[7] = 0;
   out_5787259232413602349[8] = 0;
}
void h_31(double *state, double *unused, double *out_4974759307888764822) {
   out_4974759307888764822[0] = state[8];
}
void H_31(double *state, double *unused, double *out_3702778556288752158) {
   out_3702778556288752158[0] = 0;
   out_3702778556288752158[1] = 0;
   out_3702778556288752158[2] = 0;
   out_3702778556288752158[3] = 0;
   out_3702778556288752158[4] = 0;
   out_3702778556288752158[5] = 0;
   out_3702778556288752158[6] = 0;
   out_3702778556288752158[7] = 0;
   out_3702778556288752158[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_4436222918597397805) {
  err_fun(nom_x, delta_x, out_4436222918597397805);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5455437002668972894) {
  inv_err_fun(nom_x, true_x, out_5455437002668972894);
}
void car_H_mod_fun(double *state, double *out_210375879520347438) {
  H_mod_fun(state, out_210375879520347438);
}
void car_f_fun(double *state, double dt, double *out_467846126367206141) {
  f_fun(state,  dt, out_467846126367206141);
}
void car_F_fun(double *state, double dt, double *out_3146439140780538523) {
  F_fun(state,  dt, out_3146439140780538523);
}
void car_h_25(double *state, double *unused, double *out_3524127915259881655) {
  h_25(state, unused, out_3524127915259881655);
}
void car_H_25(double *state, double *unused, double *out_3733424518165712586) {
  H_25(state, unused, out_3733424518165712586);
}
void car_h_24(double *state, double *unused, double *out_5258226883159248845) {
  h_24(state, unused, out_5258226883159248845);
}
void car_H_24(double *state, double *unused, double *out_2842147288425805515) {
  H_24(state, unused, out_2842147288425805515);
}
void car_h_30(double *state, double *unused, double *out_2922709757646518101) {
  h_30(state, unused, out_2922709757646518101);
}
void car_H_30(double *state, double *unused, double *out_3183265823325904169) {
  H_30(state, unused, out_3183265823325904169);
}
void car_h_26(double *state, double *unused, double *out_2078963510014327544) {
  h_26(state, unused, out_2078963510014327544);
}
void car_H_26(double *state, double *unused, double *out_7474927837039768810) {
  H_26(state, unused, out_7474927837039768810);
}
void car_h_27(double *state, double *unused, double *out_9006985404715807625) {
  h_27(state, unused, out_9006985404715807625);
}
void car_H_27(double *state, double *unused, double *out_1008502511525479258) {
  H_27(state, unused, out_1008502511525479258);
}
void car_h_29(double *state, double *unused, double *out_1979199904744855666) {
  h_29(state, unused, out_1979199904744855666);
}
void car_H_29(double *state, double *unused, double *out_704860215344071775) {
  H_29(state, unused, out_704860215344071775);
}
void car_h_28(double *state, double *unused, double *out_6835353348185046340) {
  h_28(state, unused, out_6835353348185046340);
}
void car_H_28(double *state, double *unused, double *out_5787259232413602349) {
  H_28(state, unused, out_5787259232413602349);
}
void car_h_31(double *state, double *unused, double *out_4974759307888764822) {
  h_31(state, unused, out_4974759307888764822);
}
void car_H_31(double *state, double *unused, double *out_3702778556288752158) {
  H_31(state, unused, out_3702778556288752158);
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
